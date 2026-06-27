package com.lens.api.domain.model;

import java.util.UUID;

public record ReviewRisk(
    UUID id,
    UUID reportId,
    String title,
    String description,
    String severity,
    String likelihood,
    String affectedArea,
    String mitigationStrategy,
    String frameworkReference
) {}
