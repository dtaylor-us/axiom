package com.archon.api.dto;

import com.archon.api.domain.model.ConversationStatus;
import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
public class SessionDto {
    private UUID id;
    private String title;
    private ConversationStatus status;
    private Instant createdAt;
    private Instant updatedAt;
}
