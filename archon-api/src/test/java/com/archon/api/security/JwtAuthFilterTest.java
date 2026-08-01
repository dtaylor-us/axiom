package com.archon.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.never;

/**
 * Unit tests for JwtAuthFilter.
 *
 * <p>Verifies that the filter correctly extracts Bearer tokens from the Authorization
 * header, delegates subject extraction to JwtService, and populates the
 * SecurityContext only when a valid subject is returned.</p>
 */
@ExtendWith(MockitoExtension.class)
class JwtAuthFilterTest {

    @Mock
    private JwtService jwtService;

    @InjectMocks
    private JwtAuthFilter filter;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void doFilterInternal_setsAuthenticationWhenValidBearerToken() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer test-token-value");
        when(jwtService.extractSubject("test-token-value")).thenReturn("user-123");

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication().getPrincipal())
                .isEqualTo("user-123");
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void doFilterInternal_skipsAuthWhenAuthorizationHeaderIsAbsent() throws Exception {
        when(request.getHeader("Authorization")).thenReturn(null);

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(filterChain).doFilter(request, response);
        verify(jwtService, never()).extractSubject(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void doFilterInternal_skipsAuthWhenHeaderIsNotBearer() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Basic dXNlcjpwYXNz");

        filter.doFilterInternal(request, response, filterChain);

        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(filterChain).doFilter(request, response);
        verify(jwtService, never()).extractSubject(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void doFilterInternal_skipsAuthWhenSubjectIsNull() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer expired-or-invalid");
        when(jwtService.extractSubject("expired-or-invalid")).thenReturn(null);

        filter.doFilterInternal(request, response, filterChain);

        // Null subject must not create an authentication entry in the SecurityContext
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void doFilterInternal_alwaysCallsFilterChainRegardlessOfToken() throws Exception {
        when(request.getHeader("Authorization")).thenReturn(null);

        filter.doFilterInternal(request, response, filterChain);

        // The filter must always forward the request, even without a token
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void doFilterInternal_extractsTokenWithoutBearerPrefix() throws Exception {
        // Verifies that exactly the substring after "Bearer " is passed to JwtService
        when(request.getHeader("Authorization")).thenReturn("Bearer precise.token.value");
        when(jwtService.extractSubject("precise.token.value")).thenReturn("subject-abc");

        filter.doFilterInternal(request, response, filterChain);

        verify(jwtService).extractSubject("precise.token.value");
    }
}
