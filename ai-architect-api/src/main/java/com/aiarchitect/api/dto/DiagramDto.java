package com.aiarchitect.api.dto;

/**
 * Data Transfer Object for a single generated Mermaid diagram.
 *
 * @param diagramId               unique identifier (e.g. D-001)
 * @param type                    diagram type (e.g. c4_container, sequence_primary)
 * @param title                   human-readable title
 * @param description             one-sentence description of what the diagram shows
 * @param mermaidSource           complete valid Mermaid source — no fences
 * @param characteristicAddressed the architecture characteristic this diagram makes visible
 */
public record DiagramDto(
        String diagramId,
        String type,
        String title,
        String description,
        String mermaidSource,
        String characteristicAddressed
) {}
