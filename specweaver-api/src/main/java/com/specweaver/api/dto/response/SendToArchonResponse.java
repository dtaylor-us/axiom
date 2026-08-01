package com.specweaver.api.dto.response;

/**
 * Response returned after retrieving a package brief for manual Archon handoff.
 */
public record SendToArchonResponse(String briefText) {
}
