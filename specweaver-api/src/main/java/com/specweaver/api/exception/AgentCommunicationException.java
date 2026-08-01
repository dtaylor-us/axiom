package com.specweaver.api.exception;

/**
 * Raised when specweaver-api cannot communicate with specweaver-agent.
 */
public class AgentCommunicationException extends RuntimeException {

    public AgentCommunicationException(String message) {
        super(message);
    }

    public AgentCommunicationException(String message, Throwable cause) {
        super(message, cause);
    }
}
