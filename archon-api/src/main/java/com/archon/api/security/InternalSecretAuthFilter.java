package com.archon.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Security filter that grants read access to internal Axiom services using a
 * shared secret header, without requiring a user JWT.
 *
 * <p>This enables service-to-service calls from Memoria (and other pillars) to
 * read architecture output, session packages, and review reports without
 * impersonating a user. The filter runs before the gateway and JWT filters so
 * that authenticated internal requests bypass user-scoped auth entirely.</p>
 *
 * <p>The internal secret must be non-blank and match the value configured in
 * {@code AXIOM_INTERNAL_SECRET} / {@code axiom.gateway.internal-secret}.
 * If the secret is blank (not configured), this filter is a no-op — requests
 * still require normal user authentication.</p>
 *
 * <p>Requests authenticated by this filter are granted the ROLE_INTERNAL_SERVICE
 * authority and a synthetic principal of "internal-service". The principal is
 * not a real user and must never be used to scope user-owned resources.</p>
 */
@Component
@Slf4j
public class InternalSecretAuthFilter extends OncePerRequestFilter {

    private static final String INTERNAL_SECRET_HEADER = "X-Internal-Secret";
    private static final String INTERNAL_PRINCIPAL = "internal-service";

    private final String internalSecret;

    public InternalSecretAuthFilter(
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.internalSecret = internalSecret == null ? "" : internalSecret;
    }

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain) throws ServletException, IOException {

        if (!internalSecret.isBlank()) {
            String header = request.getHeader(INTERNAL_SECRET_HEADER);
            if (internalSecret.equals(header)
                    && SecurityContextHolder.getContext().getAuthentication() == null) {
                log.debug("InternalSecretAuthFilter: granting internal-service access uri={}",
                        request.getRequestURI());
                UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                        INTERNAL_PRINCIPAL,
                        null,
                        List.of(new SimpleGrantedAuthority("ROLE_INTERNAL_SERVICE")));
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }

        filterChain.doFilter(request, response);
    }
}
