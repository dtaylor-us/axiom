package com.axiom.api.filter;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;

import javax.crypto.SecretKey;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;

import reactor.core.publisher.Mono;

/**
 * Validates Bearer tokens and enriches downstream requests with trusted user context.
 */
@Component
public class JwtAuthenticationFilter implements WebFilter {

    public static final String AXIOM_USER_ID_HEADER = "X-Axiom-User-Id";
    public static final String AXIOM_EMAIL_HEADER = "X-Axiom-Email";

    static final String USER_ID_ATTRIBUTE = "axiom.userId";
    static final String EMAIL_ATTRIBUTE = "axiom.email";

    private static final String BEARER_PREFIX = "Bearer ";
    private static final String USER_ID_CLAIM = "userId";
    private static final String EMAIL_CLAIM = "email";

    private final SecretKey signingKey;

    public JwtAuthenticationFilter(
            @Value("${jwt.secret}") String jwtSecret) {
        this.signingKey = Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Authenticates protected routes while bypassing known public endpoints.
     *
     * @param exchange current HTTP exchange
     * @param chain remaining web filter chain
     * @return completion signal
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        if (isPublicEndpoint(exchange.getRequest())) {
            return chain.filter(exchange);
        }

        String authorization = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authorization == null || !authorization.startsWith(BEARER_PREFIX)) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = authorization.substring(BEARER_PREFIX.length());
        JwtPrincipal principal = parseAndValidateToken(token);
        if (principal == null) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        ServerHttpRequest enrichedRequest = exchange.getRequest().mutate()
                .header(AXIOM_USER_ID_HEADER, principal.userId())
                .header(AXIOM_EMAIL_HEADER, principal.email())
                .build();

        ServerWebExchange enrichedExchange = exchange.mutate().request(enrichedRequest).build();
        enrichedExchange.getAttributes().put(USER_ID_ATTRIBUTE, principal.userId());
        enrichedExchange.getAttributes().put(EMAIL_ATTRIBUTE, principal.email());

        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                principal.userId(), token, List.of(new SimpleGrantedAuthority("ROLE_USER")));
        authentication.setDetails(principal.email());

        return chain.filter(enrichedExchange)
                .contextWrite(ReactiveSecurityContextHolder.withAuthentication(authentication));
    }

    private boolean isPublicEndpoint(ServerHttpRequest request) {
        String path = request.getPath().value();
        HttpMethod method = request.getMethod();

        if (path.startsWith("/actuator/health") && HttpMethod.GET.equals(method)) {
            return true;
        }
        if ("/actuator/info".equals(path) && HttpMethod.GET.equals(method)) {
            return true;
        }
        if ("/api/v1/auth/login".equals(path) && HttpMethod.POST.equals(method)) {
            return true;
        }
        if ("/api/v1/auth/register".equals(path) && HttpMethod.POST.equals(method)) {
            return true;
        }
        if ("/api/v1/auth/forgot-password".equals(path) && HttpMethod.POST.equals(method)) {
            return true;
        }
        return "/api/v1/auth/reset-password".equals(path) && HttpMethod.POST.equals(method);
    }

    private JwtPrincipal parseAndValidateToken(String token) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            String subject = claims.getSubject();
            if (subject == null || subject.isBlank()) {
                return null;
            }

            String userId = claims.get(USER_ID_CLAIM, String.class);
            String email = claims.get(EMAIL_CLAIM, String.class);
            Instant expiration = claims.getExpiration() == null
                    ? null
                    : claims.getExpiration().toInstant();

            if (expiration == null || expiration.isBefore(Instant.now())) {
                return null;
            }

            String resolvedUserId = userId == null || userId.isBlank() ? subject : userId;
            String resolvedEmail = email == null || email.isBlank() ? userId : email;
            return new JwtPrincipal(resolvedUserId, resolvedEmail == null || resolvedEmail.isBlank() ? subject : resolvedEmail);
        } catch (JwtException | IllegalArgumentException ex) {
            return null;
        }
    }

    private record JwtPrincipal(String userId, String email) {
    }
}
