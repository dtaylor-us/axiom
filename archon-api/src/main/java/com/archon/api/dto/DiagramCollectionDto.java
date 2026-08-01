package com.archon.api.dto;

import java.util.List;

/**
 * Wraps the full set of diagrams returned for a session.
 *
 * @param diagrams     ordered list of generated diagrams
 * @param diagramCount total number of diagrams
 * @param diagramTypes list of diagram type identifiers present
 */
public record DiagramCollectionDto(
        List<DiagramDto> diagrams,
        int diagramCount,
        List<String> diagramTypes
) {}
