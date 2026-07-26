package com.memoria.api.security;

import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

class GatewayHeaderAuthFilterTest {

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void doFilterInternal_authenticatesWithoutSecret_whenGatewayBypassEnabled() throws Exception {
        MockEnvironment environment = new MockEnvironment().withProperty("AXIOM_GATEWAY_BYPASS", "true");
        GatewayHeaderAuthFilter filter = new GatewayHeaderAuthFilter("dev-secret", environment);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Axiom-User-Id", "local-dev");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilterInternal(request, response, chain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication().getName()).isEqualTo("local-dev");
        assertThat(response.getStatus()).isEqualTo(200);
    }

    @Test
    void doFilterInternal_rejectsMissingSecret_whenGatewayBypassDisabled() throws Exception {
        MockEnvironment environment = new MockEnvironment().withProperty("AXIOM_GATEWAY_BYPASS", "false");
        GatewayHeaderAuthFilter filter = new GatewayHeaderAuthFilter("dev-secret", environment);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Axiom-User-Id", "local-dev");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilterInternal(request, response, chain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        assertThat(response.getStatus()).isEqualTo(401);
    }
}