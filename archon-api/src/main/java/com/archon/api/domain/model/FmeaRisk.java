package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "fmea_risks")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class FmeaRisk {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    @Column(name = "risk_id", nullable = false)
    private String riskId;

    @Column(name = "failure_mode", nullable = false)
    private String failureMode;

    @Column(nullable = false)
    private String component;

    private String cause;
    private String effect;

    @Column(nullable = false)
    private int severity;

    @Column(nullable = false)
    private int occurrence;

    @Column(nullable = false)
    private int detection;

    @Column(nullable = false)
    private int rpn;

    @Column(name = "current_controls")
    private String currentControls;

    @Column(name = "recommended_action")
    private String recommendedAction;

    @Column(name = "linked_weakness")
    private String linkedWeakness;

    @Column(name = "linked_characteristic")
    private String linkedCharacteristic;

    @CreationTimestamp
    private Instant createdAt;
}
