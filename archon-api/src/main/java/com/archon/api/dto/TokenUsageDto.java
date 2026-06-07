package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

/**
 * Per-stage token usage for API responses.
 */
@Data @Builder
public class TokenUsageDto {
    private String stage;
    private String model;
    private int inputTokens;
    private int outputTokens;
    private int totalTokens;
    private BigDecimal estimatedCost;
}
