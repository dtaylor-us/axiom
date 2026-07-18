package com.memoria.api.exception;

public class DuplicateSessionLinkException extends RuntimeException {
    public DuplicateSessionLinkException(String message) {
        super(message);
    }
}
