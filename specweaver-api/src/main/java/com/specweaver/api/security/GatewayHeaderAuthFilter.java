package com.specweaver.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Trusts axiom-api user identity headers when gateway bypass is disabled.
 */
@Component
public class GatewayHeaderAuthFilter extends OncePerRequestFilter {

    static final String AXIOM_USER_ID_HEADER = "X-Axiom-User-Id";
    static final String AXIOM_INTERNAL_SECRET_HEADER = "X-Axiom-Internal-Secret";

    private final String internalSecret;

    public GatewayHeaderAuthFilter(
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.internalSecret = internalSecret;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        String userId = request.getHeader(AXIOM_USER_ID_HEADER);
        if (userId == null || userId.isBlank()) {
            filterChain.doFilter(request, response);
            return;
        }
        if (isInternalSecretRequired() && !hasMatchingInternalSecret(request)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        var auth = new UsernamePasswordAuthenticationToken(userId, null, List.of());
        SecurityContextHolder.getContext().setAuthentication(auth);
        filterChain.doFilter(request, response);
    }

    private boolean isInternalSecretRequired() {
        return internalSecret != null && !internalSecret.isBlank();
    }

    private boolean hasMatchingInternalSecret(HttpServletRequest request) {
        return internalSecret.equals(request.getHeader(AXIOM_INTERNAL_SECRET_HEADER));
    }
}
