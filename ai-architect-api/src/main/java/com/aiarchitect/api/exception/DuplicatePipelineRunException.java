package com.aiarchitect.api.exception;

/**
 * Raised when a conversation already has an active durable pipeline run.
 */
public class DuplicatePipelineRunException extends RuntimeException {

    public DuplicatePipelineRunException(String message) {
        super(message);
    }
}
