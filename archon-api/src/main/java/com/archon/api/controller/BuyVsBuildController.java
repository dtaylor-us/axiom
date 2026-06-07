package com.archon.api.controller;

import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.dto.BuyVsBuildDecisionDto;
import com.archon.api.dto.BuyVsBuildSummaryDto;
import com.archon.api.service.BuyVsBuildService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

/**
 * REST endpoints for stage 6b buy-vs-build sourcing decisions.
 */
@RestController
@RequestMapping("/api/v1/sessions/{conversationId}/build-analysis")
@RequiredArgsConstructor
public class BuyVsBuildController {

    private final BuyVsBuildService buyVsBuildService;
    private final ConversationRepository conversationRepository;

    @GetMapping
    public ResponseEntity<BuyVsBuildSummaryDto> getSummary(
            @PathVariable UUID conversationId,
            @RequestParam(required = false) String recommendation,
            @AuthenticationPrincipal String userId
    ) {
        // Ownership validation: return 404 for non-existent or non-owned conversations.
        conversationRepository.findByIdAndUserId(conversationId, userId)
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND, "Conversation not found"));

        BuyVsBuildSummaryDto summary = buyVsBuildService.getSummary(conversationId);
        if (recommendation == null || recommendation.isBlank()) {
            return ResponseEntity.ok(summary);
        }

        List<BuyVsBuildDecisionDto> filtered = buyVsBuildService.getByRecommendation(
                conversationId, recommendation
        );

        int buildCount = (int) filtered.stream().filter(d -> "build".equals(d.getRecommendation())).count();
        int buyCount = (int) filtered.stream().filter(d -> "buy".equals(d.getRecommendation())).count();
        int adoptCount = (int) filtered.stream().filter(d -> "adopt".equals(d.getRecommendation())).count();
        int conflictCount = (int) filtered.stream().filter(BuyVsBuildDecisionDto::isConflictsWithUserPreference).count();

        return ResponseEntity.ok(new BuyVsBuildSummaryDto(
                summary.summaryText(),
                filtered.size(),
                buildCount,
                buyCount,
                adoptCount,
                conflictCount,
                filtered
        ));
    }

    @GetMapping("/conflicts")
    public ResponseEntity<List<BuyVsBuildDecisionDto>> getConflicts(
            @PathVariable UUID conversationId,
            @AuthenticationPrincipal String userId
    ) {
        conversationRepository.findByIdAndUserId(conversationId, userId)
                .orElseThrow(() -> new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.NOT_FOUND, "Conversation not found"));

        List<BuyVsBuildDecisionDto> all = buyVsBuildService.getDecisions(conversationId);
        List<BuyVsBuildDecisionDto> conflicts = all.stream()
                .filter(BuyVsBuildDecisionDto::isConflictsWithUserPreference)
                .toList();
        return ResponseEntity.ok(conflicts);
    }
}

