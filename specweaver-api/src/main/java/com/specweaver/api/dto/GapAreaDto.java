package com.specweaver.api.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Missing requirement area identified by SpecWeaver Phase 1b.
 *
 * @author OpenAI
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record GapAreaDto(
        String gapId,
        String area,
        String severity,
        String explanation,
        String clarificationQuestion,
        List<String> affectedCategories
) {
}
