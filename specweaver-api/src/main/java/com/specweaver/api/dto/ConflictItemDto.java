package com.specweaver.api.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Unresolved contradiction between requirements found by SpecWeaver Phase 1b.
 *
 * @author OpenAI
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ConflictItemDto(
        String conflictId,
        List<String> requirementIds,
        String description,
        List<String> interpretations,
        String clarificationQuestion
) {
}
