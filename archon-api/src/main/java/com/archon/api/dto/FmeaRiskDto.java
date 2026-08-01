package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
public class FmeaRiskDto {
    private UUID id;
    private String riskId;
    private String failureMode;
    private String component;
    private String cause;
    private String effect;
    private int severity;
    private int occurrence;
    private int detection;
    private int rpn;
    private String currentControls;
    private String recommendedAction;
    private String linkedWeakness;
    private String linkedCharacteristic;
    private Instant createdAt;
}
