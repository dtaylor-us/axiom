package com.archon.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
public class BuyVsBuildDecisionDto {

    private UUID id;
    private UUID conversationId;
    private String componentName;
    private String recommendation;
    private String rationale;
    private List<String> alternativesConsidered;
    private String recommendedSolution;
    private String estimatedBuildCost;
    private String vendorLockInRisk;
    private String integrationEffort;
    private boolean conflictsWithUserPreference;
    private String conflictExplanation;

    /**
     * Keep the JSON field name aligned with the UI contract (including the
     * historical typo "Coree").
     */
    @JsonProperty("isCoreeDifferentiator")
    private boolean isCoreeDifferentiator;

    private Instant createdAt;
}

