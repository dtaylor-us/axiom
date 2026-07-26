package com.memoria.api.dto;

import jakarta.validation.constraints.AssertTrue;

public record UpdateProjectRequest(
        String name,
        String description) {

    @AssertTrue(message = "At least one field must be provided")
    public boolean hasAtLeastOneField() {
        return name != null || description != null;
    }
}
