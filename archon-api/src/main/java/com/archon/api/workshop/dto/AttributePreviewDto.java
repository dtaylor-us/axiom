package com.archon.api.workshop.dto;

/**
 * Preview of one attribute the generator would produce at the current evidence level.
 */
public record AttributePreviewDto(
        String name,
        String confidence,
        String reason
) {}
