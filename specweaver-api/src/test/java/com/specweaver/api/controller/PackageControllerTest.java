package com.specweaver.api.controller;

import com.specweaver.api.config.GlobalExceptionHandler;
import com.specweaver.api.config.SecurityConfig;
import com.specweaver.api.dto.response.PackageResponse;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.security.GatewayHeaderAuthFilter;
import com.specweaver.api.security.JwtAuthFilter;
import com.specweaver.api.security.JwtService;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.PackageGenerationService;
import com.specweaver.api.service.PackageService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(PackageController.class)
@Import({SecurityConfig.class, GatewayHeaderAuthFilter.class, JwtAuthFilter.class, JwtService.class,
        GlobalExceptionHandler.class, AuthenticationUserResolver.class})
@TestPropertySource(properties = {
        "axiom.gateway.bypass=false",
        "security.jwt.secret=super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes"
})
class PackageControllerTest {

    @Autowired private MockMvc mockMvc;
    @MockBean private PackageGenerationService packageGenerationService;
        @MockBean private PackageService packageService;

    @Test
    void postGenerate_returnsAcceptedWhenExtractedDocsExist() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageGenerationService.generatePackage(any(), any())).thenReturn(packageResponse());

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/generate", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.packageId").exists());
    }

    @Test
    void postGenerate_returnsBadRequestWhenNoExtractedDocs() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageGenerationService.generatePackage(any(), any()))
                .thenThrow(new IllegalArgumentException("No extracted documents"));

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/generate", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isBadRequest());
    }

    @Test
    void postGenerate_returnsConflictWhenAlreadyProcessing() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageGenerationService.generatePackage(any(), any()))
                .thenThrow(new IllegalStateException("Package generation already in progress"));

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/generate", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isConflict());
    }

    @Test
    void getPackage_returnsOkWhenAvailable() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageGenerationService.getPackage(any(), any())).thenReturn(packageResponse());

        mockMvc.perform(get("/api/v1/sessions/{sessionId}/package", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.readinessScore").value(0.85))
                .andExpect(jsonPath("$.readinessLabel").value("Ready for architecture"))
                .andExpect(jsonPath("$.gapCount").value(1))
                .andExpect(jsonPath("$.conflictCount").value(1))
                .andExpect(jsonPath("$.gaps").isArray())
                .andExpect(jsonPath("$.conflicts").isArray());
    }

    @Test
    void getPackage_returnsNotFoundWhenNotGenerated() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageGenerationService.getPackage(any(), any()))
                .thenThrow(new PackageNotFoundException("Package not generated"));

        mockMvc.perform(get("/api/v1/sessions/{sessionId}/package", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isNotFound());
    }

    @Test
    void postSendToArchon_returnsOkWithBriefText() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageService.getBriefText(any(), any()))
                .thenReturn("## Requirements Package from SpecWeaver");

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/send-to-archon", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.briefText").value("## Requirements Package from SpecWeaver"));
    }

    @Test
    void postSendToArchon_returnsNotFoundWhenNoPackage() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageService.getBriefText(any(), any()))
                .thenThrow(new PackageNotFoundException("Package not generated"));

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/send-to-archon", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isNotFound());
    }

    @Test
    void postSendToArchon_isIdempotentWhenCalledTwice() throws Exception {
        UUID userId = UUID.randomUUID();
        when(packageService.getBriefText(any(), any()))
                .thenReturn("brief text");

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/send-to-archon", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.briefText").value("brief text"));

        mockMvc.perform(post("/api/v1/sessions/{sessionId}/package/send-to-archon", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.briefText").value("brief text"));
    }

    private PackageResponse packageResponse() {
        return new PackageResponse(
                UUID.randomUUID(),
                UUID.randomUUID(),
                Instant.now(),
                new BigDecimal("0.85"),
                "Ready for architecture",
                "Payments",
                List.of(),
                List.of(Map.of("area", "Latency", "severity", "high")),
                List.of(Map.of("description", "Conflicting datastore choices")),
                List.of(),
                1,
                1,
                0,
                0,
                1,
                1);
    }
}
