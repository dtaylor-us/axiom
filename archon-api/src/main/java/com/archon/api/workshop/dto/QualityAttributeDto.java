package com.archon.api.workshop.dto;

import java.util.List;

/**
 * One quality attribute derived during a workshop session.
 *
 * <p>Used in both the turn response (right panel) and the
 * dedicated GET /attributes endpoint. Contains everything the
 * UI needs to render an AttributeCard without parsing JSON.</p>
 */
public record QualityAttributeDto(
        String attributeId,
        String name,
        String category,
        String importance,

        /**
         * Evidence quality: confirmed | inferred | tentative.
         * Determines the badge colour on the AttributeCard.
         */
        String confidence,

        String description,

        /**
         * Completeness of the primary scenario:
         * complete | partial | needs_measure | aspirational.
         */
        String scenarioCompleteness,

        /**
         * Questions still needed to fully ground this attribute.
         * Shown in the expandable section of the AttributeCard.
         */
        List<String> openQuestions,

        /**
         * Verbatim phrases from user input that support this attribute.
         * Shown when the user expands the evidence section.
         */
        List<String> evidenceQuotes,

        /** First user-triggered generation pass that created this attribute, if any. */
        Integer firstGenerationPass,

        /** Most recent generation pass that updated this attribute, if any. */
        Integer lastGenerationPass,

        List<ResolvedAnswerDto> resolvedAnswers,

        int questionsResolvedCount,

        String lastUpdateSummary,

        Integer lastUpdatedTurn
) {}
