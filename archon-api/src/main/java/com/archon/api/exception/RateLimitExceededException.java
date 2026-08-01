package com.archon.api.exception;

/**
 * Raised when a caller exceeds the password-reset request limit.
 */
public class RateLimitExceededException extends RuntimeException {

    public RateLimitExceededException(String message) {
        super(message);
    }
}
