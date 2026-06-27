package com.lens.api.service;

import com.lens.api.domain.model.GapQuestion;
import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;
import com.lens.api.exception.ResourceNotFoundException;
import com.lens.api.repository.ArchitectureEvidenceRepository;
import com.lens.api.repository.GapQuestionRepository;
import com.lens.api.repository.ReviewFindingRepository;
import com.lens.api.repository.ReviewReportRepository;
import com.lens.api.repository.ReviewRiskRepository;
import com.lens.api.repository.ReviewSessionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class ReviewSessionService {

    private static final String DEFAULT_TITLE = "Untitled review";

    private final ReviewSessionRepository reviewSessionRepository;
    private final GapQuestionRepository gapQuestionRepository;
    private final ArchitectureEvidenceRepository evidenceRepository;
    private final ReviewReportRepository reviewReportRepository;
    private final ReviewFindingRepository reviewFindingRepository;
    private final ReviewRiskRepository reviewRiskRepository;

    public ReviewSessionService(
            ReviewSessionRepository reviewSessionRepository,
            GapQuestionRepository gapQuestionRepository,
            ArchitectureEvidenceRepository evidenceRepository,
            ReviewReportRepository reviewReportRepository,
            ReviewFindingRepository reviewFindingRepository,
            ReviewRiskRepository reviewRiskRepository) {
        this.reviewSessionRepository = reviewSessionRepository;
        this.gapQuestionRepository = gapQuestionRepository;
        this.evidenceRepository = evidenceRepository;
        this.reviewReportRepository = reviewReportRepository;
        this.reviewFindingRepository = reviewFindingRepository;
        this.reviewRiskRepository = reviewRiskRepository;
    }

    @Transactional
    public ReviewSession createSession(String userId, String title, String systemDescription) {
        LocalDateTime now = LocalDateTime.now();
        ReviewSession session = new ReviewSession();
        session.setId(UUID.randomUUID());
        session.setUserId(toStableUserId(userId));
        session.setTitle(normalizeTitle(title));
        session.setSystemDescription(systemDescription);
        session.setStatus(ReviewStatus.EVIDENCE_COLLECTION);
        session.setGapRound(0);
        session.setGapsResolved(false);
        session.setCreatedAt(now);
        session.setUpdatedAt(now);
        return reviewSessionRepository.save(session);
    }

    @Transactional(readOnly = true)
    public ReviewSession getSession(UUID sessionId, String userId) {
        return reviewSessionRepository.findByIdAndUserId(sessionId, toStableUserId(userId))
                .orElseThrow(() -> new ResourceNotFoundException("Review session not found"));
    }

    @Transactional(readOnly = true)
    public List<ReviewSession> listSessions(String userId) {
        return reviewSessionRepository.findByUserIdOrderByCreatedAtDesc(toStableUserId(userId));
    }

    @Transactional
    public void deleteSession(UUID sessionId, String userId) {
        ReviewSession session = getSession(sessionId, userId);
        reviewReportRepository.findBySessionId(session.getId()).ifPresent(report -> {
            reviewFindingRepository.deleteByReportId(report.getId());
            reviewRiskRepository.deleteByReportId(report.getId());
        });
        reviewReportRepository.deleteBySessionId(session.getId());
        evidenceRepository.deleteBySessionId(session.getId());
        gapQuestionRepository.deleteBySessionId(session.getId());
        reviewSessionRepository.delete(session);
    }

    @Transactional
    public ReviewSession updateSession(UUID sessionId, String userId, String title, String systemDescription) {
        ReviewSession session = getSession(sessionId, userId);
        session.setTitle(normalizeTitle(title));
        session.setSystemDescription(systemDescription == null ? "" : systemDescription.trim());
        session.setUpdatedAt(LocalDateTime.now());
        return reviewSessionRepository.save(session);
    }

    @Transactional
    public ReviewSession transitionStatus(UUID sessionId, ReviewStatus newStatus) {
        ReviewSession session = requireSession(sessionId);
        session.setStatus(newStatus);
        session.setUpdatedAt(LocalDateTime.now());
        return reviewSessionRepository.save(session);
    }

    @Transactional
    public ReviewSession incrementGapRound(UUID sessionId) {
        ReviewSession session = requireSession(sessionId);
        session.setGapRound(session.getGapRound() + 1);
        session.setUpdatedAt(LocalDateTime.now());
        return reviewSessionRepository.save(session);
    }

    @Transactional
    public List<String> forceProceed(UUID sessionId, String userId) {
        ReviewSession session = getSession(sessionId, userId);
        session.setGapsResolved(true);
        session.setStatus(ReviewStatus.READY_FOR_REVIEW);
        session.setUpdatedAt(LocalDateTime.now());
        reviewSessionRepository.save(session);

        List<GapQuestion> unanswered = gapQuestionRepository.findBySessionIdOrderByAskedAtAsc(sessionId)
                .stream()
                .filter(question -> question.isSkipped()
                        || !question.isAnswered()
                        || question.getAnswer() == null
                        || question.getAnswer().isBlank())
                .toList();

        return unanswered.stream().map(GapQuestion::getQuestion).toList();
    }

    @Transactional(readOnly = true)
    public ReviewSession requireSession(UUID sessionId) {
        return reviewSessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Review session not found"));
    }

    private UUID toStableUserId(String userId) {
        try {
            return UUID.fromString(userId);
        } catch (IllegalArgumentException ignored) {
            return UUID.nameUUIDFromBytes(userId.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
    }

    private String normalizeTitle(String title) {
        if (title == null || title.isBlank()) {
            return DEFAULT_TITLE;
        }
        return title.trim();
    }
}
