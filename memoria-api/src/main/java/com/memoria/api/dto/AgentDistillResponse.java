package com.memoria.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record AgentDistillResponse(
        @JsonProperty("session_id")
        String sessionId,
        List<AgentMemoryCandidate> candidates,
        List<AgentConflictFlag> conflicts,
        String message) {
}
