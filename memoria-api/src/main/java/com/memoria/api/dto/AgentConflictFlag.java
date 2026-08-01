package com.memoria.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AgentConflictFlag(
        @JsonProperty("existing_entry_id")
        String existingEntryId,
        @JsonProperty("new_candidate_index")
        int newCandidateIndex,
        @JsonProperty("conflict_description")
        String conflictDescription,
        boolean supersedes) {
}
