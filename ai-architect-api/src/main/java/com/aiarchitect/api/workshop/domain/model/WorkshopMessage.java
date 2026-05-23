package com.aiarchitect.api.workshop.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.UUID;

/**
 * One message entry in a workshop session conversation.
 *
 * <p>Messages are append-only and record the conversation thread
 * visible in the UI. Agent messages and user responses alternate.
 * The full turn state is redundantly stored in
 * {@link WorkshopSession#getContextJson()}, but this table provides
 * a queryable, readable conversation history.</p>
 */
@Entity
@Table(name = "workshop_messages")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class WorkshopMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    /** Owning session. */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "session_id", nullable = false)
    private WorkshopSession session;

    /** Monotonically increasing turn number within the session. */
    @Column(nullable = false)
    private int turnNumber;

    /** The user's input for this turn. */
    @Column(columnDefinition = "text", nullable = false)
    private String userInput;

    /** The agent's response for this turn. */
    @Column(columnDefinition = "text", nullable = false)
    private String agentResponse;

    /**
     * Workshop phase active during this turn.
     * One of the QAW phase identifiers from WorkshopContext.workshop_phase.
     */
    @Column(nullable = false)
    private String workshopPhase;

    @CreationTimestamp
    @Column(nullable = false)
    private Instant createdAt;
}
