package com.lens.api.domain.model;

import java.util.UUID;

public record ReviewFinding(
    UUID id,
    UUID reportId,
    String findingType,
    String category,
    String title,
    String description,
    String evidence,
    String frameworkReference,
    String severity
) {}
