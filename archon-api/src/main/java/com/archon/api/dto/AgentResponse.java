package com.archon.api.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;
import java.util.Map;

/**
 * AgentResponse represents a response event from an AI agent during processing.
 * 
 * <p>This DTO encapsulates various types of events that can occur during agent execution,
 * including chunk processing, stage transitions, tool invocations, and error handling.
 * 
 * <p>The response can contain different information depending on the event type:
 * <ul>
 *   <li>{@link EventType#CHUNK} - Contains content chunks from processing</li>
 *   <li>{@link EventType#STAGE_START} - Indicates start of a processing stage</li>
 *   <li>{@link EventType#STAGE_COMPLETE} - Indicates completion of a processing stage</li>
 *   <li>{@link EventType#TOOL_CALL} - Contains tool invocation details</li>
 *   <li>{@link EventType#COMPLETE} - Indicates successful completion</li>
 *   <li>{@link EventType#ERROR} - Contains error information</li>
 * </ul>
 * 
 * @see EventType
 */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AgentResponse {
    public enum EventType {
        CHUNK, STAGE_START, STAGE_COMPLETE, TOOL_CALL, COMPLETE, RE_ITERATE, ERROR, RUN_CREATED
    }
    private EventType type;
    private String content;
    private String stage;
    private String toolName;
    private Object payload;
    private String conversationId;
    private Map<String, Object> metadata;
}
