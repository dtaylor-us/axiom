package com.memoria.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.core.env.Environment;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private static final int BEARER_PREFIX_LENGTH = 7;

    private final JwtService jwtService;
    private final Environment environment;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        if (isGatewayBypassEnabled()) {
            setAuthentication("local-dev");
            filterChain.doFilter(request, response);
            return;
        }
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String subject = jwtService.extractSubject(header.substring(BEARER_PREFIX_LENGTH));
            if (subject != null) {
                setAuthentication(subject);
            }
        }
        filterChain.doFilter(request, response);
    }

    private boolean isGatewayBypassEnabled() {
        return Boolean.parseBoolean(environment.getProperty(
                "AXIOM_GATEWAY_BYPASS",
                environment.getProperty("axiom.gateway.bypass", "false")));
    }

    private void setAuthentication(String subject) {
        var auth = new UsernamePasswordAuthenticationToken(subject, null, List.of());
        SecurityContextHolder.getContext().setAuthentication(auth);
    }
}
