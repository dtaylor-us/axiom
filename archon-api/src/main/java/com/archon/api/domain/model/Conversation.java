package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Represents a conversation entity in the system.
 * 
 * A conversation is a container for a series of messages exchanged within a specific context.
 * Each conversation belongs to a user and maintains a status to track its lifecycle.
 * Messages within a conversation are ordered chronologically by creation timestamp.
 * 
 * Entity Mapping:
 * - Table Name: conversations
 * - Primary Key: id (UUID)
 * 
 * Relationships:
 * - One-to-Many with Message: A conversation contains multiple messages
 *   (cascade delete enabled, lazy loaded)
 * 
 * Status Tracking:
 * - Default status: ACTIVE
 * - Status can be modified during the conversation lifecycle
 * 
 * Timestamps:
 * - createdAt: Automatically set when the conversation is created
 * - updatedAt: Automatically updated on each modification
 */
@Entity @Table(name = "conversations")
@Data @Builder @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Conversation {

    @Id @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @Column(nullable = false) private String userId;
    @Column(nullable = false) private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private ConversationStatus status = ConversationStatus.ACTIVE;

    @OneToMany(mappedBy = "conversation", cascade = CascadeType.ALL,
               fetch = FetchType.LAZY)
    @OrderBy("createdAt ASC")
    @Builder.Default
    private List<Message> messages = new ArrayList<>();

    @CreationTimestamp private Instant createdAt;
    @UpdateTimestamp   private Instant updatedAt;
}
