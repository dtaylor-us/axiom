package com.specweaver.api.controller;

import com.specweaver.api.config.GlobalExceptionHandler;
import com.specweaver.api.config.SecurityConfig;
import com.specweaver.api.domain.model.SessionStatus;
import com.specweaver.api.dto.response.SessionResponse;
import com.specweaver.api.exception.SessionNotFoundException;
import com.specweaver.api.security.GatewayHeaderAuthFilter;
import com.specweaver.api.security.JwtAuthFilter;
import com.specweaver.api.security.JwtService;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.SessionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(SessionController.class)
@Import({SecurityConfig.class, GatewayHeaderAuthFilter.class, JwtAuthFilter.class, JwtService.class,
        GlobalExceptionHandler.class, AuthenticationUserResolver.class})
@TestPropertySource(properties = {
        "axiom.gateway.bypass=false",
        "security.jwt.secret=super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes"
})
class SessionControllerTest {

    @Autowired private MockMvc mockMvc;
    @MockBean private SessionService sessionService;

    @Test
    void postSessions_returnsCreatedWithSessionResponse() throws Exception {
        UUID userId = UUID.randomUUID();
        when(sessionService.createSession(any(), any())).thenReturn(session(userId));

        mockMvc.perform(post("/api/v1/sessions")
                        .header("X-Axiom-User-Id", userId.toString())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"System\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("System"));
    }

    @Test
    void postSessions_withoutAuthReturnsUnauthorized() throws Exception {
        mockMvc.perform(post("/api/v1/sessions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"System\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void getSessions_returnsUserSessionsOnly() throws Exception {
        UUID userId = UUID.randomUUID();
        when(sessionService.listSessions(any())).thenReturn(List.of(session(userId)));

        mockMvc.perform(get("/api/v1/sessions")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void getSession_returnsOwnSession() throws Exception {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        when(sessionService.getSession(any(), any())).thenReturn(session(sessionId, userId));

        mockMvc.perform(get("/api/v1/sessions/{sessionId}", sessionId)
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(sessionId.toString()));
    }

    @Test
    void getSession_returnsForbiddenForAnotherUsersSession() throws Exception {
        UUID userId = UUID.randomUUID();
        when(sessionService.getSession(any(), any())).thenThrow(new AccessDeniedException("wrong user"));

        mockMvc.perform(get("/api/v1/sessions/{sessionId}", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isForbidden());
    }

    @Test
    void getSession_returnsNotFoundForUnknownSession() throws Exception {
        UUID userId = UUID.randomUUID();
        when(sessionService.getSession(any(), any())).thenThrow(new SessionNotFoundException("Session not found"));

        mockMvc.perform(get("/api/v1/sessions/{sessionId}", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isNotFound());
    }

    @Test
    void patchSession_updatesTitle() throws Exception {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        when(sessionService.updateSessionTitle(any(), any(), any())).thenReturn(session(sessionId, userId));

        mockMvc.perform(patch("/api/v1/sessions/{sessionId}", sessionId)
                        .header("X-Axiom-User-Id", userId.toString())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Updated title\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(sessionId.toString()));
    }

    @Test
    void patchSession_withoutAuthReturnsUnauthorized() throws Exception {
        mockMvc.perform(patch("/api/v1/sessions/{sessionId}", UUID.randomUUID())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Updated title\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void deleteSession_returnsNoContent() throws Exception {
        UUID userId = UUID.randomUUID();
        doNothing().when(sessionService).deleteSession(any(), any());

        mockMvc.perform(delete("/api/v1/sessions/{sessionId}", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isNoContent());
    }

    @Test
    void deleteSession_returnsForbiddenForAnotherUsersSession() throws Exception {
        UUID userId = UUID.randomUUID();
        doThrow(new AccessDeniedException("wrong user")).when(sessionService).deleteSession(any(), any());

        mockMvc.perform(delete("/api/v1/sessions/{sessionId}", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isForbidden());
    }

    private SessionResponse session(UUID userId) {
        return session(UUID.randomUUID(), userId);
    }

    private SessionResponse session(UUID sessionId, UUID userId) {
        return new SessionResponse(
                sessionId, userId, "System", SessionStatus.ACTIVE,
                Instant.now(), Instant.now(), null, List.of());
    }
}
