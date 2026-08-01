package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * Aggregate token usage summary for a conversation.
 */
@Data @Builder
public class UsageSummaryDto {
    private int totalInputTokens;
    private int totalOutputTokens;
    private int totalTokens;
    private BigDecimal estimatedTotalCost;
    private List<TokenUsageDto> stages;
}
