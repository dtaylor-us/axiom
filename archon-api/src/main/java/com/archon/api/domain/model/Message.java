package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.Instant;
import java.util.UUID;

/**
 * Represents a message in a conversation within the Archon system.
 * 
 * This entity stores individual messages exchanged in a conversation, including
 * the sender's role, content, and optional structured output along with token usage metrics.
 * Messages are immutable after creation and are linked to their parent conversation.
 * 
 * @author Archon
 * @version 1.0
 */
@Entity @Table(name = "messages")
@Data @Builder @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Message {

    @Id @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id", nullable = false)
    private Conversation conversation;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private MessageRole role;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String structuredOutput;

    private String model;
    private Integer inputTokens;
    private Integer outputTokens;

    @CreationTimestamp private Instant createdAt;
}
