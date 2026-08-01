package com.specweaver.api.service;

import java.math.BigDecimal;
import java.math.RoundingMode;

import org.springframework.stereotype.Service;

/**
 * Computes the readiness score for an ArchInputPackage.
 *
 * @author OpenAI
 */
@Service
public class ReadinessScoreService {

    private static final double BASE_SCORE = 1.0;
    private static final double CRITICAL_GAP_DEDUCTION = 0.15;
    private static final double MAX_CRITICAL_GAP_DEDUCTION = 0.45;
    private static final double HIGH_GAP_DEDUCTION = 0.08;
    private static final double MAX_HIGH_GAP_DEDUCTION = 0.24;
    private static final double MEDIUM_GAP_DEDUCTION = 0.03;
    private static final double MAX_MEDIUM_GAP_DEDUCTION = 0.09;
    private static final double CONFLICT_DEDUCTION = 0.05;
    private static final double MAX_CONFLICT_DEDUCTION = 0.20;
    private static final double WEAK_EVIDENCE_RATIO = 0.4;
    private static final double WEAK_EVIDENCE_DEDUCTION = 0.10;
    private static final double NO_HIGH_CONFIDENCE_DEDUCTION = 0.20;
    private static final double MINIMUM_NON_EMPTY_SCORE = 0.10;
    private static final int SCORE_SCALE = 2;

    /**
     * Computes a normalized score from requirement evidence quality and Phase 1b findings.
     */
    public BigDecimal compute(
            int totalRequirements,
            int highConfidenceCount,
            int inferredCount,
            int criticalGaps,
            int highGaps,
            int mediumGaps,
            int conflictCount
    ) {
        if (totalRequirements == 0) {
            return BigDecimal.ZERO;
        }

        double score = BASE_SCORE;

        score -= Math.min(criticalGaps * CRITICAL_GAP_DEDUCTION, MAX_CRITICAL_GAP_DEDUCTION);
        score -= Math.min(highGaps * HIGH_GAP_DEDUCTION, MAX_HIGH_GAP_DEDUCTION);
        score -= Math.min(mediumGaps * MEDIUM_GAP_DEDUCTION, MAX_MEDIUM_GAP_DEDUCTION);
        score -= Math.min(conflictCount * CONFLICT_DEDUCTION, MAX_CONFLICT_DEDUCTION);

        double inferredRatio = (double) inferredCount / totalRequirements;
        if (inferredRatio > WEAK_EVIDENCE_RATIO) {
            score -= WEAK_EVIDENCE_DEDUCTION;
        }

        if (highConfidenceCount == 0) {
            score -= NO_HIGH_CONFIDENCE_DEDUCTION;
        }

        score = Math.max(score, MINIMUM_NON_EMPTY_SCORE);
        return BigDecimal.valueOf(score).setScale(SCORE_SCALE, RoundingMode.HALF_UP);
    }
}
