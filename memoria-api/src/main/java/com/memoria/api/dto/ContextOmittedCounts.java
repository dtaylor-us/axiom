package com.memoria.api.dto;

public record ContextOmittedCounts(
        long stale,
        long superseded,
        long archived,
        long expired,
        long sessionSummaries) {
}
