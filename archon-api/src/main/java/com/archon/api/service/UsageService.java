package com.archon.api.service;

import com.archon.api.domain.model.TokenUsage;
import com.archon.api.domain.repository.TokenUsageRepository;
import com.archon.api.dto.TokenUsageDto;
import com.archon.api.dto.UsageSummaryDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Persists and queries per-stage LLM token usage.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class UsageService {

    private final TokenUsageRepository tokenUsageRepository;

    /**
     * Persist token usage data from the agent's COMPLETE payload.
     *
     * @param conversationId the conversation UUID
     * @param tokenUsageMap  the token_usage map from the agent payload
     */
    @Transactional
    public void saveFromPayload(UUID conversationId,
                                Map<String, Object> tokenUsageMap) {
        if (tokenUsageMap == null) {
            return;
        }

        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> stages =
                (Map<String, Map<String, Object>>) tokenUsageMap.get("stages");
        if (stages == null) {
            return;
        }

        for (var entry : stages.entrySet()) {
            Map<String, Object> s = entry.getValue();
            TokenUsage tu = TokenUsage.builder()
                    .conversationId(conversationId)
                    .stage(stringOrDefault(s, "stage", entry.getKey()))
                    .model(stringOrDefault(s, "model", "unknown"))
                    .inputTokens(intOrZero(s, "input_tokens"))
                    .outputTokens(intOrZero(s, "output_tokens"))
                    .totalTokens(intOrZero(s, "total_tokens"))
                    .estimatedCost(decimalOrZero(s, "estimated_cost_usd"))
                    .build();
            tokenUsageRepository.save(tu);
        }

        log.info("Persisted token usage for {} stages, conversation={}",
                 stages.size(), conversationId);
    }

    /**
     * Retrieve aggregated usage summary for a conversation.
     */
    @Transactional(readOnly = true)
    public UsageSummaryDto getSummary(UUID conversationId) {
        List<TokenUsage> rows = tokenUsageRepository
                .findByConversationIdOrderByCreatedAtAsc(conversationId);

        List<TokenUsageDto> stageDtos = rows.stream()
                .map(tu -> TokenUsageDto.builder()
                        .stage(tu.getStage())
                        .model(tu.getModel())
                        .inputTokens(tu.getInputTokens())
                        .outputTokens(tu.getOutputTokens())
                        .totalTokens(tu.getTotalTokens())
                        .estimatedCost(tu.getEstimatedCost())
                        .build())
                .toList();

        int totalIn = rows.stream().mapToInt(TokenUsage::getInputTokens).sum();
        int totalOut = rows.stream().mapToInt(TokenUsage::getOutputTokens).sum();
        BigDecimal totalCost = rows.stream()
                .map(TokenUsage::getEstimatedCost)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        return UsageSummaryDto.builder()
                .totalInputTokens(totalIn)
                .totalOutputTokens(totalOut)
                .totalTokens(totalIn + totalOut)
                .estimatedTotalCost(totalCost)
                .stages(stageDtos)
                .build();
    }

    private String stringOrDefault(Map<String, Object> m, String key, String def) {
        Object v = m.get(key);
        return v != null ? v.toString() : def;
    }

    private int intOrZero(Map<String, Object> m, String key) {
        Object v = m.get(key);
        if (v instanceof Number n) {
            return n.intValue();
        }
        return 0;
    }

    private BigDecimal decimalOrZero(Map<String, Object> m, String key) {
        Object v = m.get(key);
        if (v instanceof Number n) {
            return BigDecimal.valueOf(n.doubleValue());
        }
        return BigDecimal.ZERO;
    }
}
