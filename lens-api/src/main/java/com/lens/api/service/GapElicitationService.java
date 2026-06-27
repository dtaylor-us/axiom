package com.lens.api.service;

import com.lens.api.client.LensAgentClient;
import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.domain.model.GapQuestion;
import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;
import com.lens.api.exception.BadRequestException;
import com.lens.api.exception.ConflictException;
import com.lens.api.exception.ResourceNotFoundException;
import com.lens.api.repository.GapQuestionRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class GapElicitationService {

    private final LensAgentClient lensAgentClient;
    private final ReviewSessionService reviewSessionService;
    private final EvidenceIngestionService evidenceIngestionService;
    private final GapQuestionRepository gapQuestionRepository;
    private final int maxRounds;
    private final Duration timeout;

    public GapElicitationService(
            LensAgentClient lensAgentClient,
            ReviewSessionService reviewSessionService,
            EvidenceIngestionService evidenceIngestionService,
            GapQuestionRepository gapQuestionRepository,
            @Value("${lens.gap.max-rounds:${LENS_GAP_MAX_ROUNDS:5}}") int maxRounds,
            @Value("${lens.agent.timeout-seconds:${AGENT_TIMEOUT_SECONDS:300}}") int timeoutSeconds) {
        this.lensAgentClient = lensAgentClient;
        this.reviewSessionService = reviewSessionService;
        this.evidenceIngestionService = evidenceIngestionService;
        this.gapQuestionRepository = gapQuestionRepository;
        this.maxRounds = maxRounds;
        this.timeout = Duration.ofSeconds(timeoutSeconds);
    }

    @Transactional
    public List<GapQuestion> generateNextRound(UUID sessionId, String userId) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getStatus() != ReviewStatus.EVIDENCE_COLLECTION
                && session.getStatus() != ReviewStatus.GAP_ELICITATION) {
            throw new ConflictException("Gap questions can only be generated during evidence collection or gap elicitation");
        }

        List<ArchitectureEvidence> evidence = evidenceIngestionService.listEvidence(sessionId);
        if (evidence.isEmpty()) {
            throw new BadRequestException("Submit evidence before generating gap questions");
        }

        int round = session.getGapRound() + 1;
        List<Map<String, Object>> evidencePayload = toEvidencePayload(evidence);
        List<Map<String, Object>> previousPayload = gapQuestionRepository.findBySessionIdOrderByAskedAtAsc(sessionId)
                .stream()
                .map(this::toPreviousQuestionPayload)
                .toList();
        List<Map<String, Object>> answersPayload = gapQuestionRepository.findBySessionIdOrderByAskedAtAsc(sessionId)
                .stream()
                .filter(GapQuestion::isAnswered)
                .map(this::toAnswerPayload)
                .toList();

        List<Set<String>> previousQuestionTokens = previousPayload.stream()
                .map(question -> normalizeQuestion(String.valueOf(question.get("question"))))
                .map(this::questionTokens)
                .toList();
        Set<String> generatedQuestionKeys = new HashSet<>();

        List<GapQuestion> generated = lensAgentClient.generateGapQuestions(
                        sessionId,
                        evidencePayload,
                        previousPayload,
                        answersPayload,
                        round)
                .block(timeout);

        if (generated == null || generated.isEmpty()) {
            throw new RuntimeException("Lens agent returned no gap questions");
        }

        generated = generated.stream()
                .filter(question -> {
                    String normalized = normalizeQuestion(question.getQuestion());
                    Set<String> tokens = questionTokens(normalized);
                    boolean alreadyAsked = previousQuestionTokens.stream()
                            .anyMatch(previousTokens -> isSimilarQuestion(previousTokens, tokens));
                    return !alreadyAsked && generatedQuestionKeys.add(normalized);
                })
                .toList();

        if (generated.isEmpty()) {
            throw new RuntimeException("Lens agent returned only duplicate gap questions");
        }

        LocalDateTime now = LocalDateTime.now();
        generated.forEach(question -> {
            question.setSessionId(sessionId);
            question.setRound(round);
            question.setAskedAt(now);
            question.setAnswered(false);
            question.setSkipped(false);
        });

        gapQuestionRepository.saveAll(generated);
        reviewSessionService.incrementGapRound(sessionId);
        reviewSessionService.transitionStatus(sessionId, ReviewStatus.GAP_ELICITATION);
        return gapQuestionRepository.findBySessionIdAndRoundOrderByAskedAtAsc(sessionId, round);
    }

    @Transactional
    public GapQuestion answerQuestion(UUID sessionId, UUID questionId, String answer, boolean skipped, String userId) {
        reviewSessionService.getSession(sessionId, userId);
        GapQuestion question = gapQuestionRepository.findByIdAndSessionId(questionId, sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Gap question not found"));

        question.setSkipped(skipped);
        if (skipped) {
            question.setAnswered(false);
            question.setAnswer(null);
        } else {
            if (answer == null || answer.isBlank()) {
                throw new BadRequestException("Answer is required unless the question is skipped");
            }
            question.setAnswered(true);
            question.setAnswer(answer.trim());
        }
        question.setAnsweredAt(LocalDateTime.now());
        return gapQuestionRepository.save(question);
    }

    @Transactional(readOnly = true)
    public List<GapQuestion> getQuestionsForCurrentRound(UUID sessionId, String userId) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getGapRound() <= 0) {
            return List.of();
        }
        return gapQuestionRepository.findBySessionIdAndRoundOrderByAskedAtAsc(sessionId, session.getGapRound());
    }

    @Transactional
    public Map<String, Object> assessGaps(UUID sessionId, String userId) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getStatus() != ReviewStatus.GAP_ELICITATION
                && session.getStatus() != ReviewStatus.EVIDENCE_COLLECTION) {
            throw new ConflictException("Gap assessment is only available during gap elicitation");
        }

        List<ArchitectureEvidence> evidence = evidenceIngestionService.listEvidence(sessionId);
        List<GapQuestion> allQuestions = gapQuestionRepository.findBySessionIdOrderByAskedAtAsc(sessionId);

        Map<String, Object> assessment = lensAgentClient.assessGapResolution(
                        sessionId,
                        toEvidencePayload(evidence),
                        allQuestions.stream().map(this::toAssessQuestionPayload).toList(),
                        allQuestions.stream().filter(GapQuestion::isAnswered).map(this::toAnswerPayload).toList(),
                        session.getGapRound(),
                        maxRounds)
                .block(timeout);

        if (assessment == null) {
            throw new RuntimeException("Lens agent returned an empty assessment");
        }

        boolean resolved = asBoolean(assessment.get("resolved"));
        boolean canProceed = asBoolean(assessment.get("canProceed"));
        if (canProceed && (resolved || session.getGapRound() >= maxRounds)) {
            List<String> unresolved = reviewSessionService.forceProceed(sessionId, userId);
            assessment.put("unresolvableGaps", unresolved);
        }
        return assessment;
    }

    @Transactional(readOnly = true)
    public List<GapQuestion> getAllQuestions(UUID sessionId, String userId) {
        reviewSessionService.getSession(sessionId, userId);
        return gapQuestionRepository.findBySessionIdOrderByAskedAtAsc(sessionId);
    }

    private List<Map<String, Object>> toEvidencePayload(List<ArchitectureEvidence> evidence) {
        return evidence.stream().map(item -> {
            Map<String, Object> payload = new HashMap<>();
            payload.put("evidence_type", item.getEvidenceType().name());
            payload.put("content", item.getContent());
            payload.put("source_label", item.getSourceLabel());
            return payload;
        }).toList();
    }

    private Map<String, Object> toPreviousQuestionPayload(GapQuestion question) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("id", question.getId().toString());
        payload.put("category", question.getCategory().name());
        payload.put("question", question.getQuestion());
        payload.put("rationale", question.getRationale());
        return payload;
    }

    private Map<String, Object> toAssessQuestionPayload(GapQuestion question) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("id", question.getId().toString());
        payload.put("category", question.getCategory().name());
        payload.put("question", question.getQuestion());
        payload.put("answered", question.isAnswered());
        payload.put("answer", question.getAnswer());
        payload.put("skipped", question.isSkipped());
        return payload;
    }

    private Map<String, Object> toAnswerPayload(GapQuestion question) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("question_id", question.getId().toString());
        payload.put("answer", question.getAnswer());
        return payload;
    }

    private boolean asBoolean(Object value) {
        if (value instanceof Boolean booleanValue) {
            return booleanValue;
        }
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private String normalizeQuestion(String question) {
        if (question == null) {
            return "";
        }
        return question.toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9 ]", " ")
                .replaceAll("\\b(what|which|how|are|is|the|a|an|in|on|for|to|and|or|of|with|be|been|being)\\b", " ")
                .replaceAll("\\s+", " ")
                .trim();
    }

    private Set<String> questionTokens(String normalizedQuestion) {
        Set<String> tokens = new HashSet<>();
        for (String token : normalizedQuestion.split(" ")) {
            if (!token.isBlank()) {
                tokens.add(canonicalQuestionToken(token));
            }
        }
        return tokens;
    }

    private String canonicalQuestionToken(String token) {
        return switch (token) {
            case "strategies", "mechanisms", "approaches", "approach" -> "strategy";
            case "optimizing", "optimization", "optimized" -> "optimize";
            case "costs" -> "cost";
            case "deploying", "deployment", "deployments", "deployed" -> "deploy";
            case "updates", "updated" -> "update";
            case "managing", "managed", "management" -> "manage";
            case "backups" -> "backup";
            case "tests", "testing", "tested" -> "test";
            default -> token;
        };
    }

    private boolean isSimilarQuestion(Set<String> previousTokens, Set<String> candidateTokens) {
        if (previousTokens.isEmpty() || candidateTokens.isEmpty()) {
            return false;
        }
        Set<String> intersection = new HashSet<>(previousTokens);
        intersection.retainAll(candidateTokens);
        Set<String> union = new HashSet<>(previousTokens);
        union.addAll(candidateTokens);
        return ((double) intersection.size() / (double) union.size()) >= 0.55;
    }
}
