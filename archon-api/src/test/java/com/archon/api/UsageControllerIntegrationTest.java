package com.archon.api;

import com.archon.api.dto.TokenUsageDto;
import com.archon.api.dto.UsageSummaryDto;
import com.archon.api.security.JwtService;
import com.archon.api.service.UsageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
class UsageControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @MockBean private UsageService usageService;

    private String validToken;
    private UUID conversationId;

    @BeforeEach
    void setUp() {
        validToken = jwtService.generateToken("test-user");
        conversationId = UUID.randomUUID();
    }

    @Test
    void getUsage_returns200WithSummary() {
        UsageSummaryDto summary = UsageSummaryDto.builder()
                .totalInputTokens(300)
                .totalOutputTokens(150)
                .totalTokens(450)
                .estimatedTotalCost(BigDecimal.valueOf(0.00165))
                .stages(List.of(
                        TokenUsageDto.builder()
                                .stage("req_parsing")
                                .model("gpt-4o")
                                .inputTokens(100)
                                .outputTokens(50)
                                .totalTokens(150)
                                .estimatedCost(BigDecimal.valueOf(0.00075))
                                .build(),
                        TokenUsageDto.builder()
                                .stage("diagram_gen")
                                .model("gpt-4o-mini")
                                .inputTokens(200)
                                .outputTokens(100)
                                .totalTokens(300)
                                .estimatedCost(BigDecimal.valueOf(0.0009))
                                .build()
                ))
                .build();

        when(usageService.getSummary(conversationId)).thenReturn(summary);

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/usage", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.totalInputTokens").isEqualTo(300)
                .jsonPath("$.totalOutputTokens").isEqualTo(150)
                .jsonPath("$.totalTokens").isEqualTo(450)
                .jsonPath("$.stages.length()").isEqualTo(2)
                .jsonPath("$.stages[0].stage").isEqualTo("req_parsing");
    }

    @Test
    void getUsage_returns200EmptyForUnknownConversation() {
        UsageSummaryDto empty = UsageSummaryDto.builder()
                .totalInputTokens(0)
                .totalOutputTokens(0)
                .totalTokens(0)
                .estimatedTotalCost(BigDecimal.ZERO)
                .stages(List.of())
                .build();

        when(usageService.getSummary(conversationId)).thenReturn(empty);

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/usage", conversationId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.totalTokens").isEqualTo(0)
                .jsonPath("$.stages.length()").isEqualTo(0);
    }

    @Test
    void getUsage_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/conversations/{id}/usage", conversationId)
                .exchange()
                .expectStatus().isUnauthorized();
    }
}
