package com.specweaver.api.agent;

/**
 * Response from specweaver-agent containing a serialized ArchInputPackage.
 */
public record AgentExtractionResponse(
        String sessionId,
        String archInputPackageJson,
        boolean success,
        String errorMessage
) {}
