package com.lens.api.service;

import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class ReviewSessionService {

    private final Map<UUID, ReviewSession> sessions = new LinkedHashMap<>();

    public ReviewSession createSession(String title, String systemDescription) {
        UUID id = UUID.randomUUID();
        ReviewSession session = new ReviewSession(
            id,
            UUID.randomUUID(),
            title == null || title.isBlank() ? "Untitled review" : title,
            systemDescription,
            ReviewStatus.EVIDENCE_COLLECTION,
            0,
            false,
            LocalDateTime.now(),
            LocalDateTime.now()
        );
        sessions.put(id, session);
        return session;
    }

    public List<ReviewSession> listSessions() {
        return new ArrayList<>(sessions.values());
    }

    public ReviewSession getSession(UUID id) {
        return sessions.get(id);
    }

    public void deleteSession(UUID id) {
        sessions.remove(id);
    }

    public ReviewSession updateSession(ReviewSession session) {
        sessions.put(session.id(), session);
        return session;
    }
}
