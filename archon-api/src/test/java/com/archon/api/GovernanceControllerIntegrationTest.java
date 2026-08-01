package com.archon.api;

import com.archon.api.dto.FmeaRiskDto;
import com.archon.api.dto.GovernanceReportDto;
import com.archon.api.service.GovernanceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.archon.api.security.JwtService;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
@org.testcontainers.junit.jupiter.Testcontainers(disabledWithoutDocker = true)
class GovernanceControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @MockBean private GovernanceService governanceService;

    private String validToken;
    private UUID sessionId;

    @BeforeEach
    void setUp() {
        validToken = jwtService.generateToken("test-user");
        sessionId = UUID.randomUUID();
    }

    // ── GET /fmea-risks ─────────────────────────────────────────

    @Test
    void getFmeaRisks_returns200WithRisks() {
        FmeaRiskDto dto = FmeaRiskDto.builder()
                .id(UUID.randomUUID())
                .riskId("FMEA-001")
                .failureMode("Gateway timeout")
                .component("PaymentGateway")
                .severity(8)
                .occurrence(5)
                .detection(3)
                .rpn(120)
                .createdAt(Instant.now())
                .build();

        when(governanceService.getFmeaRisks(sessionId))
                .thenReturn(List.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/fmea-risks", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].riskId").isEqualTo("FMEA-001")
                .jsonPath("$[0].rpn").isEqualTo(120)
                .jsonPath("$[0].severity").isEqualTo(8);
    }

    @Test
    void getFmeaRisks_returns200EmptyListWhenNone() {
        when(governanceService.getFmeaRisks(sessionId))
                .thenReturn(List.of());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/fmea-risks", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(0);
    }

    @Test
    void getFmeaRisks_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/fmea-risks", sessionId)
                .exchange()
                .expectStatus().isUnauthorized();
    }

    // ── GET /governance ─────────────────────────────────────────

    @Test
    void getGovernance_returns200WithReport() {
        GovernanceReportDto dto = GovernanceReportDto.builder()
                .id(UUID.randomUUID())
                .conversationId(sessionId)
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

        when(governanceService.getGovernanceReport(sessionId))
                .thenReturn(Optional.of(dto));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/governance", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.governanceScore").isEqualTo(75)
                .jsonPath("$.requirementCoverage").isEqualTo(20)
                .jsonPath("$.shouldReiterate").isEqualTo(false);
    }

    @Test
    void getGovernance_returns404WhenNotFound() {
        when(governanceService.getGovernanceReport(sessionId))
                .thenReturn(Optional.empty());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/governance", sessionId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getGovernance_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/governance", sessionId)
                .exchange()
                .expectStatus().isUnauthorized();
    }
}
