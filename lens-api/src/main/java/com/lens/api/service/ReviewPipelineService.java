package com.lens.api.service;

import com.lens.api.client.LensAgentClient;
import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.domain.model.GapQuestion;
import com.lens.api.domain.model.ReviewReport;
import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;
import com.lens.api.exception.ConflictException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Service
@Slf4j
public class ReviewPipelineService {

    private final LensAgentClient lensAgentClient;
    private final ReviewSessionService reviewSessionService;
    private final EvidenceIngestionService evidenceIngestionService;
    private final GapElicitationService gapElicitationService;
    private final ReviewReportService reviewReportService;
    private final MemoriaNotificationClient memoriaNotificationClient;
    private final Duration timeout;

    public ReviewPipelineService(
            LensAgentClient lensAgentClient,
            ReviewSessionService reviewSessionService,
            EvidenceIngestionService evidenceIngestionService,
            GapElicitationService gapElicitationService,
            ReviewReportService reviewReportService,
            MemoriaNotificationClient memoriaNotificationClient,
            @Value("${lens.agent.timeout-seconds:${AGENT_TIMEOUT_SECONDS:300}}") int timeoutSeconds) {
        this.lensAgentClient = lensAgentClient;
        this.reviewSessionService = reviewSessionService;
        this.evidenceIngestionService = evidenceIngestionService;
        this.gapElicitationService = gapElicitationService;
        this.reviewReportService = reviewReportService;
        this.memoriaNotificationClient = memoriaNotificationClient;
        this.timeout = Duration.ofSeconds(timeoutSeconds);
    }

    public ReviewReport startReview(UUID sessionId, String userId) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getStatus() != ReviewStatus.READY_FOR_REVIEW) {
            throw new ConflictException("Session must be READY_FOR_REVIEW before starting review");
        }

        reviewSessionService.transitionStatus(sessionId, ReviewStatus.IN_REVIEW);

        try {
            var evidence = evidenceIngestionService.listEvidence(sessionId);
            var allQuestions = gapElicitationService.getAllQuestions(sessionId, userId);

            var insufficientInfoGaps = allQuestions.stream()
                    .filter(question -> question.isSkipped()
                            || !question.isAnswered()
                            || question.getAnswer() == null
                            || question.getAnswer().isBlank())
                    .map(GapQuestion::getQuestion)
                    .toList();
            var memoriaContext = memoriaNotificationClient.fetchSessionContext(sessionId);

            var reportPayload = lensAgentClient.runReview(
                            sessionId,
                            session.getSystemDescription(),
                            evidence.stream().map(this::toEvidencePayload).toList(),
                            allQuestions.stream().map(this::toGapQuestionPayload).toList(),
                            allQuestions.stream().filter(GapQuestion::isAnswered).map(this::toGapAnswerPayload).toList(),
                            insufficientInfoGaps,
                            memoriaContext == null ? null : memoriaContext.orElse(null))
                    .block(timeout);

            if (reportPayload == null) {
                throw new RuntimeException("Lens agent returned an empty review report");
            }

            ReviewReport savedReport = reviewReportService.saveReport(sessionId, reportPayload);
            reviewSessionService.transitionStatus(sessionId, ReviewStatus.COMPLETE);
            memoriaNotificationClient.notifyReviewComplete(sessionId, savedReport);
            return savedReport;
        } catch (RuntimeException ex) {
            reviewSessionService.transitionStatus(sessionId, ReviewStatus.READY_FOR_REVIEW);
            log.error("Lens review pipeline failed for session {}", sessionId, ex);
            throw new RuntimeException("Lens review pipeline failed for session " + sessionId, ex);
        }
    }

    private Map<String, Object> toEvidencePayload(ArchitectureEvidence evidence) {
        HashMap<String, Object> payload = new HashMap<>();
        payload.put("evidence_type", evidence.getEvidenceType().name());
        payload.put("content", evidence.getContent());
        payload.put("source_label", evidence.getSourceLabel());
        return payload;
    }

    private Map<String, Object> toGapQuestionPayload(GapQuestion question) {
        HashMap<String, Object> payload = new HashMap<>();
        payload.put("id", question.getId().toString());
        payload.put("category", question.getCategory().name());
        payload.put("question", question.getQuestion());
        payload.put("answered", question.isAnswered());
        payload.put("answer", question.getAnswer());
        payload.put("skipped", question.isSkipped());
        return payload;
    }

    private Map<String, Object> toGapAnswerPayload(GapQuestion question) {
        HashMap<String, Object> payload = new HashMap<>();
        payload.put("question_id", question.getId().toString());
        payload.put("answer", question.getAnswer());
        return payload;
    }
}
