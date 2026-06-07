package com.specweaver.api.exception;

/**
 * Raised when no generated package exists for a session.
 */
public class PackageNotFoundException extends RuntimeException {

    public PackageNotFoundException(String message) {
        super(message);
    }
}
