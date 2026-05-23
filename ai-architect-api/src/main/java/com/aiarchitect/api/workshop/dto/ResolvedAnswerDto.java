package com.aiarchitect.api.workshop.dto;

/**
 * One resolved open question on a quality attribute, with evidence traceability.
 */
public record ResolvedAnswerDto(
        String question,
        String answer,
        int resolvedInTurn,
        String evidenceQuote
) {}
