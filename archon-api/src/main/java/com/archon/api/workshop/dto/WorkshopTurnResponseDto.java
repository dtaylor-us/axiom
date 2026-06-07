package com.archon.api.workshop.dto;

import java.util.List;
import java.util.UUID;

/**
 * Response from POST /api/v1/workshop/sessions/{id}/turn.
 *
 * <p>Contains the agent's full message for this turn, the gap summary
 * for the progress panel, and the current attribute list for the
 * right panel. All UI state needed for a complete render is present
 * so the client does not need a second request.</p>
 */
public record WorkshopTurnResponseDto(
        UUID sessionId,
        int turnNumber,
        String workshopPhase,
        String agentMessage,
        List<String> questionsAsked,
        GapSummaryDto gapSummary,
        List<QualityAttributeDto> attributes,
        boolean isComplete,
        boolean readyForPipeline,
        List<NonQaConcernDto> nonQaConcerns
) {

    /**
     * Gap summary nested within the turn response.
     *
     * @param total         total gaps identified so far
     * @param filled        gaps answered by the user
     * @param completionPct percentage of gaps filled (0-100)
     * @param openGaps      list of open gap descriptions for the UI
     */
    public record GapSummaryDto(
            int total,
            int filled,
            int completionPct,
            /** Gaps with resolution confidence ≥ 0.5 but below the filled threshold. */
            int inProgressCount,
            List<OpenGapDto> openGaps
    ) {}

    /**
     * One open gap displayed in the centre panel.
     *
     * @param gapId       stable gap identifier
     * @param category    QAW category: business_context | usage_context |
     *                    technical_context | risk_priority
     * @param description human-readable description of what is missing
     * @param priority    critical | high | medium | low
     */
    public record OpenGapDto(
            String gapId,
            String category,
            String description,
            String priority,
            String residualQuestion,
            double resolutionConfidence
    ) {}

    /**
     * A concern raised by the user that is not a quality attribute.
     *
     * <p>Examples: regulatory constraints (GDPR, HIPAA), team-size concerns,
     * time-to-market pressure. These are tracked but excluded from the
     * quality attribute count.
     *
     * @param name        short concern label
     * @param description what the user said
     * @param category    rough grouping: regulatory | organisational | delivery | other
     */
    public record NonQaConcernDto(
            String name,
            String description,
            String category
    ) {}
}
