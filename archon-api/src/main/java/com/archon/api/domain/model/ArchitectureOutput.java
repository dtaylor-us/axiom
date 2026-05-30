package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/**
 * Entity representing the output of an AI-generated architecture.
 * Stores architecture details including components, interactions, diagrams, and metadata.
 */
@Entity
@Table(name = "architecture_outputs")
@Data @Builder @NoArgsConstructor @AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class ArchitectureOutput {

    /** Unique identifier for this architecture output */
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    /** References the conversation this output belongs to */
    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    /** Architecture style (e.g., microservices, monolithic) */
    private String style;

    /** Domain or business context */
    private String domain;

    /** Type of system being architected */
    @Column(name = "system_type")
    private String systemType;

    /** Count of components in the architecture */
    @Column(name = "component_count", nullable = false)
    @Builder.Default
    private int componentCount = 0;

    /** JSON representation of architecture components */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String components;

    /** JSON representation of interactions between components */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String interactions;

    /** JSON representation of architecture characteristics */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String characteristics;

    /** JSON representation of architectural conflicts or trade-offs */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String conflicts;

    /** Component diagram in text/diagram format */
    @Column(name = "component_diagram", columnDefinition = "TEXT")
    private String componentDiagram;

    /** Sequence diagram in text/diagram format */
    @Column(name = "sequence_diagram", columnDefinition = "TEXT")
    private String sequenceDiagram;

    /** JSON list of trade-off decisions */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "trade_offs", columnDefinition = "jsonb")
    private String tradeOffs;

    /** JSON list of ADL rules */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "adl_rules", columnDefinition = "jsonb")
    private String adlRules;

    /** ADL document text */
    @Column(name = "adl_document", columnDefinition = "TEXT")
    private String adlDocument;

    /** The ADL REQUIRES field — names the test tooling needed */
    @Column(name = "requires_tooling", columnDefinition = "TEXT")
    private String requiresTooling;

    /** The ADL PROMPT field — LLM instruction to generate test code */
    @Column(name = "codegen_prompt", columnDefinition = "TEXT")
    private String codegenPrompt;

    /** The complete ADL pseudo-code block, preserved verbatim */
    @Column(name = "adl_source", columnDefinition = "TEXT")
    private String adlSource;

    /** JSON list of identified weaknesses */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "weaknesses", columnDefinition = "jsonb")
    private String weaknesses;

    /** Plain-text summary of weakness analysis */
    @Column(name = "weakness_summary", columnDefinition = "TEXT")
    private String weaknessSummary;

    /** JSON list of FMEA risk entries */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "fmea_risks", columnDefinition = "jsonb")
    private String fmeaRisks;

    /** JSON array of diagram objects produced by the intelligent selector */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "diagrams_json", columnDefinition = "jsonb")
    private String diagramsJson;

    /** True when a user architecture override constrained style selection */
    @Column(name = "override_applied")
    @Builder.Default
    private boolean overrideApplied = false;

    /** Warning text when an override conflicted with inferred characteristics */
    @Column(name = "override_warning", columnDefinition = "TEXT")
    private String overrideWarning;

    /** Timestamp when this output was created */
    @CreationTimestamp
    private Instant createdAt;
}
