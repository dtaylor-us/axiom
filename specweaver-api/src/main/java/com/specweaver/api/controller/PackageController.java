package com.specweaver.api.controller;

import com.specweaver.api.dto.response.GeneratePackageResponse;
import com.specweaver.api.dto.response.PackageResponse;
import com.specweaver.api.dto.response.SendToArchonResponse;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.PackageGenerationService;
import com.specweaver.api.service.PackageService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * REST endpoints for package generation and Archon handoff.
 *
 * @author OpenAI
 */
@RestController
@RequestMapping("/api/v1/sessions/{sessionId}/package")
@RequiredArgsConstructor
public class PackageController {

    private final PackageGenerationService packageGenerationService;
    private final PackageService packageService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping("/generate")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public GeneratePackageResponse generatePackage(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        PackageResponse response = packageGenerationService.generatePackage(
                sessionId, userResolver.resolveUserId(authentication));
        return new GeneratePackageResponse(response.packageId());
    }

    @GetMapping
    public PackageResponse getPackage(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        return packageGenerationService.getPackage(sessionId, userResolver.resolveUserId(authentication));
    }

    /**
     * Returns the formatted requirements brief for manual Archon submission.
     *
     * <p>The UI pre-populates the Archon chat input with this text so the user
     * can review it before starting the pipeline.</p>
     */
    @PostMapping("/send-to-archon")
    public ResponseEntity<SendToArchonResponse> sendToArchon(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        String briefText = packageService.getBriefText(
                sessionId,
                userResolver.resolveUserId(authentication));
        return ResponseEntity.ok(new SendToArchonResponse(briefText));
    }
}
