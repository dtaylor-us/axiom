package com.archon.api.dto;

import java.util.List;

public record BuyVsBuildSummaryDto(
        String summaryText,
        int totalDecisions,
        int buildCount,
        int buyCount,
        int adoptCount,
        int conflictCount,
        List<BuyVsBuildDecisionDto> decisions
) {}

