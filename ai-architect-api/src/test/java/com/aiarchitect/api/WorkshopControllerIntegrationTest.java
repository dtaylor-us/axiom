package com.aiarchitect.api;

import com.aiarchitect.api.security.JwtService;
import com.aiarchitect.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopMessageRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopSessionRepository;
import com.aiarchitect.api.workshop.service.WorkshopService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.reactive.server.WebTestClient;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.UUID;

import com.aiarchitect.api.workshop.dto.WorkshopSessionDto;
import com.aiarchitect.api.workshop.dto.WorkshopTurnResponseDto;
import com.aiarchitect.api.workshop.dto.AttributeSummaryDto;
import com.aiarchitect.api.workshop.dto.GenerationReadinessDto;
import com.aiarchitect.api.workshop.dto.WorkshopGenerationResponseDto;
import com.aiarchitect.api.workshop.dto.WorkshopScenarioDto;
import com.aiarchitect.api.workshop.dto.AttributeResolutionDto;
import com.aiarchitect.api.workshop.dto.ResolvedAnswerDto;

import java.time.Instant;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
@org.testcontainers.junit.jupiter.Testcontainers(disabledWithoutDocker = true)
class WorkshopControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @Autowired private WorkshopSessionRepository sessionRepo;
    @Autowired private WorkshopAttributeRepository attributeRepo;
    @Autowired private WorkshopMessageRepository messageRepo;
    @MockBean private WorkshopService workshopService;

    private String validToken;
    private static final UUID SESSION_ID = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        messageRepo.deleteAll();
        attributeRepo.deleteAll();
        sessionRepo.deleteAll();
        validToken = jwtService.generateToken("test@example.com");
    }

    private WorkshopSessionDto sampleSession() {
        return new WorkshopSessionDto(
                SESSION_ID, "Payment Service", "CONTEXT_SETTING",
                0, 0, 0, 0, 0, 0, 0,
                false, false, false,
                List.of(),
                Instant.now(), Instant.now(),
                0, false
        );
    }

    // ── Security ─────────────────────────────────────────────────────────────

    @Test
    void createSession_returns401WithoutToken() {
        webTestClient.post().uri("/api/v1/workshop/sessions")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"systemName\":\"TestSys\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void createSession_returns401WithInvalidToken() {
        webTestClient.post().uri("/api/v1/workshop/sessions")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer bad-token")
                .bodyValue("{\"systemName\":\"TestSys\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    // ── Create session ────────────────────────────────────────────────────────

    @Test
    void createSession_returns201WithValidRequest() {
        when(workshopService.createSession(any(), eq("Payment Service")))
                .thenReturn(sampleSession());

        webTestClient.post().uri("/api/v1/workshop/sessions")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"systemName\":\"Payment Service\"}")
                .exchange()
                .expectStatus().isCreated()
                .expectBody()
                .jsonPath("$.systemName").isEqualTo("Payment Service");
    }

    @Test
    void createSession_returns400WhenSystemNameBlank() {
        webTestClient.post().uri("/api/v1/workshop/sessions")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"systemName\":\"\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }

    // ── Submit turn ───────────────────────────────────────────────────────────

    @Test
    void submitTurn_returns200WithAgentMessage() {
        WorkshopTurnResponseDto.GapSummaryDto gapSummary =
                new WorkshopTurnResponseDto.GapSummaryDto(3, 0, 0, 0, List.of());
        WorkshopTurnResponseDto turnResponse = new WorkshopTurnResponseDto(
                SESSION_ID, 1, "CONTEXT_SETTING",
                "Tell me more about your users.",
                List.of(), gapSummary, List.of(), false, false, List.of()
        );

        when(workshopService.processTurn(eq(SESSION_ID), any(), eq("We process payments")))
                .thenReturn(turnResponse);

        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/turn")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"userInput\":\"We process payments\"}")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.agentMessage").isEqualTo("Tell me more about your users.")
                .jsonPath("$.turnNumber").isEqualTo(1);
    }

    @Test
    void submitTurn_returns400WhenUserInputBlank() {
        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/turn")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"userInput\":\"\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }

    // ── Get session ───────────────────────────────────────────────────────────

    @Test
    void getSession_returnsSession() {
        when(workshopService.getSession(eq(SESSION_ID), any()))
                .thenReturn(sampleSession());

        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.sessionId").isEqualTo(SESSION_ID.toString());
    }

    @Test
    void getResolutions_returns200WithTraceability() {
        AttributeResolutionDto row = new AttributeResolutionDto(
                "QA-001",
                "Scalability",
                List.of(new ResolvedAnswerDto("What metrics?", "Throughput", 2, "50k/min")),
                List.of("Still open?"),
                1,
                1);
        when(workshopService.getResolutions(eq(SESSION_ID), any())).thenReturn(List.of(row));

        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/resolutions")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].attributeId").isEqualTo("QA-001")
                .jsonPath("$[0].resolvedCount").isEqualTo(1)
                .jsonPath("$[0].openCount").isEqualTo(1);
    }

    @Test
    void getScenarios_returns200WithEmptyListBeforeTurns() {
        when(workshopService.getScenarios(eq(SESSION_ID), any())).thenReturn(List.of());

        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/scenarios")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(0);
    }

    @Test
    void getScenarios_returnsScenarioWithServerComputedCompleteness() {
        WorkshopScenarioDto dto = new WorkshopScenarioDto(
                "SC-1",
                "AKS failure",
                "node fails during seasonal run",
                "k8s",
                "seasonal window",
                "calc engine",
                "isolate and resume",
                "",
                List.of("Recoverability"),
                "quote",
                2,
                "needs_measure"
        );
        when(workshopService.getScenarios(eq(SESSION_ID), any())).thenReturn(List.of(dto));

        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/scenarios")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$[0].completeness").isEqualTo("needs_measure")
                .jsonPath("$[0].scenarioId").isEqualTo("SC-1");
    }

    // ── Complete session ──────────────────────────────────────────────────────

    @Test
    void completeSession_returnsAttributeSummary() {
        AttributeSummaryDto summary = new AttributeSummaryDto(
                "Payment Service", List.of(), List.of(),
                "75%", "Good coverage.",
                false, "Proceed to architecture generation."
        );
        when(workshopService.completeSession(eq(SESSION_ID), any()))
                .thenReturn(summary);

        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/complete")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.elicitationCompleteness").isEqualTo("75%");
    }

    // ── Send to pipeline ──────────────────────────────────────────────────────

    @Test
    void sendToPipeline_returnsConversationId() {
        UUID convId = UUID.randomUUID();
        when(workshopService.sendToPipeline(eq(SESSION_ID), any())).thenReturn(convId);

        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/send-to-pipeline")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.conversationId").isEqualTo(convId.toString());
    }

    // ── List sessions ─────────────────────────────────────────────────────────

    @Test
    void listSessions_returnsEmptyArray() {
        when(workshopService.listSessions(any())).thenReturn(List.of());

        webTestClient.get().uri("/api/v1/workshop/sessions")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(0);
    }

    // ── Generation readiness & on-demand generate ─────────────────────────────

    @Test
    void getGenerationReadiness_returns200() {
        GenerationReadinessDto dto = new GenerationReadinessDto(
                "partial", "note", List.of(), List.of(), List.of(), true);
        when(workshopService.assessGenerationReadiness(eq(SESSION_ID), any()))
                .thenReturn(dto);

        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/generation-readiness")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.overallReadiness").isEqualTo("partial");
    }

    @Test
    void getGenerationReadiness_returns401WithoutToken() {
        webTestClient.get().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/generation-readiness")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void generateAttributes_returns200() {
        WorkshopGenerationResponseDto dto = new WorkshopGenerationResponseDto(
                SESSION_ID,
                1,
                "partial",
                "note",
                2,
                List.of(),
                List.of(),
                List.of(),
                "summary",
                List.of(),
                true,
                "Continue refining.",
                false);
        when(workshopService.generateAttributes(eq(SESSION_ID), any()))
                .thenReturn(dto);

        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/generate")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.generationCount").isEqualTo(1);
    }

    @Test
    void generateAttributes_returns401WithoutToken() {
        webTestClient.post().uri("/api/v1/workshop/sessions/" + SESSION_ID + "/generate")
                .exchange()
                .expectStatus().isUnauthorized();
    }
}
