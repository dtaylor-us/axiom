package com.archon.api.service;

import com.archon.api.domain.model.ArchitectureOutput;
import com.archon.api.domain.repository.ArchitectureOutputRepository;
import com.archon.api.dto.ArchitectureOutputDto;
import com.archon.api.dto.DiagramCollectionDto;
import com.archon.api.dto.DiagramDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ArchitectureOutputServiceTest {

    @Mock private ArchitectureOutputRepository repository;
    @Spy  private ObjectMapper objectMapper = new ObjectMapper();
    @InjectMocks private ArchitectureOutputService service;

    @Test
    void saveFromStructuredOutput_persistsArchitectureOutput() {
        UUID conversationId = UUID.randomUUID();
        Map<String, Object> structuredOutput = new HashMap<>();
        Map<String, Object> design = new HashMap<>();
        design.put("style", "microservices");
        design.put("domain", "fintech");
        design.put("system_type", "payment platform");
        design.put("components", List.of(
                Map.of("name", "Gateway", "type", "service"),
                Map.of("name", "FraudEngine", "type", "service")
        ));
        design.put("interactions", List.of(
                Map.of("from", "Gateway", "to", "FraudEngine")
        ));
        structuredOutput.put("architecture_design", design);
        structuredOutput.put("characteristics", List.of(
                Map.of("name", "scalability")
        ));
        structuredOutput.put("characteristic_conflicts", List.of());
        structuredOutput.put("mermaid_component_diagram", "graph TD\nA-->B");
        structuredOutput.put("mermaid_sequence_diagram", "sequenceDiagram\nA->>B: call");

        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        service.saveFromStructuredOutput(conversationId, structuredOutput);

        ArgumentCaptor<ArchitectureOutput> captor =
                ArgumentCaptor.forClass(ArchitectureOutput.class);
        verify(repository).save(captor.capture());
        ArchitectureOutput saved = captor.getValue();

        assertEquals(conversationId, saved.getConversationId());
        assertEquals("microservices", saved.getStyle());
        assertEquals("fintech", saved.getDomain());
        assertEquals("payment platform", saved.getSystemType());
        assertEquals(2, saved.getComponentCount());
        assertNotNull(saved.getComponents());
        assertNotNull(saved.getComponentDiagram());
        assertEquals("graph TD\nA-->B", saved.getComponentDiagram());
    }

    @Test
    void saveFromStructuredOutput_handlesNullInput() {
        service.saveFromStructuredOutput(UUID.randomUUID(), null);

        verify(repository, never()).save(any());
    }

    @Test
    void saveFromStructuredOutput_handlesEmptyDesign() {
        UUID conversationId = UUID.randomUUID();
        Map<String, Object> structuredOutput = new HashMap<>();
        // No architecture_design key

        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        service.saveFromStructuredOutput(conversationId, structuredOutput);

        ArgumentCaptor<ArchitectureOutput> captor =
                ArgumentCaptor.forClass(ArchitectureOutput.class);
        verify(repository).save(captor.capture());
        assertEquals(0, captor.getValue().getComponentCount());
    }

    @Test
    void getLatest_returnsDtoWhenPresent() {
        UUID conversationId = UUID.randomUUID();
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("event-driven")
                .domain("fintech")
                .systemType("payment platform")
                .componentCount(3)
                .components("[{\"name\":\"A\"}]")
                .interactions("[]")
                .characteristics("[{\"name\":\"scalability\"}]")
                .conflicts("[]")
                .componentDiagram("graph TD")
                .sequenceDiagram("sequenceDiagram")
                .createdAt(Instant.now())
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<ArchitectureOutputDto> result = service.getLatest(conversationId);

        assertTrue(result.isPresent());
        ArchitectureOutputDto dto = result.get();
        assertEquals("event-driven", dto.getStyle());
        assertEquals("fintech", dto.getDomain());
        assertEquals(3, dto.getComponentCount());
        assertEquals(1, dto.getComponents().size());
    }

    @Test
    void getLatest_returnsEmptyWhenNotFound() {
        UUID conversationId = UUID.randomUUID();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.empty());

        Optional<ArchitectureOutputDto> result = service.getLatest(conversationId);

        assertTrue(result.isEmpty());
    }

    @Test
    void getLatest_handlesNullJsonFields() {
        UUID conversationId = UUID.randomUUID();
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("monolith")
                .componentCount(0)
                .components(null)
                .interactions(null)
                .characteristics(null)
                .conflicts(null)
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<ArchitectureOutputDto> result = service.getLatest(conversationId);

        assertTrue(result.isPresent());
        assertEquals(List.of(), result.get().getComponents());
        assertEquals(List.of(), result.get().getInteractions());
    }

    // -----------------------------------------------------------------------
    // saveFromStructuredOutput — diagrams extraction
    // -----------------------------------------------------------------------

    @Test
    void saveFromStructuredOutput_persistsDiagramsJson() {
        UUID conversationId = UUID.randomUUID();
        Map<String, Object> structuredOutput = new HashMap<>();
        structuredOutput.put("architecture_design", Map.of(
                "style", "microservices",
                "components", List.of(),
                "interactions", List.of()
        ));
        structuredOutput.put("diagrams", List.of(
                Map.of("diagram_id", "D-001", "type", "c4_container",
                        "title", "C4 Container", "description", "View",
                        "mermaid_source", "graph TD\nA-->B",
                        "characteristic_addressed", "modularity")
        ));

        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        service.saveFromStructuredOutput(conversationId, structuredOutput);

        ArgumentCaptor<ArchitectureOutput> captor =
                ArgumentCaptor.forClass(ArchitectureOutput.class);
        verify(repository).save(captor.capture());
        ArchitectureOutput saved = captor.getValue();

        assertNotNull(saved.getDiagramsJson());
        assertTrue(saved.getDiagramsJson().contains("c4_container"));
    }

    // -----------------------------------------------------------------------
    // getDiagramCollection
    // -----------------------------------------------------------------------

    @Test
    void getDiagramCollection_returnsCollectionWhenPresent() {
        UUID conversationId = UUID.randomUUID();
        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4",
               "description":"test","mermaid_source":"graph TD",
               "characteristic_addressed":"modularity"},
              {"diagram_id":"D-002","type":"sequence_primary","title":"Seq",
               "description":"test","mermaid_source":"sequenceDiagram",
               "characteristic_addressed":"performance"}
            ]
            """;
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("microservices")
                .componentCount(0)
                .diagramsJson(diagramsJson)
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<DiagramCollectionDto> result = service.getDiagramCollection(conversationId);

        assertTrue(result.isPresent());
        DiagramCollectionDto dto = result.get();
        assertEquals(2, dto.diagramCount());
        assertEquals(List.of("c4_container", "sequence_primary"), dto.diagramTypes());
        assertEquals("D-001", dto.diagrams().get(0).diagramId());
        assertEquals("C4", dto.diagrams().get(0).title());
    }

    @Test
    void getDiagramCollection_returnsEmptyListWhenNullDiagramsJson() {
        UUID conversationId = UUID.randomUUID();
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("microservices")
                .componentCount(0)
                .diagramsJson(null)
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<DiagramCollectionDto> result = service.getDiagramCollection(conversationId);

        assertTrue(result.isPresent());
        assertEquals(0, result.get().diagramCount());
        assertTrue(result.get().diagrams().isEmpty());
    }

    @Test
    void getDiagramCollection_returnsEmptyWhenNoOutput() {
        UUID conversationId = UUID.randomUUID();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.empty());

        Optional<DiagramCollectionDto> result = service.getDiagramCollection(conversationId);

        assertTrue(result.isEmpty());
    }

    // -----------------------------------------------------------------------
    // getDiagramByType
    // -----------------------------------------------------------------------

    @Test
    void getDiagramByType_returnsDiagramWhenTypeExists() {
        UUID conversationId = UUID.randomUUID();
        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4",
               "description":"test","mermaid_source":"graph TD",
               "characteristic_addressed":"modularity"},
              {"diagram_id":"D-002","type":"sequence_primary","title":"Seq",
               "description":"test","mermaid_source":"sequenceDiagram",
               "characteristic_addressed":"performance"}
            ]
            """;
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("microservices")
                .componentCount(0)
                .diagramsJson(diagramsJson)
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<DiagramDto> result = service.getDiagramByType(conversationId, "sequence_primary");

        assertTrue(result.isPresent());
        assertEquals("D-002", result.get().diagramId());
        assertEquals("sequence_primary", result.get().type());
    }

    @Test
    void getDiagramByType_returnsEmptyForMissingType() {
        UUID conversationId = UUID.randomUUID();
        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4",
               "description":"test","mermaid_source":"graph TD",
               "characteristic_addressed":"modularity"}
            ]
            """;
        ArchitectureOutput entity = ArchitectureOutput.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .style("microservices")
                .componentCount(0)
                .diagramsJson(diagramsJson)
                .build();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.of(entity));

        Optional<DiagramDto> result = service.getDiagramByType(conversationId, "er");

        assertTrue(result.isEmpty());
    }

    @Test
    void getDiagramByType_returnsEmptyWhenNoOutput() {
        UUID conversationId = UUID.randomUUID();
        when(repository.findTopByConversationIdOrderByCreatedAtDesc(conversationId))
                .thenReturn(Optional.empty());

        Optional<DiagramDto> result = service.getDiagramByType(conversationId, "c4_container");

        assertTrue(result.isEmpty());
    }
}
