package com.archon.api.controller;

import com.archon.api.dto.UsageSummaryDto;
import com.archon.api.service.UsageService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

/**
 * REST controller for querying LLM token usage per conversation.
 */
@RestController
@RequestMapping("/api/v1/conversations/{conversationId}/usage")
@RequiredArgsConstructor
public class UsageController {

    private final UsageService usageService;

    @GetMapping
    public ResponseEntity<UsageSummaryDto> getUsage(
            @PathVariable UUID conversationId) {
        UsageSummaryDto summary = usageService.getSummary(conversationId);
        return ResponseEntity.ok(summary);
    }
}
