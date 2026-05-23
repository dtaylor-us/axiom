package com.aiarchitect.api.service;

import com.aiarchitect.api.domain.model.FmeaRisk;
import com.aiarchitect.api.domain.model.GovernanceReport;
import com.aiarchitect.api.domain.repository.FmeaRiskRepository;
import com.aiarchitect.api.domain.repository.GovernanceReportRepository;
import com.aiarchitect.api.dto.FmeaRiskDto;
import com.aiarchitect.api.dto.GovernanceReportDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class GovernanceService {

    private final FmeaRiskRepository fmeaRiskRepository;
    private final GovernanceReportRepository governanceReportRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public void saveFmeaRisks(UUID conversationId, List<Map<String, Object>> risks) {
        for (Map<String, Object> risk : risks) {
            FmeaRisk entity = FmeaRisk.builder()
                    .conversationId(conversationId)
                    .riskId(getString(risk, "id"))
                    .failureMode(getString(risk, "failure_mode"))
                    .component(getString(risk, "component"))
                    .cause(getString(risk, "cause"))
                    .effect(getString(risk, "effect"))
                    .severity(getInt(risk, "severity"))
                    .occurrence(getInt(risk, "occurrence"))
                    .detection(getInt(risk, "detection"))
                    .rpn(getInt(risk, "rpn"))
                    .currentControls(getString(risk, "current_controls"))
                    .recommendedAction(getString(risk, "recommended_action"))
                    .linkedWeakness(getString(risk, "linked_weakness"))
                    .linkedCharacteristic(getString(risk, "linked_characteristic"))
                    .build();
            fmeaRiskRepository.save(entity);
        }
        log.info("Saved {} FMEA risks for conversation={}", risks.size(), conversationId);
    }

    @Transactional
    public void saveGovernanceReport(UUID conversationId, Map<String, Object> structuredOutput) {
        Map<String, Object> breakdown = getMap(structuredOutput, "governance_score_breakdown");
        Integer score = getIntOrNull(structuredOutput, "governance_score");
        String confidence = getString(structuredOutput, "governance_score_confidence");
        boolean completedFully = Boolean.TRUE.equals(structuredOutput.get("review_completed_fully"));

        String reviewFindingsJson = null;
        String improvementRecsJson = null;
        String failedNodesJson = null;
        String scoreEvidenceJson = null;
        try {
            Object findings = structuredOutput.get("review_findings");
            if (findings != null) {
                reviewFindingsJson = objectMapper.writeValueAsString(findings);
            }
            Object recs = structuredOutput.get("improvement_recommendations");
            if (recs != null) {
                improvementRecsJson = objectMapper.writeValueAsString(recs);
            }
            Object failedNodes = structuredOutput.get("failed_review_nodes");
            if (failedNodes != null) {
                failedNodesJson = objectMapper.writeValueAsString(failedNodes);
            }
            Object scoreEvidence = structuredOutput.get("score_evidence");
            if (scoreEvidence == null) {
                scoreEvidence = breakdown.get("score_evidence");
            }
            if (scoreEvidence != null) {
                scoreEvidenceJson = objectMapper.writeValueAsString(scoreEvidence);
            }
        } catch (JsonProcessingException e) {
            log.warn("Failed to serialize review data for conversation={}", conversationId, e);
        }

        int characteristicAlignment = getInt(breakdown, "characteristic_alignment");
        int adlEnforceability = getInt(breakdown, "adl_enforceability");
        int riskAwareness = getInt(breakdown, "risk_awareness");
        GovernanceReport report = GovernanceReport.builder()
                .conversationId(conversationId)
                .iteration(getInt(structuredOutput, "iteration"))
                .governanceScore(score)
                .governanceScoreConfidence(confidence != null ? confidence : "unavailable")
                .reviewCompletedFully(completedFully)
                .failedReviewNodes(failedNodesJson)
                .requirementCoverage(getInt(breakdown, "requirement_coverage"))
                .characteristicAlignment(characteristicAlignment)
                .tradeOffQuality(getInt(breakdown, "trade_off_quality"))
                .adlEnforceability(adlEnforceability)
                .riskAwareness(riskAwareness)
                .consistencyBonus(getInt(breakdown, "consistency_bonus"))
                .scoreEvidence(scoreEvidenceJson)
                .architecturalSoundness(characteristicAlignment)
                .riskMitigation(riskAwareness)
                .governanceCompleteness(adlEnforceability)
                .justification(getString(breakdown, "justification"))
                .shouldReiterate(Boolean.TRUE.equals(structuredOutput.get("should_reiterate")))
                .reviewFindings(reviewFindingsJson)
                .improvementRecommendations(improvementRecsJson)
                .build();

        governanceReportRepository.save(report);
        log.info(
                "Saved governance report for conversation={} score={} confidence={}",
                conversationId,
                score,
                report.getGovernanceScoreConfidence()
        );
    }

    public List<FmeaRiskDto> getFmeaRisks(UUID conversationId) {
        return fmeaRiskRepository.findByConversationIdOrderByRpnDesc(conversationId)
                .stream()
                .map(this::toFmeaDto)
                .toList();
    }

    public Optional<GovernanceReportDto> getGovernanceReport(UUID conversationId) {
        return governanceReportRepository
                .findTopByConversationIdOrderByCreatedAtDesc(conversationId)
                .map(this::toGovernanceDto);
    }

    private FmeaRiskDto toFmeaDto(FmeaRisk r) {
        return FmeaRiskDto.builder()
                .id(r.getId())
                .riskId(r.getRiskId())
                .failureMode(r.getFailureMode())
                .component(r.getComponent())
                .cause(r.getCause())
                .effect(r.getEffect())
                .severity(r.getSeverity())
                .occurrence(r.getOccurrence())
                .detection(r.getDetection())
                .rpn(r.getRpn())
                .currentControls(r.getCurrentControls())
                .recommendedAction(r.getRecommendedAction())
                .linkedWeakness(r.getLinkedWeakness())
                .linkedCharacteristic(r.getLinkedCharacteristic())
                .createdAt(r.getCreatedAt())
                .build();
    }

    private GovernanceReportDto toGovernanceDto(GovernanceReport r) {
        Object findings = null;
        List<Object> recs = null;
        List<String> failedNodes = List.of();
        Map<String, String> scoreEvidence = Map.of();
        try {
            if (r.getReviewFindings() != null) {
                findings = objectMapper.readValue(r.getReviewFindings(), Object.class);
            }
            if (r.getImprovementRecommendations() != null) {
                recs = objectMapper.readValue(
                        r.getImprovementRecommendations(),
                        new TypeReference<>() {});
            }
            if (r.getFailedReviewNodes() != null) {
                failedNodes = objectMapper.readValue(
                        r.getFailedReviewNodes(),
                        new TypeReference<>() {});
            }
            if (r.getScoreEvidence() != null) {
                scoreEvidence = objectMapper.readValue(
                        r.getScoreEvidence(),
                        new TypeReference<>() {});
            }
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse governance JSON for report={}", r.getId(), e);
        }

        return GovernanceReportDto.builder()
                .id(r.getId())
                .conversationId(r.getConversationId())
                .iteration(r.getIteration())
                .governanceScore(r.getGovernanceScore())
                .governanceScoreConfidence(r.getGovernanceScoreConfidence())
                .reviewCompletedFully(r.isReviewCompletedFully())
                .failedReviewNodes(failedNodes)
                .requirementCoverage(r.getRequirementCoverage())
                .characteristicAlignment(r.getCharacteristicAlignment())
                .tradeOffQuality(r.getTradeOffQuality())
                .adlEnforceability(r.getAdlEnforceability())
                .riskAwareness(r.getRiskAwareness())
                .consistencyBonus(r.getConsistencyBonus())
                .scoreEvidence(scoreEvidence)
                .architecturalSoundness(r.getArchitecturalSoundness())
                .riskMitigation(r.getRiskMitigation())
                .governanceCompleteness(r.getGovernanceCompleteness())
                .justification(r.getJustification())
                .shouldReiterate(r.isShouldReiterate())
                .reviewFindings(findings)
                .improvementRecommendations(recs)
                .createdAt(r.getCreatedAt())
                .build();
    }

    private static String getString(Map<String, Object> map, String key) {
        if (map == null) return null;
        Object v = map.get(key);
        return v != null ? v.toString() : null;
    }

    private static int getInt(Map<String, Object> map, String key) {
        if (map == null) return 0;
        Object v = map.get(key);
        if (v instanceof Number n) return n.intValue();
        return 0;
    }

    private static Integer getIntOrNull(Map<String, Object> map, String key) {
        if (map == null) return null;
        Object v = map.get(key);
        if (v instanceof Number n) return n.intValue();
        return null;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> getMap(Map<String, Object> map, String key) {
        if (map == null) return Map.of();
        Object v = map.get(key);
        if (v instanceof Map<?, ?> m) return (Map<String, Object>) m;
        return Map.of();
    }
}
