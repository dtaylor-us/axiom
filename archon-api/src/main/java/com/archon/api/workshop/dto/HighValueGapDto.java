package com.archon.api.workshop.dto;

/**
 * An open gap that would materially improve generation quality if filled.
 */
public record HighValueGapDto(
        String gapId,
        String description,
        String impact
) {}
