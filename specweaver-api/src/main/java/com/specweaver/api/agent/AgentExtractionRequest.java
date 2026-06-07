package com.specweaver.api.agent;

import java.util.List;

/**
 * Request sent to specweaver-agent for batch requirements extraction.
 */
public record AgentExtractionRequest(
        String sessionId,
        List<DocumentPayload> documents
) {
    /**
     * Extracted document payload passed to the agent.
     */
    public record DocumentPayload(
            String documentId,
            String documentType,
            String content,
            String filename,
            String sourceLabel
    ) {}
}
