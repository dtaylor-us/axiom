package com.memoria.api.controller;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.dto.ArchitectureDecisionResponse;
import com.memoria.api.dto.CreateAdrRequest;
import com.memoria.api.dto.SupersedeAdrRequest;
import com.memoria.api.dto.UpdateAdrRequest;
import com.memoria.api.service.AdrService;
import com.memoria.api.service.AuthenticationUserResolver;
import com.memoria.api.service.ProjectService;
import com.memoria.api.service.ResponseMapper;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects/{projectId}/adrs")
@RequiredArgsConstructor
public class AdrController {

    private final AdrService adrService;
    private final ProjectService projectService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ArchitectureDecisionResponse createAdr(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateAdrRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return ResponseMapper.toArchitectureDecisionResponse(adrService.createAdr(projectId, request));
    }

    @GetMapping
    public List<ArchitectureDecisionResponse> listAdrs(
            @PathVariable UUID projectId,
            @RequestParam(required = false) AdrStatus status,
            @RequestParam(required = false) String q,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return adrService.searchAdrs(projectId, status, q).stream()
                .map(ResponseMapper::toArchitectureDecisionResponse)
                .toList();
    }

    @PutMapping("/{adrId}")
    public ArchitectureDecisionResponse updateAdr(
            @PathVariable UUID projectId,
            @PathVariable UUID adrId,
            @RequestBody UpdateAdrRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return ResponseMapper.toArchitectureDecisionResponse(adrService.updateAdr(projectId, adrId, request));
    }

    @PostMapping("/{adrId}/supersede")
    public ArchitectureDecisionResponse supersedeAdr(
            @PathVariable UUID projectId,
            @PathVariable UUID adrId,
            @Valid @RequestBody SupersedeAdrRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return ResponseMapper.toArchitectureDecisionResponse(
                adrService.supersedeAdr(projectId, adrId, request.newAdrId()));
    }

    private void validateProjectAccess(UUID projectId, String userIdHeader, Authentication authentication) {
        projectService.getProject(projectId, resolveUser(userIdHeader, authentication));
    }

    private UUID resolveUser(String userIdHeader, Authentication authentication) {
        if (userIdHeader != null && !userIdHeader.isBlank()) {
            try {
                return UUID.fromString(userIdHeader);
            } catch (IllegalArgumentException e) {
                return UUID.nameUUIDFromBytes(userIdHeader.getBytes(StandardCharsets.UTF_8));
            }
        }
        return userResolver.resolveUserId(authentication);
    }
}
