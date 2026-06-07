package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
public class TacticDto {

    private UUID id;
    private String tacticId;
    private String tacticName;
    private String characteristicName;
    private String category;
    private String description;
    private String concreteApplication;
    private List<String> implementationExamples;
    private boolean alreadyAddressed;
    private String addressEvidence;
    private String effort;
    private String priority;
    private Instant createdAt;
}
