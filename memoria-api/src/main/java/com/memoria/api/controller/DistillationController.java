package com.memoria.api.controller;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.dto.DistillSessionRequest;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.service.DistillationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria")
@RequiredArgsConstructor
public class DistillationController {

    private final DistillationService distillationService;

    @PostMapping("/distill-session")
    @ResponseStatus(HttpStatus.CREATED)
    public DistillSessionResponse distillSession(@Valid @RequestBody DistillSessionRequest request) {
        return distillationService.distillLinkedSession(request);
    }

    @PostMapping("/sessions/{pillar}/{sessionId}/distill")
    @ResponseStatus(HttpStatus.CREATED)
    public DistillSessionResponse distillLinkedSession(
            @PathVariable Pillar pillar,
            @PathVariable UUID sessionId,
            @RequestBody DistillSessionRequest request) {
        DistillSessionRequest normalized = new DistillSessionRequest(
                request.projectId(),
                pillar,
                sessionId,
                request.sessionSummary(),
                request.sessionPayload());
        return distillationService.distillLinkedSession(normalized);
    }
}
