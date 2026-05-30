package com.archon.api.service;

import com.archon.api.client.AgentHttpClient;
import com.archon.api.dto.AgentRequest;
import com.archon.api.dto.AgentResponse;
import com.archon.api.exception.AgentCommunicationException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;

/**
 * Service that bridges communication with the Agent API.
 * Handles streaming responses and JSON parsing with error handling.
 */
@Service @RequiredArgsConstructor @Slf4j
public class AgentBridgeService {

    private final AgentHttpClient agentHttpClient;
    private final ObjectMapper objectMapper;

    /**
     * Streams agent responses as a Flux of parsed AgentResponse objects.
     * 
     * @param request the agent request to send
     * @return a Flux of parsed responses
     */
    public Flux<AgentResponse> stream(AgentRequest request) {
        return agentHttpClient.stream(request)
                // Drop SSE keepalive comments (": heartbeat") and blank lines
                // BEFORE map() — Reactor map() must never receive a line that
                // would produce a null, as returning null from map() throws NPE.
                .filter(line -> line != null && !line.isBlank() && !line.startsWith(":"))
                // Parse each qualifying line into an AgentResponse
                .map(this::parseLine)
                // Convert non-AgentCommunicationException errors to AgentCommunicationException
                .onErrorMap(
                    e -> !(e instanceof AgentCommunicationException),
                    e -> new AgentCommunicationException(
                             "Agent stream failed", e));
    }

    /**
     * Parses a JSON line into an AgentResponse object.
     * Returns an ERROR-typed response if parsing fails.
     * Never returns null — blank/comment lines must be filtered upstream.
     *
     * @param line the JSON string to parse (non-null, non-blank, non-comment)
     * @return parsed AgentResponse or error response on failure
     */
    private AgentResponse parseLine(String line) {
        try {
            return objectMapper.readValue(line, AgentResponse.class);
        } catch (JsonProcessingException e) {
            log.warn("Unparseable agent chunk: {}", line);
            AgentResponse err = new AgentResponse();
            err.setType(AgentResponse.EventType.ERROR);
            err.setContent("Parse error on agent response");
            return err;
        }
    }
}
