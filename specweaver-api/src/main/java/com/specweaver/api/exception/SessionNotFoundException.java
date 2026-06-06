package com.specweaver.api.exception;

/**
 * Raised when a session is absent or no longer visible to the caller.
 */
public class SessionNotFoundException extends RuntimeException {

    public SessionNotFoundException(String message) {
        super(message);
    }
}
