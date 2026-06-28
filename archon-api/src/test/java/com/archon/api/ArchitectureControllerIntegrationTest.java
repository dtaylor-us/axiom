package com.archon.api;

import com.archon.api.domain.model.*;
import com.archon.api.domain.repository.ArchitectureOutputRepository;
import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.domain.repository.MessageRepository;
import com.archon.api.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
@Testcontainers(disabledWithoutDocker = true)
class ArchitectureControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @Autowired private ConversationRepository conversationRepo;
    @Autowired private MessageRepository messageRepo;
    @Autowired private ArchitectureOutputRepository architectureOutputRepo;

    private String validToken;

    @BeforeEach
    void setUp() {
        architectureOutputRepo.deleteAll();
        messageRepo.deleteAll();
        conversationRepo.deleteAll();
        validToken = jwtService.generateToken("test@example.com");
    }

    @Test
    void getArchitecture_returnsOutputWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .domain("fintech")
                .systemType("payment platform")
                .componentCount(2)
                .components("[{\"name\":\"Gateway\"},{\"name\":\"FraudEngine\"}]")
                .interactions("[{\"from\":\"Gateway\",\"to\":\"FraudEngine\"}]")
                .characteristics("[{\"name\":\"scalability\"}]")
                .conflicts("[]")
                .componentDiagram("graph TD\nA-->B")
                .sequenceDiagram("sequenceDiagram\nA->>B: call")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/architecture", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.style").isEqualTo("microservices")
                .jsonPath("$.domain").isEqualTo("fintech")
                .jsonPath("$.componentCount").isEqualTo(2)
                .jsonPath("$.componentDiagram").isNotEmpty();
    }

    @Test
    void getArchitecture_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/architecture", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getArchitecture_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/architecture", UUID.randomUUID())
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void getDiagram_returnsDiagramCollectionWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4 Container",
               "description":"Container view","mermaid_source":"graph TD\\nA-->B",
               "characteristic_addressed":"modularity"},
              {"diagram_id":"D-002","type":"sequence_primary","title":"Primary Sequence",
               "description":"Happy path","mermaid_source":"sequenceDiagram\\nA->>B: call",
               "characteristic_addressed":"performance"}
            ]
            """;

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(1)
                .componentDiagram("graph TD\nA-->B")
                .sequenceDiagram("sequenceDiagram\nA->>B: call")
                .diagramsJson(diagramsJson)
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.diagramCount").isEqualTo(2)
                .jsonPath("$.diagramTypes[0]").isEqualTo("c4_container")
                .jsonPath("$.diagramTypes[1]").isEqualTo("sequence_primary")
                .jsonPath("$.diagrams[0].diagramId").isEqualTo("D-001")
                .jsonPath("$.diagrams[0].title").isEqualTo("C4 Container")
                .jsonPath("$.diagrams[1].type").isEqualTo("sequence_primary");
    }

    @Test
    void getDiagram_returnsEmptyCollectionWhenNoDiagramsJson() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(1)
                .componentDiagram("graph TD\nA-->B")
                .sequenceDiagram("sequenceDiagram\nA->>B: call")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.diagramCount").isEqualTo(0)
                .jsonPath("$.diagrams").isEmpty();
    }

    @Test
    void getDiagram_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getDiagram_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram", UUID.randomUUID())
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void getDiagramByType_returnsSingleDiagramWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4 Container",
               "description":"Container view","mermaid_source":"graph TD\\nA-->B",
               "characteristic_addressed":"modularity"},
              {"diagram_id":"D-002","type":"sequence_primary","title":"Primary Sequence",
               "description":"Happy path","mermaid_source":"sequenceDiagram\\nA->>B: call",
               "characteristic_addressed":"performance"}
            ]
            """;

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(1)
                .diagramsJson(diagramsJson)
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram/{type}", conv.getId(), "c4_container")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.diagramId").isEqualTo("D-001")
                .jsonPath("$.type").isEqualTo("c4_container")
                .jsonPath("$.title").isEqualTo("C4 Container");
    }

    @Test
    void getDiagramByType_returns404ForValidTypeNotGenerated() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        String diagramsJson = """
            [
              {"diagram_id":"D-001","type":"c4_container","title":"C4 Container",
               "description":"Container view","mermaid_source":"graph TD\\nA-->B",
               "characteristic_addressed":"modularity"}
            ]
            """;

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(1)
                .diagramsJson(diagramsJson)
                .build());

        // sequence_primary was not generated — should be 404, not 400
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram/{type}", conv.getId(), "sequence_primary")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getDiagramByType_returns404WhenNoOutput() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/diagram/{type}", conv.getId(), "c4_container")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    // -----------------------------------------------------------------------
    // Trade-offs endpoint
    // -----------------------------------------------------------------------

    @Test
    void getTradeOffs_returnsListWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(0)
                .tradeOffs("[{\"decision\":\"chose async\"}]")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/trade-offs", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].decision").isEqualTo("chose async");
    }

    @Test
    void getTradeOffs_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/trade-offs", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    // -----------------------------------------------------------------------
    // ADL endpoint
    // -----------------------------------------------------------------------

    @Test
    void getAdl_returnsDocumentAndRulesWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(0)
                .adlDocument("DEFINE SYSTEM payment-platform")
                .adlRules("[{\"adl_id\":\"ADL-001\"}]")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/adl", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.document").isEqualTo("DEFINE SYSTEM payment-platform")
                .jsonPath("$.rules[0].adl_id").isEqualTo("ADL-001");
    }

    @Test
    void getAdl_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/adl", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    // -----------------------------------------------------------------------
    // Weaknesses endpoint
    // -----------------------------------------------------------------------

    @Test
    void getWeaknesses_returnsReportWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(0)
                .weaknesses("[{\"area\":\"caching\"}]")
                .weaknessSummary("No caching layer detected")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/weaknesses", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.weaknesses[0].area").isEqualTo("caching")
                .jsonPath("$.summary").isEqualTo("No caching layer detected");
    }

    @Test
    void getWeaknesses_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/weaknesses", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    // -----------------------------------------------------------------------
    // FMEA endpoint
    // -----------------------------------------------------------------------

    @Test
    void getFmea_returnsRisksWhenPresent() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        architectureOutputRepo.save(ArchitectureOutput.builder()
                .conversationId(conv.getId())
                .style("microservices")
                .componentCount(0)
                .fmeaRisks("[{\"component\":\"Gateway\",\"rpn\":120}]")
                .build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/fmea", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].component").isEqualTo("Gateway")
                .jsonPath("$[0].rpn").isEqualTo(120);
    }

    @Test
    void getFmea_returns404WhenMissing() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/fmea", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }
}
