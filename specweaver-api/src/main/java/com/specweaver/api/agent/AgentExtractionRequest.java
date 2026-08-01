package com.specweaver.api.agent;

import java.util.List;
import java.util.Map;

/**
 * Request sent to specweaver-agent for batch requirements extraction.
 */
public record AgentExtractionRequest(
        String sessionId,
        List<DocumentPayload> documents,
        Map<String, Object> projectMemoryContext
) {
    public AgentExtractionRequest(String sessionId, List<DocumentPayload> documents) {
        this(sessionId, documents, null);
    }

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
