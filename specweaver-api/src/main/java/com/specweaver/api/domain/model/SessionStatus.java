package com.specweaver.api.domain.model;

/**
 * Lifecycle state for a SpecWeaver requirements session.
 */
public enum SessionStatus {
    ACTIVE,
    PROCESSING,
    PACKAGE_READY,
    SENT_TO_ARCHON,
    DELETED
}
