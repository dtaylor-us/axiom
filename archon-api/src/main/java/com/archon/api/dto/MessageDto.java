package com.archon.api.dto;

import com.archon.api.domain.model.MessageRole;
import lombok.Builder;
import lombok.Data;
import java.time.Instant;
import java.util.UUID;

/**
 * Data Transfer Object for representing a message in the Archon API.
 * 
 * <p>This DTO encapsulates message information exchanged within the system,
 * including metadata such as the message identifier, role, content, and timestamp.
 * 
 * @since 1.0.0
 */
@Data @Builder
public class MessageDto {
    private UUID id;
    private MessageRole role;
    private String content;
    private Instant createdAt;
}
