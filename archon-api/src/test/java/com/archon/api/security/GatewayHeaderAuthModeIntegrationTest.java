package com.archon.api.security;

import com.archon.api.config.SecurityConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Verifies gateway-header authentication mode behavior when bypass=false.
 */
@WebMvcTest(controllers = TestProtectedController.class,
        properties = {
                "axiom.gateway.bypass=false",
                "axiom.gateway.internal-secret=test-internal-secret",
                "security.jwt.secret=super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes"
        })
@Import({SecurityConfig.class, JwtAuthFilter.class, JwtService.class, GatewayHeaderAuthFilter.class})
class GatewayHeaderAuthModeIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void bypassFalse_withAxiomUserHeader_authenticatesRequest() throws Exception {
        mockMvc.perform(get("/api/v1/protected/me")
                        .header("X-Axiom-User-Id", "gateway-user")
                        .header("X-Axiom-Internal-Secret", "test-internal-secret"))
                .andExpect(status().isOk())
                .andExpect(content().string("gateway-user"));
    }

    @Test
    void bypassFalse_missingAxiomUserHeader_returnsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/protected/me")
                        .header("X-Axiom-Internal-Secret", "test-internal-secret"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void bypassFalse_internalSecretMismatch_returnsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/protected/me")
                        .header("X-Axiom-User-Id", "gateway-user")
                        .header("X-Axiom-Internal-Secret", "wrong-secret"))
                .andExpect(status().isUnauthorized());
    }

}
