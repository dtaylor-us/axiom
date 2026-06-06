package com.specweaver.api.dto.response;

import java.util.UUID;

/**
 * Response returned when package generation is accepted.
 */
public record GeneratePackageResponse(UUID packageId) {}
