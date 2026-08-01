package com.memoria.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
public class GatewayHeaderAuthFilter extends OncePerRequestFilter {

    static final String AXIOM_USER_ID_HEADER = "X-Axiom-User-Id";
    static final String AXIOM_INTERNAL_SECRET_HEADER = "X-Axiom-Internal-Secret";

    private final String internalSecret;
    private final Environment environment;

    public GatewayHeaderAuthFilter(
            @Value("${axiom.gateway.internal-secret:}") String internalSecret,
            Environment environment) {
        this.internalSecret = internalSecret;
        this.environment = environment;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        String userId = request.getHeader(AXIOM_USER_ID_HEADER);
        if (GatewayBypassMode.isEnabled(environment)) {
            setAuthentication(userId == null || userId.isBlank() ? "local-dev" : userId);
            filterChain.doFilter(request, response);
            return;
        }
        if (userId == null || userId.isBlank()) {
            filterChain.doFilter(request, response);
            return;
        }
        if (isInternalSecretRequired() && !hasMatchingInternalSecret(request)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        setAuthentication(userId);
        filterChain.doFilter(request, response);
    }

    private void setAuthentication(String subject) {
        var auth = new UsernamePasswordAuthenticationToken(subject, null, List.of());
        SecurityContextHolder.getContext().setAuthentication(auth);
    }

    private boolean isInternalSecretRequired() {
        return internalSecret != null && !internalSecret.isBlank();
    }

    private boolean hasMatchingInternalSecret(HttpServletRequest request) {
        return internalSecret.equals(request.getHeader(AXIOM_INTERNAL_SECRET_HEADER));
    }
}
