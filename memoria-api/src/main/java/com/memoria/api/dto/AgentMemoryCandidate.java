package com.memoria.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record AgentMemoryCandidate(
        @JsonProperty("memory_type")
        String memoryType,
        String content,
        String rationale,
        String confidence,
        @JsonProperty("source_excerpt")
        String sourceExcerpt,
        List<String> tags) {
}
