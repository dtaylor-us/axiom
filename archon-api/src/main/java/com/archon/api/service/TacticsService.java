package com.archon.api.service;

import com.archon.api.domain.model.ArchitectureTactic;
import com.archon.api.domain.repository.TacticRepository;
import com.archon.api.dto.TacticDto;
import com.archon.api.dto.TacticsSummaryDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Persistence and query service for architecture tactic recommendations.
 *
 * <p>Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TacticsService {

    private static final TypeReference<List<String>> STRING_LIST_TYPE =
            new TypeReference<>() {};

    private final TacticRepository tacticRepository;
    private final ObjectMapper objectMapper;

    // -----------------------------------------------------------------------
    // Write path
    // -----------------------------------------------------------------------

    /**
     * Persist a list of raw tactic maps extracted from the Python agent's
     * structured output.
     *
     * <p>Called from {@link ChatService} when structured output contains the
     * {@code tactics} key.  Each map is a serialised
     * {@code TacticRecommendation} Pydantic model.
     *
     * @param conversationId owning conversation
     * @param tactics        raw tactic maps from {@code structured_output.tactics}
     */
    @Transactional
    public void saveTactics(UUID conversationId,
                            List<Map<String, Object>> tactics) {
        for (Map<String, Object> raw : tactics) {
            String tacticId = getString(raw, "tactic_id");
            try {
                String examplesJson = objectMapper.writeValueAsString(
                        raw.getOrDefault("implementation_examples", List.of()));

                ArchitectureTactic entity = ArchitectureTactic.builder()
                        .conversationId(conversationId)
                        .tacticId(tacticId)
                        .tacticName(getString(raw, "tactic_name"))
                        .characteristicName(getString(raw, "characteristic_name"))
                        .category(getString(raw, "category"))
                        .description(getString(raw, "description"))
                        .concreteApplication(getString(raw, "concrete_application"))
                        .implementationExamples(examplesJson)
                        .alreadyAddressed(getBoolean(raw, "already_addressed"))
                        .addressEvidence(getString(raw, "address_evidence"))
                        .effort(getString(raw, "effort"))
                        .priority(getString(raw, "priority"))
                        .build();

                tacticRepository.save(entity);
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialise implementation_examples for tactic={} conversation={}",
                        tacticId, conversationId, e);
            } catch (Exception e) {
                log.warn("Failed to persist tactic={} conversation={}", tacticId, conversationId, e);
            }
        }
        log.info("Saved {} tactics for conversation={}", tactics.size(), conversationId);
    }

    // -----------------------------------------------------------------------
    // Read path
    // -----------------------------------------------------------------------

    /**
     * Return all tactics for a conversation, ordered by priority then name.
     *
     * @param conversationId owning conversation
     * @param characteristic optional filter — only tactics for this quality attribute
     * @param priority       optional filter — only tactics with this priority value
     * @param newOnly        when {@code true} exclude already-addressed tactics
     */
    public List<TacticDto> getTactics(UUID conversationId,
                                      String characteristic,
                                      String priority,
                                      boolean newOnly) {
        List<ArchitectureTactic> entities;

        if (characteristic != null && !characteristic.isBlank()) {
            entities = tacticRepository
                    .findByConversationIdAndCharacteristicNameOrderByPriorityAsc(
                            conversationId, characteristic);
        } else if (priority != null && !priority.isBlank()) {
            entities = tacticRepository
                    .findByConversationIdAndPriorityOrderByTacticNameAsc(
                            conversationId, priority);
        } else if (newOnly) {
            entities = tacticRepository
                    .findByConversationIdAndAlreadyAddressedFalseOrderByPriorityAscTacticNameAsc(
                            conversationId);
        } else {
            entities = tacticRepository
                    .findByConversationIdOrderByPriorityAscTacticNameAsc(conversationId);
        }

        return entities.stream().map(this::toDto).toList();
    }

    /**
     * Return aggregate summary counts and the natural-language summary text.
     */
    public TacticsSummaryDto getTacticsSummary(UUID conversationId) {
        List<ArchitectureTactic> all = tacticRepository
                .findByConversationIdOrderByPriorityAscTacticNameAsc(conversationId);

        long criticalCount = all.stream()
                .filter(t -> "critical".equals(t.getPriority()))
                .count();
        long alreadyAddressedCount = all.stream()
                .filter(ArchitectureTactic::isAlreadyAddressed)
                .count();
        long newCount = all.size() - alreadyAddressedCount;

        Map<String, Long> perCharacteristic = all.stream()
                .collect(Collectors.groupingBy(
                        ArchitectureTactic::getCharacteristicName,
                        Collectors.counting()));

        List<String> topCritical = all.stream()
                .filter(t -> "critical".equals(t.getPriority()) && !t.isAlreadyAddressed())
                .map(ArchitectureTactic::getTacticName)
                .limit(5)
                .toList();

        return TacticsSummaryDto.builder()
                .totalTactics(all.size())
                .criticalCount((int) criticalCount)
                .alreadyAddressedCount((int) alreadyAddressedCount)
                .newTacticsCount((int) newCount)
                .perCharacteristic(perCharacteristic)
                .topCriticalTactics(topCritical)
                .summary("")   // tactics_summary is stored in the message; callers may overlay it
                .build();
    }

    // -----------------------------------------------------------------------
    // Mapping helpers
    // -----------------------------------------------------------------------

    private TacticDto toDto(ArchitectureTactic e) {
        List<String> examples;
        try {
            examples = objectMapper.readValue(e.getImplementationExamples(), STRING_LIST_TYPE);
        } catch (Exception ex) {
            log.warn("Failed to deserialise implementation_examples for tactic_id={}", e.getTacticId(), ex);
            examples = Collections.emptyList();
        }

        return TacticDto.builder()
                .id(e.getId())
                .tacticId(e.getTacticId())
                .tacticName(e.getTacticName())
                .characteristicName(e.getCharacteristicName())
                .category(e.getCategory())
                .description(e.getDescription())
                .concreteApplication(e.getConcreteApplication())
                .implementationExamples(examples)
                .alreadyAddressed(e.isAlreadyAddressed())
                .addressEvidence(e.getAddressEvidence())
                .effort(e.getEffort())
                .priority(e.getPriority())
                .createdAt(e.getCreatedAt())
                .build();
    }

    private static String getString(Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val != null ? val.toString() : "";
    }

    private static boolean getBoolean(Map<String, Object> map, String key) {
        Object val = map.get(key);
        if (val instanceof Boolean b) return b;
        if (val instanceof String s) return Boolean.parseBoolean(s);
        return false;
    }
}
