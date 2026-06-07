package com.archon.api.service;

import com.archon.api.domain.model.TokenUsage;
import com.archon.api.domain.repository.TokenUsageRepository;
import com.archon.api.dto.UsageSummaryDto;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UsageServiceTest {

    @Mock private TokenUsageRepository tokenUsageRepository;

    private UsageService usageService;

    @BeforeEach
    void setUp() {
        usageService = new UsageService(tokenUsageRepository);
    }

    // ── saveFromPayload ─────────────────────────────────────────

    @Test
    void saveFromPayload_persistsEachStage() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> payload = Map.of(
                "stages", Map.of(
                        "req_parsing", Map.of(
                                "stage", "req_parsing",
                                "model", "gpt-4o",
                                "input_tokens", 100,
                                "output_tokens", 50,
                                "total_tokens", 150,
                                "estimated_cost_usd", 0.00075
                        ),
                        "diagram_gen", Map.of(
                                "stage", "diagram_gen",
                                "model", "gpt-4o-mini",
                                "input_tokens", 200,
                                "output_tokens", 100,
                                "total_tokens", 300,
                                "estimated_cost_usd", 0.0009
                        )
                )
        );

        usageService.saveFromPayload(convId, payload);

        verify(tokenUsageRepository, times(2)).save(any(TokenUsage.class));
    }

    @Test
    void saveFromPayload_mapsFieldsCorrectly() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> payload = Map.of(
                "stages", Map.of(
                        "req_parsing", Map.of(
                                "stage", "req_parsing",
                                "model", "gpt-4o",
                                "input_tokens", 500,
                                "output_tokens", 250,
                                "total_tokens", 750,
                                "estimated_cost_usd", 0.00375
                        )
                )
        );

        when(tokenUsageRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        usageService.saveFromPayload(convId, payload);

        ArgumentCaptor<TokenUsage> captor = ArgumentCaptor.forClass(TokenUsage.class);
        verify(tokenUsageRepository).save(captor.capture());

        TokenUsage saved = captor.getValue();
        assertEquals(convId, saved.getConversationId());
        assertEquals("req_parsing", saved.getStage());
        assertEquals("gpt-4o", saved.getModel());
        assertEquals(500, saved.getInputTokens());
        assertEquals(250, saved.getOutputTokens());
        assertEquals(750, saved.getTotalTokens());
    }

    @Test
    void saveFromPayload_handlesNullPayloadGracefully() {
        UUID convId = UUID.randomUUID();

        usageService.saveFromPayload(convId, null);

        verifyNoInteractions(tokenUsageRepository);
    }

    @Test
    void saveFromPayload_handlesNullStagesGracefully() {
        UUID convId = UUID.randomUUID();
        Map<String, Object> payload = Map.of("total_tokens", 100);

        usageService.saveFromPayload(convId, payload);

        verifyNoInteractions(tokenUsageRepository);
    }

    // ── getSummary ──────────────────────────────────────────────

    @Test
    void getSummary_aggregatesAcrossRows() {
        UUID convId = UUID.randomUUID();
        List<TokenUsage> rows = List.of(
                TokenUsage.builder()
                        .conversationId(convId)
                        .stage("req_parsing").model("gpt-4o")
                        .inputTokens(100).outputTokens(50).totalTokens(150)
                        .estimatedCost(BigDecimal.valueOf(0.00075))
                        .createdAt(Instant.now())
                        .build(),
                TokenUsage.builder()
                        .conversationId(convId)
                        .stage("diagram_gen").model("gpt-4o-mini")
                        .inputTokens(200).outputTokens(100).totalTokens(300)
                        .estimatedCost(BigDecimal.valueOf(0.0009))
                        .createdAt(Instant.now())
                        .build()
        );

        when(tokenUsageRepository.findByConversationIdOrderByCreatedAtAsc(convId))
                .thenReturn(rows);

        UsageSummaryDto summary = usageService.getSummary(convId);

        assertEquals(300, summary.getTotalInputTokens());
        assertEquals(150, summary.getTotalOutputTokens());
        assertEquals(450, summary.getTotalTokens());
        assertEquals(2, summary.getStages().size());
        assertEquals(BigDecimal.valueOf(0.00165),
                summary.getEstimatedTotalCost());
    }

    @Test
    void getSummary_returnsEmptyForUnknownConversation() {
        UUID convId = UUID.randomUUID();
        when(tokenUsageRepository.findByConversationIdOrderByCreatedAtAsc(convId))
                .thenReturn(List.of());

        UsageSummaryDto summary = usageService.getSummary(convId);

        assertEquals(0, summary.getTotalInputTokens());
        assertEquals(0, summary.getTotalOutputTokens());
        assertEquals(0, summary.getTotalTokens());
        assertEquals(0, summary.getEstimatedTotalCost().compareTo(BigDecimal.ZERO));
        assertTrue(summary.getStages().isEmpty());
    }
}
