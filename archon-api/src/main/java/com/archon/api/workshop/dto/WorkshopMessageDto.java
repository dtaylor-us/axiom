package com.archon.api.workshop.dto;

import java.time.Instant;
import java.util.UUID;

/**
 * One message in a workshop conversation thread.
 *
 * <p>Returned as part of session detail responses so the UI can
 * render the full conversation history without re-processing
 * context_json on the client.</p>
 */
public record WorkshopMessageDto(
        UUID messageId,
        int turnNumber,
        String userInput,
        String agentResponse,
        String workshopPhase,
        Instant createdAt
) {}
