package com.archon.api.service;

import com.archon.api.domain.model.BuyVsBuildDecision;
import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.repository.BuyVsBuildRepository;
import com.archon.api.dto.BuyVsBuildDecisionDto;
import com.archon.api.dto.BuyVsBuildSummaryDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Persistence and query service for stage 6b buy-vs-build decisions.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class BuyVsBuildService {

    private static final TypeReference<List<String>> STRING_LIST_TYPE =
            new TypeReference<>() {};

    private final BuyVsBuildRepository repository;
    private final ObjectMapper objectMapper;

    /**
     * Persist one DB row per buy-vs-build decision.
     *
     * <p>Best-effort: callers typically wrap this in a try/catch because
     * pipeline persistence must never break SSE completion.
     */
    @Transactional
    public void saveDecisions(Conversation conv,
                              List<Map<String, Object>> decisions) {
        if (decisions == null || decisions.isEmpty()) {
            return;
        }
        UUID conversationId = conv.getId();

        for (Map<String, Object> raw : decisions) {
            String component = getString(raw, "component_name");
            try {
                String alternativesJson = objectMapper.writeValueAsString(
                        raw.getOrDefault("alternatives_considered", List.of()));

                BuyVsBuildDecision entity = BuyVsBuildDecision.builder()
                        .conversationId(conversationId)
                        .componentName(component)
                        .recommendation(getString(raw, "recommendation"))
                        .rationale(getString(raw, "rationale"))
                        .alternativesConsidered(alternativesJson)
                        .recommendedSolution(getString(raw, "recommended_solution"))
                        .estimatedBuildCost(getString(raw, "estimated_build_cost"))
                        .vendorLockInRisk(getString(raw, "vendor_lock_in_risk"))
                        .integrationEffort(getString(raw, "integration_effort"))
                        .conflictsWithUserPreference(getBoolean(raw, "conflicts_with_user_preference"))
                        .conflictExplanation(getString(raw, "conflict_explanation"))
                        .isCoreDifferentiator(getBoolean(raw, "is_core_differentiator"))
                        .build();

                repository.save(entity);
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialise alternatives_considered component={} conversation={}",
                        component, conversationId, e);
            } catch (Exception e) {
                log.warn("Failed to persist buy-vs-build decision component={} conversation={}",
                        component, conversationId, e);
            }
        }

        log.info("Saved {} buy-vs-build decisions for conversation={}",
                decisions.size(), conversationId);
    }

    @Transactional(readOnly = true)
    public BuyVsBuildSummaryDto getSummary(UUID conversationId) {
        List<BuyVsBuildDecision> all = repository.findByConversationId(conversationId);
        if (all.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No buy-vs-build decisions found");
        }

        int buildCount = (int) all.stream().filter(d -> "build".equals(d.getRecommendation())).count();
        int buyCount = (int) all.stream().filter(d -> "buy".equals(d.getRecommendation())).count();
        int adoptCount = (int) all.stream().filter(d -> "adopt".equals(d.getRecommendation())).count();
        int conflictCount = (int) all.stream().filter(BuyVsBuildDecision::isConflictsWithUserPreference).count();

        List<BuyVsBuildDecisionDto> dtos = all.stream().map(this::toDto).toList();

        String summaryText = ""; // summary text is stored in messages; callers may overlay it
        return new BuyVsBuildSummaryDto(
                summaryText,
                all.size(),
                buildCount,
                buyCount,
                adoptCount,
                conflictCount,
                dtos
        );
    }

    @Transactional(readOnly = true)
    public List<BuyVsBuildDecisionDto> getDecisions(UUID conversationId) {
        return repository.findByConversationId(conversationId).stream().map(this::toDto).toList();
    }

    @Transactional(readOnly = true)
    public List<BuyVsBuildDecisionDto> getByRecommendation(UUID conversationId, String recommendation) {
        return repository.findByConversationIdAndRecommendation(conversationId, recommendation)
                .stream().map(this::toDto).toList();
    }

    private BuyVsBuildDecisionDto toDto(BuyVsBuildDecision e) {
        List<String> alternatives;
        try {
            alternatives = objectMapper.readValue(
                    e.getAlternativesConsidered() == null ? "[]" : e.getAlternativesConsidered(),
                    STRING_LIST_TYPE);
        } catch (Exception ex) {
            log.warn("Failed to deserialise alternatives_considered id={}", e.getId(), ex);
            alternatives = Collections.emptyList();
        }

        return BuyVsBuildDecisionDto.builder()
                .id(e.getId())
                .conversationId(e.getConversationId())
                .componentName(e.getComponentName())
                .recommendation(e.getRecommendation())
                .rationale(e.getRationale())
                .alternativesConsidered(alternatives)
                .recommendedSolution(e.getRecommendedSolution())
                .estimatedBuildCost(e.getEstimatedBuildCost())
                .vendorLockInRisk(e.getVendorLockInRisk())
                .integrationEffort(e.getIntegrationEffort())
                .conflictsWithUserPreference(e.isConflictsWithUserPreference())
                .conflictExplanation(e.getConflictExplanation() != null ? e.getConflictExplanation() : "")
                .isCoreeDifferentiator(e.isCoreDifferentiator())
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

