package com.memoria.api.security;

import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class JwtAuthFilterTest {

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void doFilterInternal_usesLocalDev_whenBearerTokenIsInvalidAndGatewayBypassEnabled() throws Exception {
        JwtService jwtService = new JwtService("dev-jwt-secret-minimum-32-chars-here");
        JwtAuthFilter filter = new JwtAuthFilter(jwtService, new MockEnvironment()
                .withProperty("AXIOM_GATEWAY_BYPASS", "true"));
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer stale-or-invalid-token");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilterInternal(request, response, chain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication().getName()).isEqualTo("local-dev");
    }

    @Test
    void doFilterInternal_leavesRequestUnauthenticated_whenBearerTokenIsInvalidAndGatewayBypassDisabled()
            throws Exception {
        JwtService jwtService = new JwtService("dev-jwt-secret-minimum-32-chars-here");
        JwtAuthFilter filter = new JwtAuthFilter(jwtService, new MockEnvironment()
                .withProperty("AXIOM_GATEWAY_BYPASS", "false"));
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer stale-or-invalid-token");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilterInternal(request, response, chain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }
}
