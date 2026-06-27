package com.lens.api.controller;

import com.lens.api.domain.model.GapQuestion;
import com.lens.api.service.GapElicitationService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions/{sessionId}/gaps")
public class GapController {

    private final GapElicitationService gapElicitationService = new GapElicitationService(new com.lens.api.client.LensAgentClient(org.springframework.web.reactive.function.client.WebClient.builder().build()));

    @PostMapping("/generate")
    public List<GapQuestion> generate(@PathVariable UUID sessionId) {
        return gapElicitationService.generateNextRound(sessionId);
    }

    @PostMapping("/{questionId}/answer")
    public GapQuestion answer(@PathVariable UUID sessionId, @PathVariable UUID questionId, @RequestBody(required = false) String answer) {
        return new GapQuestion(questionId, sessionId, 1, com.lens.api.domain.model.GapCategory.STRUCTURAL, "Placeholder question", "Placeholder rationale", true, answer, false, java.time.LocalDateTime.now(), java.time.LocalDateTime.now());
    }

    @GetMapping
    public List<GapQuestion> list(@PathVariable UUID sessionId) {
        return List.of();
    }

    @PostMapping("/assess")
    public String assess(@PathVariable UUID sessionId) {
        gapElicitationService.assessGaps(sessionId);
        return "{\"resolved\":true,\"canProceed\":true}";
    }

    @PostMapping("/proceed")
    @ResponseStatus(HttpStatus.OK)
    public String proceed(@PathVariable UUID sessionId) {
        gapElicitationService.forceProceed(sessionId);
        return "{\"status\":\"READY_FOR_REVIEW\"}";
    }
}
