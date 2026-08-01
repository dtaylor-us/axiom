package com.archon.api.workshop.dto;

/**
 * A single node in the SEI QAW utility tree.
 *
 * <p>Each node represents one scenario placed within a quality attribute
 * group and refinement, scored by business importance and technical risk.
 * Nodes with (H,H) or (H,M) scores are architectural drivers.</p>
 */
public record UtilityTreeNodeDto(
        String nodeId,
        String attributeName,
        String refinement,
        String scenarioId,
        String scenarioTitle,
        String businessImportance,
        String technicalRisk,
        String priorityLabel,
        String rationale
) {}
