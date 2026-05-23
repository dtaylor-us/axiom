package com.aiarchitect.api.workshop.exception;

import java.util.UUID;

/**
 * Thrown when the workshop agent does not respond within the turn timeout.
 *
 * <p>The caller's input is preserved (it was sent to the agent and stored
 * in the Spring Boot session before the timeout expired). The HTTP layer
 * maps this to HTTP 504 Gateway Timeout with a {@code draft_preserved: true}
 * flag so the UI can surface a recoverable error to the user.
 */
public class WorkshopTurnTimeoutException extends RuntimeException {

    private final UUID sessionId;

    public WorkshopTurnTimeoutException(UUID sessionId) {
        super("Workshop agent did not respond within the allowed time. session=" + sessionId);
        this.sessionId = sessionId;
    }

    public UUID getSessionId() {
        return sessionId;
    }
}
