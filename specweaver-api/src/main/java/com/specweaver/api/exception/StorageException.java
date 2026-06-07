package com.specweaver.api.exception;

/**
 * Raised when document blob storage fails.
 */
public class StorageException extends RuntimeException {

    public StorageException(String message, Throwable cause) {
        super(message, cause);
    }
}
