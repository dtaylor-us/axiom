package com.aiarchitect.api.workshop.dto;

import java.util.List;

/**
 * Final attribute summary from POST /sessions/{id}/complete.
 *
 * <p>This summary is the structured output of the entire workshop.
 * It is also the input to the pipeline bridge — the
 * send-to-pipeline endpoint formats this into natural language
 * requirements and creates a new Conversation for the main
 * architecture pipeline.</p>
 */
public record AttributeSummaryDto(
        String systemDescription,
        List<SummaryAttributeDto> qualityAttributes,
        List<String> openQuestions,
        String elicitationCompleteness,
        String completenessRationale,
        boolean readyForArchitecturePipeline,
        String pipelineReadinessNotes
) {

    /**
     * One quality attribute in the final summary.
     *
     * <p>Contains the scenario for the send-to-pipeline formatter,
     * which extracts the response_measure to produce measurable
     * requirements statements.</p>
     *
     * @param name        canonical attribute name
     * @param importance  critical | high | medium | low
     * @param confidence  confirmed | inferred | tentative
     * @param description system-specific description
     * @param scenario    six-part QA scenario
     * @param evidence    summary of supporting evidence
     */
    public record SummaryAttributeDto(
            String name,
            String importance,
            String confidence,
            String category,
            String description,
            ScenarioDto scenario,
            String evidence
    ) {}

    /**
     * Six-part QA scenario from Bass, Clements, Kazman.
     *
     * @param stimulus        what triggers the quality concern
     * @param source          who or what generates the stimulus
     * @param environment     conditions under which this occurs
     * @param artifact        which part of the system is affected
     * @param response        what the system must do
     * @param responseMeasure how to know if the response is adequate
     * @param completeness    complete | partial | needs_measure | aspirational
     */
    public record ScenarioDto(
            String stimulus,
            String source,
            String environment,
            String artifact,
            String response,
            String responseMeasure,
            String completeness
    ) {}
}
