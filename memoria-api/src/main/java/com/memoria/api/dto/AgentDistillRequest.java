package com.memoria.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.memoria.api.domain.model.Pillar;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record AgentDistillRequest(
        @JsonProperty("session_id")
        String sessionId,
        @JsonProperty("project_id")
        String projectId,
        Pillar pillar,
        @JsonProperty("session_summary")
        String sessionSummary,
        @JsonProperty("session_payload")
        Map<String, Object> sessionPayload,
        @JsonProperty("existing_entries")
        List<Map<String, Object>> existingEntries) {

    public static AgentDistillRequest from(
            UUID sessionId,
            UUID projectId,
            Pillar pillar,
            String sessionSummary,
            Map<String, Object> sessionPayload,
            List<Map<String, Object>> existingEntries) {
        return new AgentDistillRequest(
                sessionId.toString(),
                projectId.toString(),
                pillar,
                sessionSummary,
                sessionPayload,
                existingEntries);
    }
}
