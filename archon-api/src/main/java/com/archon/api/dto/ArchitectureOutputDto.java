package com.archon.api.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Data Transfer Object for Architecture Output.
 * 
 * Contains the complete output of an architecture generation request, including
 * architectural style, domain information, system components, their interactions,
 * and visual diagrams.
 * 
 * @author Archon
 */
@Data @Builder
public class ArchitectureOutputDto {

    private UUID id;
    private UUID conversationId;
    private String style;
    private String domain;
    private String systemType;
    private int componentCount;
    private List<Object> components;
    private List<Object> interactions;
    private List<Object> characteristics;
    private List<Object> conflicts;
    private String componentDiagram;
    private String sequenceDiagram;
    private List<Object> tradeOffs;
    private List<Object> adlRules;
    private String adlDocument;
    private String requiresTooling;
    private String codegenPrompt;
    private String adlSource;
    private List<Object> weaknesses;
    private String weaknessSummary;
    private List<Object> fmeaRisks;
    private List<Object> diagrams;
    private boolean overrideApplied;
    private String overrideWarning;
    private Instant createdAt;
}
