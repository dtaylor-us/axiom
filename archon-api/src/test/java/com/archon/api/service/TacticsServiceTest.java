package com.archon.api.service;

import com.archon.api.domain.model.ArchitectureTactic;
import com.archon.api.domain.repository.TacticRepository;
import com.archon.api.dto.TacticDto;
import com.archon.api.dto.TacticsSummaryDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link TacticsService}.
 *
 * <p>Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 */
@ExtendWith(MockitoExtension.class)
class TacticsServiceTest {

    @Mock  private TacticRepository tacticRepository;
    @Spy   private ObjectMapper objectMapper = new ObjectMapper();

    private TacticsService tacticsService;

    @BeforeEach
    void setUp() {
        tacticsService = new TacticsService(tacticRepository, objectMapper);
    }

    // -----------------------------------------------------------------------
    // saveTactics
    // -----------------------------------------------------------------------

    @Test
    void saveTactics_persistsAllTactics() {
        UUID convId = UUID.randomUUID();
        List<Map<String, Object>> tactics = List.of(
                createTacticMap("T-001", "Circuit Breaker", "availability", false, "medium", "critical"),
                createTacticMap("T-002", "Caching", "performance", false, "low", "recommended")
        );

        tacticsService.saveTactics(convId, tactics);

        verify(tacticRepository, times(2)).save(any(ArchitectureTactic.class));
    }

    @Test
    void saveTactics_mapsFieldsCorrectly() {
        UUID convId = UUID.randomUUID();
        List<Map<String, Object>> tactics = List.of(
                createTacticMap("T-001", "Circuit Breaker", "availability", false, "medium", "critical")
        );

        when(tacticRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        tacticsService.saveTactics(convId, tactics);

        ArgumentCaptor<ArchitectureTactic> captor =
                ArgumentCaptor.forClass(ArchitectureTactic.class);
        verify(tacticRepository).save(captor.capture());

        ArchitectureTactic saved = captor.getValue();
        assertEquals(convId, saved.getConversationId());
        assertEquals("T-001", saved.getTacticId());
        assertEquals("Circuit Breaker", saved.getTacticName());
        assertEquals("availability", saved.getCharacteristicName());
        assertEquals("medium", saved.getEffort());
        assertEquals("critical", saved.getPriority());
        assertFalse(saved.isAlreadyAddressed());
    }

    @Test
    void saveTactics_mapsAlreadyAddressedTrue() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> tactic = createTacticMap(
                "T-003", "Redundancy", "availability", true, "high", "recommended");

        when(tacticRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        tacticsService.saveTactics(convId, List.of(tactic));

        ArgumentCaptor<ArchitectureTactic> captor =
                ArgumentCaptor.forClass(ArchitectureTactic.class);
        verify(tacticRepository).save(captor.capture());
        assertTrue(captor.getValue().isAlreadyAddressed());
    }

    @Test
    void saveTactics_serialisesImplementationExamplesAsJson() throws Exception {
        UUID convId = UUID.randomUUID();
        Map<String, Object> tactic = createTacticMap("T-001", "Circuit Breaker", "availability", false, "medium", "critical");
        tactic = new java.util.HashMap<>(tactic);
        tactic.put("implementation_examples", List.of("Resilience4j", "Hystrix"));

        when(tacticRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        tacticsService.saveTactics(convId, List.of(tactic));

        ArgumentCaptor<ArchitectureTactic> captor =
                ArgumentCaptor.forClass(ArchitectureTactic.class);
        verify(tacticRepository).save(captor.capture());

        String json = captor.getValue().getImplementationExamples();
        assertNotNull(json);
        assertTrue(json.contains("Resilience4j"));
        assertTrue(json.contains("Hystrix"));
    }

    @Test
    void saveTactics_doesNotThrowOnEmptyList() {
        UUID convId = UUID.randomUUID();
        assertDoesNotThrow(() ->
                tacticsService.saveTactics(convId, List.of()));
        verify(tacticRepository, never()).save(any());
    }

    // -----------------------------------------------------------------------
    // getTactics — no filter
    // -----------------------------------------------------------------------

    @Test
    void getTactics_returnsAllWhenNoFilters() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-001", "availability", "critical", false),
                buildEntity(convId, "T-002", "performance", "recommended", false)
        );
        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(entities);

        List<TacticDto> result = tacticsService.getTactics(convId, null, null, false);

        assertEquals(2, result.size());
        assertEquals("T-001", result.get(0).getTacticId());
    }

    @Test
    void getTactics_filtersByCharacteristic() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-001", "availability", "critical", false)
        );
        when(tacticRepository.findByConversationIdAndCharacteristicNameOrderByPriorityAsc(
                convId, "availability"))
                .thenReturn(entities);

        List<TacticDto> result = tacticsService.getTactics(convId, "availability", null, false);

        assertEquals(1, result.size());
        assertEquals("availability", result.get(0).getCharacteristicName());
    }

    @Test
    void getTactics_filtersByPriority() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-001", "availability", "critical", false)
        );
        when(tacticRepository.findByConversationIdAndPriorityOrderByTacticNameAsc(
                convId, "critical"))
                .thenReturn(entities);

        List<TacticDto> result = tacticsService.getTactics(convId, null, "critical", false);

        assertEquals(1, result.size());
        assertEquals("critical", result.get(0).getPriority());
    }

    @Test
    void getTactics_filtersByNewOnly() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-002", "performance", "recommended", false)
        );
        when(tacticRepository
                .findByConversationIdAndAlreadyAddressedFalseOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(entities);

        List<TacticDto> result = tacticsService.getTactics(convId, null, null, true);

        assertEquals(1, result.size());
        assertFalse(result.get(0).isAlreadyAddressed());
    }

    // -----------------------------------------------------------------------
    // getTacticsSummary
    // -----------------------------------------------------------------------

    @Test
    void getTacticsSummary_returnsCorrectCounts() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-001", "availability", "critical", false),
                buildEntity(convId, "T-002", "availability", "critical", true),
                buildEntity(convId, "T-003", "performance", "recommended", false)
        );
        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(entities);

        TacticsSummaryDto summary = tacticsService.getTacticsSummary(convId);

        assertEquals(3, summary.getTotalTactics());
        assertEquals(2, summary.getCriticalCount());
        assertEquals(1, summary.getAlreadyAddressedCount());
        assertEquals(2, summary.getNewTacticsCount());
    }

    @Test
    void getTacticsSummary_groupsPerCharacteristic() {
        UUID convId = UUID.randomUUID();
        List<ArchitectureTactic> entities = List.of(
                buildEntity(convId, "T-001", "availability", "critical", false),
                buildEntity(convId, "T-002", "availability", "recommended", false),
                buildEntity(convId, "T-003", "performance", "recommended", false)
        );
        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(entities);

        TacticsSummaryDto summary = tacticsService.getTacticsSummary(convId);

        assertEquals(2L, summary.getPerCharacteristic().get("availability"));
        assertEquals(1L, summary.getPerCharacteristic().get("performance"));
    }

    @Test
    void getTacticsSummary_topCriticalTacticsLimitedToFive() {
        UUID convId = UUID.randomUUID();
        // 7 critical unaddressed tactics
        List<ArchitectureTactic> entities = new java.util.ArrayList<>();
        for (int i = 1; i <= 7; i++) {
            entities.add(buildEntity(convId, "T-" + String.format("%03d", i),
                    "availability", "critical", false));
        }
        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(entities);

        TacticsSummaryDto summary = tacticsService.getTacticsSummary(convId);

        assertEquals(5, summary.getTopCriticalTactics().size());
    }

    @Test
    void getTacticsSummary_returns0ForEmptyList() {
        UUID convId = UUID.randomUUID();
        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(List.of());

        TacticsSummaryDto summary = tacticsService.getTacticsSummary(convId);

        assertEquals(0, summary.getTotalTactics());
        assertEquals(0, summary.getCriticalCount());
        assertEquals(0, summary.getNewTacticsCount());
        assertTrue(summary.getTopCriticalTactics().isEmpty());
    }

    // -----------------------------------------------------------------------
    // DTO mapping
    // -----------------------------------------------------------------------

    @Test
    void getTactics_deserialisesImplementationExamples() throws Exception {
        UUID convId = UUID.randomUUID();
        ArchitectureTactic entity = buildEntity(convId, "T-001", "availability", "critical", false);
        entity.setImplementationExamples("[\"Resilience4j\",\"Hystrix\"]");

        when(tacticRepository.findByConversationIdOrderByPriorityAscTacticNameAsc(convId))
                .thenReturn(List.of(entity));

        List<TacticDto> result = tacticsService.getTactics(convId, null, null, false);

        assertFalse(result.get(0).getImplementationExamples().isEmpty());
        assertEquals("Resilience4j", result.get(0).getImplementationExamples().get(0));
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private Map<String, Object> createTacticMap(
            String tacticId, String tacticName, String characteristic,
            boolean addressed, String effort, String priority) {
        Map<String, Object> map = new java.util.HashMap<>();
        map.put("tactic_id", tacticId);
        map.put("tactic_name", tacticName);
        map.put("characteristic_name", characteristic);
        map.put("category", "detect faults");
        map.put("description", "Prevent cascading failures in the system.");
        map.put("concrete_application", "Apply this tactic in the payment gateway layer.");
        map.put("implementation_examples", List.of("Resilience4j"));
        map.put("already_addressed", addressed);
        map.put("address_evidence", "");
        map.put("effort", effort);
        map.put("priority", priority);
        return map;
    }

    private ArchitectureTactic buildEntity(UUID convId, String tacticId,
                                           String characteristic, String priority,
                                           boolean addressed) {
        return ArchitectureTactic.builder()
                .id(UUID.randomUUID())
                .conversationId(convId)
                .tacticId(tacticId)
                .tacticName("Tactic " + tacticId)
                .characteristicName(characteristic)
                .category("detect faults")
                .description("A tactic for " + characteristic)
                .concreteApplication("Apply to the gateway layer of this system.")
                .implementationExamples("[]")
                .alreadyAddressed(addressed)
                .addressEvidence("")
                .effort("medium")
                .priority(priority)
                .createdAt(Instant.now())
                .build();
    }
}
