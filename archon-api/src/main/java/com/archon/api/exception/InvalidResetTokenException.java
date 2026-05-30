package com.archon.api.exception;

/**
 * Raised when a password reset token is invalid, expired, or already used.
 */
public class InvalidResetTokenException extends RuntimeException {

    public InvalidResetTokenException(String message) {
        super(message);
    }
}
