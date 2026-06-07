package com.archon.api.controller;

import com.archon.api.dto.FmeaRiskDto;
import com.archon.api.dto.GovernanceReportDto;
import com.archon.api.service.GovernanceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
public class GovernanceController {

    private final GovernanceService governanceService;

    @GetMapping("/{id}/fmea-risks")
    public ResponseEntity<List<FmeaRiskDto>> getFmeaRisks(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {
        List<FmeaRiskDto> risks = governanceService.getFmeaRisks(id);
        return ResponseEntity.ok(risks);
    }

    @GetMapping("/{id}/governance")
    public ResponseEntity<GovernanceReportDto> getGovernanceReport(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {
        return governanceService.getGovernanceReport(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
