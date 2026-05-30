package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class TacticsSummaryDto {

    /** Total number of recommended tactics stored. */
    private int totalTactics;

    /** Number of tactics with priority = "critical". */
    private int criticalCount;

    /** Number of tactics already addressed in the existing design. */
    private int alreadyAddressedCount;

    /** Number of net-new tactics to be implemented. */
    private int newTacticsCount;

    /**
     * Tactic counts per characteristic, keyed by characteristic name.
     * Example: {"availability": 3, "performance": 2}
     */
    private Map<String, Long> perCharacteristic;

    /**
     * Natural-language summary produced by the tactics advisor,
     * describing the overall tactic landscape for this system.
     */
    private String summary;

    /**
     * The three highest-priority unaddressed tactic names, for use in
     * the ArchitectureView critical-tactics sidebar.
     */
    private List<String> topCriticalTactics;
}
