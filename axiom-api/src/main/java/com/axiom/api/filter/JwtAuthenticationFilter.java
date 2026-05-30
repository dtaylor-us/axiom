package com.axiom.api.filter;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.ReactiveSecurityContextHolder;
import org.springframework.security.web.server.WebFilterExchange;
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
    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private final ObjectMapper objectMapper;
    private final byte[] jwtSecret;

    public JwtAuthenticationFilter(
            ObjectMapper objectMapper,
            @Value("${jwt.secret}") String jwtSecret) {
        this.objectMapper = objectMapper;
        this.jwtSecret = jwtSecret.getBytes(StandardCharsets.UTF_8);
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

        return chain.filter(enrichedExchange)
                .contextWrite(ReactiveSecurityContextHolder.withAuthentication(authentication));
    }

    private boolean isPublicEndpoint(ServerHttpRequest request) {
        String path = request.getPath().value();
        HttpMethod method = request.getMethod();

        if ("/actuator/health".equals(path) && HttpMethod.GET.equals(method)) {
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
            String[] tokenParts = token.split("\\.");
            if (tokenParts.length != 3) {
                return null;
            }

            String signingInput = tokenParts[0] + "." + tokenParts[1];
            byte[] expectedSignature = hmacSha256(signingInput.getBytes(StandardCharsets.UTF_8), jwtSecret);
            byte[] tokenSignature = Base64.getUrlDecoder().decode(tokenParts[2]);
            if (!MessageDigest.isEqual(expectedSignature, tokenSignature)) {
                return null;
            }

            byte[] payloadBytes = Base64.getUrlDecoder().decode(tokenParts[1]);
            Map<String, Object> payload = objectMapper.readValue(payloadBytes, new TypeReference<>() { });

            String userId = asString(payload.get("sub"));
            String email = asString(payload.get("email"));
            Long expiration = asLong(payload.get("exp"));

            if (userId == null || userId.isBlank()) {
                return null;
            }
            if (expiration == null || expiration <= Instant.now().getEpochSecond()) {
                return null;
            }

            String resolvedEmail = email == null || email.isBlank() ? userId : email;
            return new JwtPrincipal(userId, resolvedEmail);
        } catch (Exception ex) {
            return null;
        }
    }

    private static byte[] hmacSha256(byte[] content, byte[] key)
            throws NoSuchAlgorithmException, InvalidKeyException {
        Mac mac = Mac.getInstance(HMAC_ALGORITHM);
        mac.init(new SecretKeySpec(key, HMAC_ALGORITHM));
        return mac.doFinal(content);
    }

    private static String asString(Object value) {
        return value instanceof String stringValue ? stringValue : null;
    }

    private static Long asLong(Object value) {
        if (value instanceof Number numberValue) {
            return numberValue.longValue();
        }
        return null;
    }

    private record JwtPrincipal(String userId, String email) {
    }
}
