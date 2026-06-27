package com.lens.api.controller;

import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.domain.model.EvidenceType;
import com.lens.api.service.EvidenceIngestionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
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
@RequestMapping("/api/v1/lens/sessions/{sessionId}/evidence")
public class EvidenceController {

    private final EvidenceIngestionService evidenceIngestionService = new EvidenceIngestionService();

    public record SubmitEvidenceRequest(@NotNull EvidenceType evidenceType, @NotBlank String content, String sourceLabel) {}

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ArchitectureEvidence submitEvidence(@PathVariable UUID sessionId, @Valid @RequestBody SubmitEvidenceRequest request) {
        return evidenceIngestionService.submitEvidence(sessionId, request.evidenceType(), request.content(), request.sourceLabel());
    }

    @GetMapping
    public List<ArchitectureEvidence> listEvidence(@PathVariable UUID sessionId) {
        return evidenceIngestionService.listEvidence(sessionId);
    }

    @DeleteMapping("/{evidenceId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteEvidence(@PathVariable UUID sessionId, @PathVariable UUID evidenceId) {
        evidenceIngestionService.deleteEvidence(sessionId, evidenceId);
    }
}
