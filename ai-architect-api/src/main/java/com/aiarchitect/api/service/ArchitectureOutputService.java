package com.aiarchitect.api.service;

import com.aiarchitect.api.domain.model.ArchitectureOutput;
import com.aiarchitect.api.domain.repository.ArchitectureOutputRepository;
import com.aiarchitect.api.dto.ArchitectureOutputDto;
import com.aiarchitect.api.dto.DiagramCollectionDto;
import com.aiarchitect.api.dto.DiagramDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class ArchitectureOutputService {

    private final ArchitectureOutputRepository repository;
    private final ObjectMapper objectMapper;

    /**
     * Persist a new architecture output extracted from the agent's structured output.
     *
     * @param conversationId   the conversation UUID
     * @param structuredOutput the full structured_output map from the COMPLETE event
     */
    @Transactional
    public void saveFromStructuredOutput(UUID conversationId,
                                         Map<String, Object> structuredOutput) {
        if (structuredOutput == null) {
            return;
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> design = (Map<String, Object>)
                structuredOutput.getOrDefault("architecture_design", Map.of());

        @SuppressWarnings("unchecked")
        List<Object> components = (List<Object>)
                design.getOrDefault("components", List.of());

        @SuppressWarnings("unchecked")
        List<Object> interactions = (List<Object>)
                design.getOrDefault("interactions", List.of());

        @SuppressWarnings("unchecked")
        List<Object> characteristics = (List<Object>)
                structuredOutput.getOrDefault("characteristics", List.of());

        @SuppressWarnings("unchecked")
        List<Object> conflicts = (List<Object>)
                structuredOutput.getOrDefault("characteristic_conflicts", List.of());

        String componentDiagram = (String)
                structuredOutput.getOrDefault("mermaid_component_diagram", "");
        String sequenceDiagram = (String)
                structuredOutput.getOrDefault("mermaid_sequence_diagram", "");

        @SuppressWarnings("unchecked")
        List<Object> tradeOffs = (List<Object>)
                structuredOutput.getOrDefault("trade_offs", List.of());

        @SuppressWarnings("unchecked")
        List<Object> adlRules = (List<Object>)
                structuredOutput.getOrDefault("adl_rules", List.of());

        String adlDocument = (String)
                structuredOutput.getOrDefault("adl_document", "");

        // Extract Richards-spec ADL fields from the first adl_block if present.
        // These are denormalized onto the output row for query convenience.
        String requiresTooling = extractFirstAdlMetadataField(adlRules, "requires");
        String codegenPrompt = extractFirstAdlMetadataField(adlRules, "prompt");
        String adlSourceField = extractFirstAdlField(adlRules, "adl_source");

        @SuppressWarnings("unchecked")
        List<Object> weaknesses = (List<Object>)
                structuredOutput.getOrDefault("weaknesses", List.of());

        String weaknessSummary = (String)
                structuredOutput.getOrDefault("weakness_summary", "");

        @SuppressWarnings("unchecked")
        List<Object> fmeaRisks = (List<Object>)
                structuredOutput.getOrDefault("fmea_risks", List.of());

        @SuppressWarnings("unchecked")
        List<Object> diagrams = (List<Object>)
                structuredOutput.getOrDefault("diagrams", List.of());

        boolean overrideApplied = false;
        String overrideWarning = "";
        try {
            Object oa = design.getOrDefault("override_applied", false);
            if (oa instanceof Boolean b) {
                overrideApplied = b;
            } else if (oa instanceof String s) {
                overrideApplied = Boolean.parseBoolean(s);
            }
            Object ow = design.getOrDefault("override_warning", "");
            if (ow != null) {
                overrideWarning = ow.toString();
            }
        } catch (Exception e) {
            log.warn("Failed to extract override metadata for conversation={}",
                    conversationId, e);
        }

        ArchitectureOutput output = ArchitectureOutput.builder()
                .conversationId(conversationId)
                .style((String) design.getOrDefault("style", ""))
                .domain((String) design.getOrDefault("domain", ""))
                .systemType((String) design.getOrDefault("system_type", ""))
                .componentCount(components.size())
                .components(toJson(components))
                .interactions(toJson(interactions))
                .characteristics(toJson(characteristics))
                .conflicts(toJson(conflicts))
                .componentDiagram(componentDiagram)
                .sequenceDiagram(sequenceDiagram)
                .tradeOffs(toJson(tradeOffs))
                .adlRules(toJson(adlRules))
                .adlDocument(adlDocument)
                .requiresTooling(requiresTooling)
                .codegenPrompt(codegenPrompt)
                .adlSource(adlSourceField)
                .weaknesses(toJson(weaknesses))
                .weaknessSummary(weaknessSummary)
                .fmeaRisks(toJson(fmeaRisks))
                .diagramsJson(toJson(diagrams))
                .overrideApplied(overrideApplied)
                .overrideWarning(overrideWarning)
                .build();

        repository.save(output);
        log.info("Saved architecture output for conversation={}, components={}",
                 conversationId, components.size());
    }

    /**
     * Retrieve the latest architecture output for a conversation.
     */
    @Transactional(readOnly = true)
    public Optional<ArchitectureOutputDto> getLatest(UUID conversationId) {
        return repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId)
                .map(this::toDto);
    }

    private ArchitectureOutputDto toDto(ArchitectureOutput entity) {
        return ArchitectureOutputDto.builder()
                .id(entity.getId())
                .conversationId(entity.getConversationId())
                .style(entity.getStyle())
                .domain(entity.getDomain())
                .systemType(entity.getSystemType())
                .componentCount(entity.getComponentCount())
                .components(fromJson(entity.getComponents()))
                .interactions(fromJson(entity.getInteractions()))
                .characteristics(fromJson(entity.getCharacteristics()))
                .conflicts(fromJson(entity.getConflicts()))
                .componentDiagram(entity.getComponentDiagram())
                .sequenceDiagram(entity.getSequenceDiagram())
                .tradeOffs(fromJson(entity.getTradeOffs()))
                .adlRules(fromJson(entity.getAdlRules()))
                .adlDocument(entity.getAdlDocument())
                .requiresTooling(entity.getRequiresTooling())
                .codegenPrompt(entity.getCodegenPrompt())
                .adlSource(entity.getAdlSource())
                .weaknesses(fromJson(entity.getWeaknesses()))
                .weaknessSummary(entity.getWeaknessSummary())
                .fmeaRisks(fromJson(entity.getFmeaRisks()))
                .diagrams(fromJson(entity.getDiagramsJson()))
                .overrideApplied(entity.isOverrideApplied())
                .overrideWarning(entity.getOverrideWarning())
                .createdAt(entity.getCreatedAt())
                .build();
    }

    /**
     * Return the full diagram collection for a conversation.
     * Parses the diagrams_json column into a structured DiagramCollectionDto.
     */
    @Transactional(readOnly = true)
    public Optional<DiagramCollectionDto> getDiagramCollection(UUID conversationId) {
        return repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId)
                .map(entity -> {
                    List<DiagramDto> diagrams = parseDiagrams(entity.getDiagramsJson());
                    List<String> types = diagrams.stream()
                            .map(DiagramDto::type)
                            .toList();
                    return new DiagramCollectionDto(diagrams, diagrams.size(), types);
                });
    }

    /**
     * Return a single diagram by type for a conversation.
     * Returns 404 (empty Optional) when the type was not generated.
     */
    @Transactional(readOnly = true)
    public Optional<DiagramDto> getDiagramByType(UUID conversationId, String type) {
        return repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId)
                .flatMap(entity -> parseDiagrams(entity.getDiagramsJson()).stream()
                        .filter(d -> d.type().equals(type))
                        .findFirst());
    }

    /**
     * Parse the diagrams_json JSONB column into a list of DiagramDto records.
     */
    private List<DiagramDto> parseDiagrams(String diagramsJson) {
        if (diagramsJson == null || diagramsJson.isBlank()) {
            return List.of();
        }
        try {
            List<Map<String, Object>> raw = objectMapper.readValue(
                    diagramsJson, new TypeReference<>() {});
            return raw.stream().map(m -> new DiagramDto(
                    (String) m.getOrDefault("diagram_id", ""),
                    (String) m.getOrDefault("type", ""),
                    (String) m.getOrDefault("title", ""),
                    (String) m.getOrDefault("description", ""),
                    (String) m.getOrDefault("mermaid_source", ""),
                    (String) m.getOrDefault("characteristic_addressed", "")
            )).toList();
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse diagrams_json", e);
            return List.of();
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            log.warn("Failed to serialize to JSON", e);
            return "[]";
        }
    }

    private List<Object> fromJson(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to deserialize JSON", e);
            return List.of();
        }
    }

    /**
     * Extract a field from the metadata object of the first ADL block.
     * The payload now contains AdlBlock structures with nested metadata.
     *
     * @param adlBlocks list of ADL block maps from the pipeline payload
     * @param fieldName the metadata field to extract (e.g. "requires", "prompt")
     * @return the field value from the first block, or empty string if absent
     */
    @SuppressWarnings("unchecked")
    private String extractFirstAdlMetadataField(List<Object> adlBlocks, String fieldName) {
        if (adlBlocks == null || adlBlocks.isEmpty()) {
            return "";
        }
        Object first = adlBlocks.get(0);
        if (first instanceof Map<?, ?> block) {
            Object metadata = block.get("metadata");
            if (metadata instanceof Map<?, ?> meta) {
                Object value = meta.get(fieldName);
                return value != null ? value.toString() : "";
            }
        }
        return "";
    }

    /**
     * Extract a top-level field from the first ADL block.
     *
     * @param adlBlocks list of ADL block maps from the pipeline payload
     * @param fieldName the field to extract (e.g. "adl_source")
     * @return the field value from the first block, or empty string if absent
     */
    private String extractFirstAdlField(List<Object> adlBlocks, String fieldName) {
        if (adlBlocks == null || adlBlocks.isEmpty()) {
            return "";
        }
        Object first = adlBlocks.get(0);
        if (first instanceof Map<?, ?> block) {
            Object value = block.get(fieldName);
            return value != null ? value.toString() : "";
        }
        return "";
    }
}
