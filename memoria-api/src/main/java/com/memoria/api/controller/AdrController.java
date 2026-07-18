package com.memoria.api.controller;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.dto.ArchitectureDecisionResponse;
import com.memoria.api.dto.CreateAdrRequest;
import com.memoria.api.dto.SupersedeAdrRequest;
import com.memoria.api.dto.UpdateAdrRequest;
import com.memoria.api.service.AdrService;
import com.memoria.api.service.ResponseMapper;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects/{projectId}/adrs")
@RequiredArgsConstructor
public class AdrController {

    private final AdrService adrService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ArchitectureDecisionResponse createAdr(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateAdrRequest request) {
        return ResponseMapper.toArchitectureDecisionResponse(adrService.createAdr(projectId, request));
    }

    @GetMapping
    public List<ArchitectureDecisionResponse> listAdrs(
            @PathVariable UUID projectId,
            @RequestParam(required = false) AdrStatus status,
            @RequestParam(required = false) String q) {
        return adrService.searchAdrs(projectId, status, q).stream()
                .map(ResponseMapper::toArchitectureDecisionResponse)
                .toList();
    }

    @PutMapping("/{adrId}")
    public ArchitectureDecisionResponse updateAdr(
            @PathVariable UUID projectId,
            @PathVariable UUID adrId,
            @RequestBody UpdateAdrRequest request) {
        return ResponseMapper.toArchitectureDecisionResponse(adrService.updateAdr(projectId, adrId, request));
    }

    @PostMapping("/{adrId}/supersede")
    public ArchitectureDecisionResponse supersedeAdr(
            @PathVariable UUID projectId,
            @PathVariable UUID adrId,
            @Valid @RequestBody SupersedeAdrRequest request) {
        return ResponseMapper.toArchitectureDecisionResponse(
                adrService.supersedeAdr(projectId, adrId, request.newAdrId()));
    }
}
