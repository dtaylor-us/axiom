package com.archon.api.workshop.client;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

/**
 * HTTP bridge to the Python Quality Attribute Workshop agent.
 *
 * <p>Isolated so {@link com.archon.api.workshop.service.WorkshopService}
 * can remain unit-testable with mocked ordering (agent call before persistence).</p>
 */
public interface WorkshopAgentClient {

    /**
     * POST /workshop/turn — process one conversational turn.
     *
     * @param payload session_id, user_input, context_json
     * @return parsed JSON body from the agent (updated_context_json, turn_response, ...)
     */
    JsonNode postWorkshopTurn(Map<String, Object> payload);

    /**
     * POST /workshop/summary — final workshop summary for pipeline handoff.
     *
     * @param payload session_id, context_json
     * @return parsed JSON body from the agent
     */
    JsonNode postWorkshopSummary(Map<String, Object> payload);

    /**
     * POST /workshop/assess-readiness — preview generation quality from current evidence.
     *
     * @param payload session_id, context_json
     */
    JsonNode postWorkshopAssessReadiness(Map<String, Object> payload);

    /**
     * POST /workshop/generate — produce attributes from current evidence.
     *
     * @param payload session_id, context_json
     */
    JsonNode postWorkshopGenerate(Map<String, Object> payload);
}
