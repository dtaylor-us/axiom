package com.archon.api;

import com.archon.api.dto.TacticDto;
import com.archon.api.dto.TacticsSummaryDto;
import com.archon.api.security.JwtService;
import com.archon.api.service.TacticsService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

/**
 * Integration tests for {@link com.archon.api.controller.TacticsController}.
 *
 * <p>Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
class TacticsControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @MockBean  private TacticsService tacticsService;

    private String validToken;
    private UUID sessionId;

    @BeforeEach
    void setUp() {
        validToken = jwtService.generateToken("test-user");
        sessionId = UUID.randomUUID();
    }

    // -----------------------------------------------------------------------
    // GET /api/v1/sessions/{id}/tactics
    // -----------------------------------------------------------------------

    @Test
    void getTactics_returns200WithTactics() {
        TacticDto dto = buildDto("T-001", "Circuit Breaker", "availability",
                "critical", false);

        when(tacticsService.getTactics(eq(sessionId), isNull(), isNull(), eq(false)))
                .thenReturn(List.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].tacticId").isEqualTo("T-001")
                .jsonPath("$[0].tacticName").isEqualTo("Circuit Breaker")
                .jsonPath("$[0].priority").isEqualTo("critical");
    }

    @Test
    void getTactics_returns200EmptyListWhenNone() {
        when(tacticsService.getTactics(eq(sessionId), isNull(), isNull(), eq(false)))
                .thenReturn(List.of());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(0);
    }

    @Test
    void getTactics_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics", sessionId)
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void getTactics_passesCharacteristicFilterToService() {
        TacticDto dto = buildDto("T-001", "Circuit Breaker", "availability",
                "critical", false);

        when(tacticsService.getTactics(eq(sessionId), eq("availability"), isNull(), eq(false)))
                .thenReturn(List.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics?characteristic=availability", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].characteristicName").isEqualTo("availability");
    }

    @Test
    void getTactics_passesPriorityFilterToService() {
        TacticDto dto = buildDto("T-001", "Circuit Breaker", "availability",
                "critical", false);

        when(tacticsService.getTactics(eq(sessionId), isNull(), eq("critical"), eq(false)))
                .thenReturn(List.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics?priority=critical", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].priority").isEqualTo("critical");
    }

    @Test
    void getTactics_passesNewOnlyFilterToService() {
        TacticDto dto = buildDto("T-002", "Caching", "performance", "recommended", false);

        when(tacticsService.getTactics(eq(sessionId), isNull(), isNull(), eq(true)))
                .thenReturn(List.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics?newOnly=true", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].tacticId").isEqualTo("T-002");
    }

    // -----------------------------------------------------------------------
    // GET /api/v1/sessions/{id}/tactics/summary
    // -----------------------------------------------------------------------

    @Test
    void getTacticsSummary_returns200WithSummary() {
        TacticsSummaryDto summary = TacticsSummaryDto.builder()
                .totalTactics(5)
                .criticalCount(2)
                .alreadyAddressedCount(1)
                .newTacticsCount(4)
                .perCharacteristic(Map.of("availability", 3L, "performance", 2L))
                .summary("Availability is the dominant quality concern.")
                .topCriticalTactics(List.of("Circuit Breaker", "Health Monitoring"))
                .build();

        when(tacticsService.getTacticsSummary(sessionId)).thenReturn(summary);

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics/summary", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.totalTactics").isEqualTo(5)
                .jsonPath("$.criticalCount").isEqualTo(2)
                .jsonPath("$.alreadyAddressedCount").isEqualTo(1)
                .jsonPath("$.newTacticsCount").isEqualTo(4)
                .jsonPath("$.topCriticalTactics[0]").isEqualTo("Circuit Breaker");
    }

    @Test
    void getTacticsSummary_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/tactics/summary", sessionId)
                .exchange()
                .expectStatus().isUnauthorized();
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private TacticDto buildDto(String tacticId, String tacticName,
                                String characteristic, String priority,
                                boolean addressed) {
        return TacticDto.builder()
                .id(UUID.randomUUID())
                .tacticId(tacticId)
                .tacticName(tacticName)
                .characteristicName(characteristic)
                .category("detect faults")
                .description("Prevent cascading failures in the distributed system.")
                .concreteApplication("Apply this tactic at the payment gateway layer.")
                .implementationExamples(List.of("Resilience4j"))
                .alreadyAddressed(addressed)
                .addressEvidence("")
                .effort("medium")
                .priority(priority)
                .createdAt(Instant.now())
                .build();
    }
}
