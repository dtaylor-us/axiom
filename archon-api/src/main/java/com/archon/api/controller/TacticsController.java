package com.archon.api.controller;

import com.archon.api.dto.TacticDto;
import com.archon.api.dto.TacticsSummaryDto;
import com.archon.api.service.TacticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

/**
 * REST endpoints for architecture tactic recommendations.
 *
 * <p>Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 */
@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
public class TacticsController {

    private final TacticsService tacticsService;

    /**
     * Return all tactic recommendations for a session, with optional filters.
     *
     * <p>Query parameters are mutually exclusive; if more than one is provided
     * the precedence order is: {@code characteristic} &gt; {@code priority} &gt;
     * {@code newOnly}.
     *
     * @param id             session / conversation UUID
     * @param characteristic optional quality-attribute filter (e.g. "availability")
     * @param priority       optional priority filter: critical | recommended | optional
     * @param newOnly        when {@code true} exclude already-addressed tactics
     */
    @GetMapping("/{id}/tactics")
    public ResponseEntity<List<TacticDto>> getTactics(
            @PathVariable UUID id,
            @RequestParam(required = false) String characteristic,
            @RequestParam(required = false) String priority,
            @RequestParam(defaultValue = "false") boolean newOnly,
            @AuthenticationPrincipal String userId) {

        List<TacticDto> tactics = tacticsService.getTactics(id, characteristic, priority, newOnly);
        return ResponseEntity.ok(tactics);
    }

    /**
     * Return aggregate summary counts for a session's tactics.
     *
     * @param id session / conversation UUID
     */
    @GetMapping("/{id}/tactics/summary")
    public ResponseEntity<TacticsSummaryDto> getTacticsSummary(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        TacticsSummaryDto summary = tacticsService.getTacticsSummary(id);
        return ResponseEntity.ok(summary);
    }
}
