package com.archon.api.service;

import com.archon.api.domain.model.FmeaRisk;
import com.archon.api.domain.model.GovernanceReport;
import com.archon.api.domain.repository.FmeaRiskRepository;
import com.archon.api.domain.repository.GovernanceReportRepository;
import com.archon.api.dto.FmeaRiskDto;
import com.archon.api.dto.GovernanceReportDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class GovernanceServiceTest {

    @Mock private FmeaRiskRepository fmeaRiskRepository;
    @Mock private GovernanceReportRepository governanceReportRepository;
    @Spy  private ObjectMapper objectMapper = new ObjectMapper();

    private GovernanceService governanceService;

    @BeforeEach
    void setUp() {
        governanceService = new GovernanceService(
                fmeaRiskRepository, governanceReportRepository, objectMapper);
    }

    // ── saveFmeaRisks ───────────────────────────────────────────

    @Test
    void saveFmeaRisks_persistsAllRisks() {
        UUID convId = UUID.randomUUID();
        List<Map<String, Object>> risks = List.of(
                createRiskMap("FMEA-001", "Gateway timeout", 8, 5, 3, 120),
                createRiskMap("FMEA-002", "Queue overflow", 7, 4, 2, 56)
        );

        governanceService.saveFmeaRisks(convId, risks);

        verify(fmeaRiskRepository, times(2)).save(any(FmeaRisk.class));
    }

    @Test
    void saveFmeaRisks_mapsFieldsCorrectly() {
        UUID convId = UUID.randomUUID();
        List<Map<String, Object>> risks = List.of(
                createRiskMap("FMEA-001", "Gateway timeout", 8, 5, 3, 120)
        );

        when(fmeaRiskRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        governanceService.saveFmeaRisks(convId, risks);

        ArgumentCaptor<FmeaRisk> captor = ArgumentCaptor.forClass(FmeaRisk.class);
        verify(fmeaRiskRepository).save(captor.capture());

        FmeaRisk saved = captor.getValue();
        assertEquals(convId, saved.getConversationId());
        assertEquals("FMEA-001", saved.getRiskId());
        assertEquals("Gateway timeout", saved.getFailureMode());
        assertEquals(8, saved.getSeverity());
        assertEquals(5, saved.getOccurrence());
        assertEquals(3, saved.getDetection());
        assertEquals(120, saved.getRpn());
    }

    // ── saveGovernanceReport ────────────────────────────────────

    @Test
    void saveGovernanceReport_persistsReport() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> output = createStructuredOutput(75, true);

        governanceService.saveGovernanceReport(convId, output);

        verify(governanceReportRepository).save(any(GovernanceReport.class));
    }

    @Test
    void saveGovernanceReport_mapsScoreBreakdown() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> output = createStructuredOutput(75, false);

        when(governanceReportRepository.save(any()))
                .thenAnswer(inv -> inv.getArgument(0));

        governanceService.saveGovernanceReport(convId, output);

        ArgumentCaptor<GovernanceReport> captor =
                ArgumentCaptor.forClass(GovernanceReport.class);
        verify(governanceReportRepository).save(captor.capture());

        GovernanceReport saved = captor.getValue();
        assertEquals(convId, saved.getConversationId());
        assertEquals(75, saved.getGovernanceScore());
        assertEquals(20, saved.getRequirementCoverage());
        assertEquals(18, saved.getArchitecturalSoundness());
        assertEquals(15, saved.getRiskMitigation());
        assertEquals(22, saved.getGovernanceCompleteness());
        assertFalse(saved.isShouldReiterate());
    }

    @Test
    void saveGovernanceReport_persistsReportWithNullScoreWhenUnavailable() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> output = new HashMap<>();
        output.put("iteration", 0);
        output.put("governance_score_confidence", "unavailable");
        output.put("review_completed_fully", false);
        output.put("failed_review_nodes", List.of("score_governance"));

        governanceService.saveGovernanceReport(convId, output);

        ArgumentCaptor<GovernanceReport> captor =
                ArgumentCaptor.forClass(GovernanceReport.class);
        verify(governanceReportRepository).save(captor.capture());

        assertNull(captor.getValue().getGovernanceScore());
        assertEquals("unavailable", captor.getValue().getGovernanceScoreConfidence());
    }

    @Test
    void saveGovernanceReport_serialisesReviewFindingsAsJson() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> output = createStructuredOutput(80, false);
        output.put("review_findings", Map.of(
                "assumption_challenges", List.of(
                        Map.of("assumption", "test", "risk", "low")
                )
        ));

        when(governanceReportRepository.save(any()))
                .thenAnswer(inv -> inv.getArgument(0));

        governanceService.saveGovernanceReport(convId, output);

        ArgumentCaptor<GovernanceReport> captor =
                ArgumentCaptor.forClass(GovernanceReport.class);
        verify(governanceReportRepository).save(captor.capture());

        String json = captor.getValue().getReviewFindings();
        assertNotNull(json);
        assertTrue(json.contains("assumption_challenges"));
    }

    // ── getFmeaRisks ────────────────────────────────────────────

    @Test
    void getFmeaRisks_returnsMappedDtos() {
        UUID convId = UUID.randomUUID();
        FmeaRisk entity = FmeaRisk.builder()
                .id(UUID.randomUUID())
                .conversationId(convId)
                .riskId("FMEA-001")
                .failureMode("Gateway timeout")
                .component("PaymentGateway")
                .severity(8)
                .occurrence(5)
                .detection(3)
                .rpn(120)
                .createdAt(Instant.now())
                .build();

        when(fmeaRiskRepository.findByConversationIdOrderByRpnDesc(convId))
                .thenReturn(List.of(entity));

        List<FmeaRiskDto> result = governanceService.getFmeaRisks(convId);

        assertEquals(1, result.size());
        assertEquals("FMEA-001", result.get(0).getRiskId());
        assertEquals(120, result.get(0).getRpn());
    }

    @Test
    void getFmeaRisks_returnsEmptyListWhenNone() {
        UUID convId = UUID.randomUUID();
        when(fmeaRiskRepository.findByConversationIdOrderByRpnDesc(convId))
                .thenReturn(List.of());

        List<FmeaRiskDto> result = governanceService.getFmeaRisks(convId);

        assertTrue(result.isEmpty());
    }

    // ── getGovernanceReport ─────────────────────────────────────

    @Test
    void getGovernanceReport_returnsMappedDto() {
        UUID convId = UUID.randomUUID();
        GovernanceReport entity = GovernanceReport.builder()
                .id(UUID.randomUUID())
                .conversationId(convId)
                .iteration(0)
                .governanceScore(75)
                .requirementCoverage(20)
                .architecturalSoundness(18)
                .riskMitigation(15)
                .governanceCompleteness(22)
                .justification("Solid design")
                .shouldReiterate(false)
                .createdAt(Instant.now())
                .build();

        when(governanceReportRepository.findTopByConversationIdOrderByCreatedAtDesc(convId))
                .thenReturn(Optional.of(entity));

        Optional<GovernanceReportDto> result =
                governanceService.getGovernanceReport(convId);

        assertTrue(result.isPresent());
        assertEquals(75, result.get().getGovernanceScore());
        assertEquals(20, result.get().getRequirementCoverage());
    }

    @Test
    void getGovernanceReport_returnsEmptyWhenNotFound() {
        UUID convId = UUID.randomUUID();
        when(governanceReportRepository.findTopByConversationIdOrderByCreatedAtDesc(convId))
                .thenReturn(Optional.empty());

        Optional<GovernanceReportDto> result =
                governanceService.getGovernanceReport(convId);

        assertTrue(result.isEmpty());
    }

    @Test
    void getGovernanceReport_deserialisesJsonbFields() throws Exception {
        UUID convId = UUID.randomUUID();
        String findingsJson = objectMapper.writeValueAsString(
                Map.of("assumption_challenges", List.of(Map.of("a", "b"))));
        String recsJson = objectMapper.writeValueAsString(
                List.of(Map.of("area", "risk", "recommendation", "add retry")));

        GovernanceReport entity = GovernanceReport.builder()
                .id(UUID.randomUUID())
                .conversationId(convId)
                .iteration(0)
                .governanceScore(65)
                .requirementCoverage(15)
                .architecturalSoundness(15)
                .riskMitigation(15)
                .governanceCompleteness(20)
                .shouldReiterate(true)
                .reviewFindings(findingsJson)
                .improvementRecommendations(recsJson)
                .createdAt(Instant.now())
                .build();

        when(governanceReportRepository.findTopByConversationIdOrderByCreatedAtDesc(convId))
                .thenReturn(Optional.of(entity));

        Optional<GovernanceReportDto> result =
                governanceService.getGovernanceReport(convId);

        assertTrue(result.isPresent());
        assertNotNull(result.get().getReviewFindings());
        assertNotNull(result.get().getImprovementRecommendations());
        assertEquals(1, result.get().getImprovementRecommendations().size());
    }

    // ── Helpers ─────────────────────────────────────────────────

    private Map<String, Object> createRiskMap(
            String id, String failureMode, int severity, int occurrence,
            int detection, int rpn) {
        Map<String, Object> risk = new HashMap<>();
        risk.put("id", id);
        risk.put("failure_mode", failureMode);
        risk.put("component", "TestComponent");
        risk.put("cause", "Test cause");
        risk.put("effect", "Test effect");
        risk.put("severity", severity);
        risk.put("occurrence", occurrence);
        risk.put("detection", detection);
        risk.put("rpn", rpn);
        risk.put("current_controls", "None");
        risk.put("recommended_action", "Fix it");
        risk.put("linked_weakness", "W-001");
        risk.put("linked_characteristic", "latency");
        return risk;
    }

    private Map<String, Object> createStructuredOutput(
            int score, boolean shouldReiterate) {
        Map<String, Object> output = new HashMap<>();
        output.put("governance_score", score);
        output.put("iteration", 0);
        output.put("should_reiterate", shouldReiterate);
        output.put("governance_score_breakdown", Map.of(
                "requirement_coverage", 20,
                "architectural_soundness", 18,
                "risk_mitigation", 15,
                "governance_completeness", 22,
                "justification", "Solid design"
        ));
        return output;
    }
}
