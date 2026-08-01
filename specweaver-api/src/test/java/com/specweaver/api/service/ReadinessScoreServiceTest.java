package com.specweaver.api.service;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ReadinessScoreServiceTest {

    private final ReadinessScoreService readinessScoreService = new ReadinessScoreService();

    @Test
    void compute_returnsOneWhenNoGapsNoConflictsAndAllHighConfidence() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 0, 0, 0, 0);

        assertEquals(new BigDecimal("1.00"), score);
    }

    @Test
    void compute_deductsPerCriticalGap() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 1, 0, 0, 0);

        assertEquals(new BigDecimal("0.85"), score);
    }

    @Test
    void compute_deductsPerHighGap() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 0, 1, 0, 0);

        assertEquals(new BigDecimal("0.92"), score);
    }

    @Test
    void compute_deductsPerConflict() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 0, 0, 0, 1);

        assertEquals(new BigDecimal("0.95"), score);
    }

    @Test
    void compute_deductsWhenInferredRatioExceedsFortyPercent() {
        BigDecimal score = readinessScoreService.compute(5, 3, 3, 0, 0, 0, 0);

        assertEquals(new BigDecimal("0.90"), score);
    }

    @Test
    void compute_deductsWhenZeroHighConfidence() {
        BigDecimal score = readinessScoreService.compute(3, 0, 0, 0, 0, 0, 0);

        assertEquals(new BigDecimal("0.80"), score);
    }

    @Test
    void compute_usesMinimumForNonEmptyPackageWithManyDeductions() {
        BigDecimal score = readinessScoreService.compute(5, 0, 5, 10, 10, 10, 10);

        assertEquals(new BigDecimal("0.10"), score);
    }

    @Test
    void compute_returnsZeroWhenNoRequirements() {
        BigDecimal score = readinessScoreService.compute(0, 0, 0, 10, 10, 10, 10);

        assertEquals(BigDecimal.ZERO, score);
    }

    @Test
    void compute_capsCriticalGapDeduction() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 4, 0, 0, 0);

        assertEquals(new BigDecimal("0.55"), score);
    }

    @Test
    void compute_capsConflictDeduction() {
        BigDecimal score = readinessScoreService.compute(3, 3, 0, 0, 0, 0, 5);

        assertEquals(new BigDecimal("0.80"), score);
    }

    @Test
    void compute_returnsBoundedNonZeroScoreForNonEmptyRequirements() {
        BigDecimal score = readinessScoreService.compute(4, 1, 2, 1, 1, 1, 1);

        assertTrue(score.compareTo(new BigDecimal("0.10")) >= 0);
        assertTrue(score.compareTo(new BigDecimal("1.00")) <= 0);
    }
}
