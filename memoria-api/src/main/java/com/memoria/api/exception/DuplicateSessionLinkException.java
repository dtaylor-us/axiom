package com.memoria.api.exception;

import java.util.UUID;

public class DuplicateSessionLinkException extends RuntimeException {
    private final UUID projectId;
    private final String projectName;

    public DuplicateSessionLinkException(String message, UUID projectId, String projectName) {
        super(message);
        this.projectId = projectId;
        this.projectName = projectName;
    }

    public UUID getProjectId() {
        return projectId;
    }

    public String getProjectName() {
        return projectName;
    }
}
