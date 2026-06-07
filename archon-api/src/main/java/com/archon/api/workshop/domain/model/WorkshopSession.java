package com.archon.api.workshop.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Persistent record for one Quality Attribute Workshop session.
 *
 * <p>The full conversation state (WorkshopContext) is stored in
 * {@code context_json} as JSONB. The Python agent receives this
 * on every turn, updates it, and returns the new version for
 * Spring Boot to persist. Spring Boot is the sole owner of
 * persistence; the Python agent is stateless.</p>
 *
 * <p>The {@code workshop_attributes} child records mirror the
 * attribute list from {@code context_json} so that API queries
 * can filter by confidence and category without client-side
 * JSON parsing.</p>
 */
@Entity
@Table(name = "workshop_sessions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class WorkshopSession {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    /** Owning user — JWT subject claim from the security context. */
    @Column(nullable = false)
    private String userId;

    /** System being elicited for, set after the first user input. */
    @Column
    private String systemName;

    /**
     * Current phase in the SEI QAW process.
     * One of: input_analysis, business_context, usage_context,
     * technical_context, risk_priority, scenario_brainstorm,
     * scenario_refinement, attribute_consolidation, validation, complete.
     */
    @Column(nullable = false)
    @Builder.Default
    private String workshopPhase = "input_analysis";

    /**
     * Full WorkshopContext serialised to JSON.
     * This is the authoritative state — workshop_attributes records
     * are a queryable mirror of the attributes list within this column.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    @Builder.Default
    private String contextJson = "{}";

    /** True when the user has confirmed the workshop is complete. */
    @Column(name = "is_complete", nullable = false)
    @Builder.Default
    private boolean complete = false;

    /** Number of conversation turns completed. */
    @Column(nullable = false)
    @Builder.Default
    private int turnCount = 0;

    @OneToMany(mappedBy = "session", cascade = CascadeType.ALL,
               fetch = FetchType.LAZY, orphanRemoval = true)
    @Builder.Default
    private List<WorkshopAttribute> attributes = new ArrayList<>();

    /**
     * SEI QAW utility tree serialised to JSON.
     * Null until the session has sufficient scenarios for generation.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String utilityTree;

    /**
     * Architectural implications serialised to JSON.
     * Null until the utility tree has been generated.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String architectureImplications;

    /**
     * Conversation created when this workshop was sent to the architecture
     * pipeline. Used to suppress rapid duplicate submissions.
     */
    @Column(name = "pipeline_conversation_id")
    private UUID pipelineConversationId;

    /**
     * Time the pipeline conversation was created. A recent value means a
     * retry should return the existing conversation rather than create one.
     */
    @Column(name = "pipeline_sent_at")
    private Instant pipelineSentAt;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(nullable = false)
    private Instant lastUpdated;
}
