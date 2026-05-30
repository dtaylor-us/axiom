package com.archon.api;

import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.dto.BuyVsBuildDecisionDto;
import com.archon.api.dto.BuyVsBuildSummaryDto;
import com.archon.api.security.JwtService;
import com.archon.api.service.BuyVsBuildService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
class BuyVsBuildControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;

    @MockBean private BuyVsBuildService buyVsBuildService;
    @MockBean private ConversationRepository conversationRepository;

    private String validToken;
    private UUID conversationId;

    @BeforeEach
    void setUp() {
        validToken = jwtService.generateToken("test-user");
        conversationId = UUID.randomUUID();

        when(conversationRepository.findByIdAndUserId(eq(conversationId), anyString()))
                .thenReturn(Optional.of(Conversation.builder()
                        .id(conversationId)
                        .userId("test-user")
                        .title("t")
                        .build()));
    }

    @Test
    void getBuildAnalysis_withoutToken_returns401() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis", conversationId)
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void getBuildAnalysis_returnsBuyVsBuildSummaryDto() {
        BuyVsBuildDecisionDto d = BuyVsBuildDecisionDto.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .componentName("Payments")
                .recommendation("buy")
                .rationale("Buy Stripe; building payment processing is a high-risk, non-core capability.")
                .alternativesConsidered(List.of("Stripe", "Adyen"))
                .recommendedSolution("Stripe")
                .estimatedBuildCost("~$500/month")
                .vendorLockInRisk("high")
                .integrationEffort("low")
                .conflictsWithUserPreference(true)
                .conflictExplanation("User wants in-house; best practice forbids building payment processing.")
                .isCoreeDifferentiator(false)
                .createdAt(Instant.now())
                .build();

        when(buyVsBuildService.getSummary(conversationId)).thenReturn(
                new BuyVsBuildSummaryDto("Summary", 1, 0, 1, 0, 1, List.of(d))
        );

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.totalDecisions").isEqualTo(1)
                .jsonPath("$.buyCount").isEqualTo(1)
                .jsonPath("$.decisions[0].componentName").isEqualTo("Payments");
    }

    @Test
    void getBuildAnalysis_recommendationQueryParam_filtersCorrectly() {
        BuyVsBuildDecisionDto build = BuyVsBuildDecisionDto.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .componentName("Core")
                .recommendation("build")
                .rationale("Core logic is differentiating and must be built.")
                .alternativesConsidered(List.of("Custom build", "ERP module"))
                .recommendedSolution("")
                .estimatedBuildCost("2-4 weeks")
                .vendorLockInRisk("low")
                .integrationEffort("medium")
                .conflictsWithUserPreference(false)
                .conflictExplanation("")
                .isCoreeDifferentiator(true)
                .createdAt(Instant.now())
                .build();

        when(buyVsBuildService.getSummary(conversationId)).thenReturn(
                new BuyVsBuildSummaryDto("Summary", 2, 1, 1, 0, 0, List.of(build))
        );
        when(buyVsBuildService.getByRecommendation(conversationId, "build"))
                .thenReturn(List.of(build));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis?recommendation=build", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.totalDecisions").isEqualTo(1)
                .jsonPath("$.buildCount").isEqualTo(1)
                .jsonPath("$.decisions[0].recommendation").isEqualTo("build");
    }

    @Test
    void getBuildAnalysis_returns404WhenNoDecisionsExist() {
        when(buyVsBuildService.getSummary(conversationId))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "No buy-vs-build decisions found"));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getBuildAnalysisConflicts_returnsOnlyConflictingDecisions() {
        BuyVsBuildDecisionDto ok = BuyVsBuildDecisionDto.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .componentName("Search")
                .recommendation("adopt")
                .rationale("Adopt OpenSearch; mature OSS and manageable ops.")
                .alternativesConsidered(List.of("OpenSearch", "Elasticsearch"))
                .recommendedSolution("OpenSearch")
                .estimatedBuildCost("~$200/month infra")
                .vendorLockInRisk("low")
                .integrationEffort("medium")
                .conflictsWithUserPreference(false)
                .conflictExplanation("")
                .isCoreeDifferentiator(false)
                .createdAt(Instant.now())
                .build();

        BuyVsBuildDecisionDto conflict = BuyVsBuildDecisionDto.builder()
                .id(UUID.randomUUID())
                .conversationId(conversationId)
                .componentName("Payments")
                .recommendation("buy")
                .rationale("Buy Stripe; never build payment processing.")
                .alternativesConsidered(List.of("Stripe", "Adyen"))
                .recommendedSolution("Stripe")
                .estimatedBuildCost("~$500/month")
                .vendorLockInRisk("high")
                .integrationEffort("low")
                .conflictsWithUserPreference(true)
                .conflictExplanation("User wants in-house; payment processing should not be built.")
                .isCoreeDifferentiator(false)
                .createdAt(Instant.now())
                .build();

        when(buyVsBuildService.getDecisions(conversationId)).thenReturn(List.of(ok, conflict));

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis/conflicts", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(1)
                .jsonPath("$[0].componentName").isEqualTo("Payments");
    }

    @Test
    void getBuildAnalysisConflicts_returnsEmptyListWhenNoConflicts() {
        when(buyVsBuildService.getDecisions(conversationId)).thenReturn(List.of());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/build-analysis/conflicts", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(0);
    }
}

