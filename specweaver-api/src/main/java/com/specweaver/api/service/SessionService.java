package com.specweaver.api.service;

import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionStatus;
import com.specweaver.api.dto.request.CreateSessionRequest;
import com.specweaver.api.dto.request.UpdateSessionRequest;
import com.specweaver.api.dto.response.SessionResponse;
import com.specweaver.api.exception.SessionNotFoundException;
import com.specweaver.api.repository.SessionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * Coordinates the lifecycle of user-owned SpecWeaver sessions.
 *
 * @author OpenAI
 */
@Service
@RequiredArgsConstructor
public class SessionService {

    private final SessionRepository sessionRepository;

    /**
     * Creates a new active session for the authenticated user.
     *
     * @param request session creation request
     * @param userId authenticated user ID
     * @return created session response
     */
    @Transactional
    public SessionResponse createSession(CreateSessionRequest request, UUID userId) {
        Session session = Session.builder()
                .userId(userId)
                .title(normalizeTitle(request == null ? null : request.title()))
                .status(SessionStatus.ACTIVE)
                .build();
        return ResponseMapper.toSessionResponse(sessionRepository.save(session), false);
    }

    /**
     * Updates the editable title for a user-owned session.
     *
     * @param sessionId session identifier
     * @param userId authenticated user ID
     * @param request mutable session fields
     * @return updated session response
     */
    @Transactional
    public SessionResponse updateSessionTitle(UUID sessionId, UUID userId, UpdateSessionRequest request) {
        Session session = requireOwnedSession(sessionId, userId);
        session.setTitle(normalizeTitle(request.title()));
        return ResponseMapper.toSessionResponse(sessionRepository.save(session), false);
    }

    @Transactional(readOnly = true)
    public List<SessionResponse> listSessions(UUID userId) {
        return sessionRepository.findByUserIdAndStatusNotOrderByCreatedAtDesc(userId, SessionStatus.DELETED)
                .stream()
                .map(session -> ResponseMapper.toSessionResponse(session, false))
                .toList();
    }

    @Transactional(readOnly = true)
    public SessionResponse getSession(UUID sessionId, UUID userId) {
        return ResponseMapper.toSessionResponse(requireOwnedSession(sessionId, userId), true);
    }

    @Transactional
    public void deleteSession(UUID sessionId, UUID userId) {
        Session session = requireOwnedSession(sessionId, userId);
        session.setStatus(SessionStatus.DELETED);
        sessionRepository.save(session);
    }

    @Transactional(readOnly = true)
    public Session requireOwnedSession(UUID sessionId, UUID userId) {
        Session session = sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED)
                .orElseThrow(() -> new SessionNotFoundException("Session not found"));
        if (!session.getUserId().equals(userId)) {
            throw new AccessDeniedException("Session belongs to a different user");
        }
        return session;
    }

    private String normalizeTitle(String title) {
        if (title == null) {
            return null;
        }
        String trimmedTitle = title.trim();
        return trimmedTitle.isEmpty() ? null : trimmedTitle;
    }
}
