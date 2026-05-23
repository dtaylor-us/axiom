package com.aiarchitect.api.exception;

/**
 * Raised when a submitted password does not meet Archon's policy.
 */
public class PasswordValidationException extends RuntimeException {

    public PasswordValidationException(String message) {
        super(message);
    }
}
