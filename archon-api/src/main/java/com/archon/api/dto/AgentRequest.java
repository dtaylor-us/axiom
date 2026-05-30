package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;
import java.util.List;
import java.util.Map;

/**
 * Data Transfer Object for agent requests in the Archon API.
 * 
 * This class encapsulates the request payload sent to the agent service,
 * containing conversation context, user input, and execution parameters.
 * 
 * @author Archon
 */
@Data @Builder
public class AgentRequest {
    private String conversationId;
    private String userMessage;
    private String mode;
    private List<MessageDto> history;
    private Map<String, Object> context;
}
