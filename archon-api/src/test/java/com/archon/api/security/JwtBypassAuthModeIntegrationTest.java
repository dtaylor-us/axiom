package com.archon.api.security;

import com.archon.api.config.SecurityConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpHeaders;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Verifies direct JWT authentication behavior when bypass=true.
 */
@WebMvcTest(controllers = TestProtectedController.class,
        properties = {
                "axiom.gateway.bypass=true",
                "security.jwt.secret=super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes"
        })
@Import({SecurityConfig.class, JwtAuthFilter.class, JwtService.class, GatewayHeaderAuthFilter.class})
class JwtBypassAuthModeIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @Test
    void bypassTrue_validJwt_authenticatesRequest() throws Exception {
        String token = jwtService.generateToken("jwt-user");

        mockMvc.perform(get("/api/v1/protected/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(content().string("jwt-user"));
    }

    @Test
    void bypassTrue_invalidJwt_returnsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/protected/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer invalid.token.value"))
                .andExpect(status().isUnauthorized());
    }

}
