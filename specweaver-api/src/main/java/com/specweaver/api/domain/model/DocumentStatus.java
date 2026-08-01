package com.specweaver.api.domain.model;

/**
 * Processing state for a document attached to a SpecWeaver session.
 */
public enum DocumentStatus {
    PENDING,
    PROCESSING,
    EXTRACTED,
    FAILED
}
