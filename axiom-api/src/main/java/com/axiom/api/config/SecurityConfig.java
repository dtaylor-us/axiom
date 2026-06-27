package com.axiom.api.config;

import com.axiom.api.filter.JwtAuthenticationFilter;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.SecurityWebFiltersOrder;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.authentication.HttpStatusServerEntryPoint;

/**
 * JWT authentication at the gateway level.
 *
 * axiom-api is the only service that validates JWT tokens from external clients.
 * After validation, the user identity is forwarded to pillar services via
 * X-Axiom-User-Id and X-Axiom-Email headers. Pillar services trust these headers
 * without re-validating the JWT.
 *
 * Public endpoints (no authentication required):
 *   /api/v1/auth/**
 *   GET /actuator/health
 *   GET /actuator/health/**
 *   GET /actuator/info
 *
 * All other paths require a valid Bearer token.
 */
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    /**
     * Configures reactive security and plugs in gateway JWT validation.
     *
     * @param http reactive HTTP security builder
     * @param jwtAuthenticationFilter JWT validation filter for protected routes
     * @return configured security filter chain
     */
    @Bean
    public SecurityWebFilterChain securityWebFilterChain(
            ServerHttpSecurity http,
            JwtAuthenticationFilter jwtAuthenticationFilter) {
        return http
                .csrf(ServerHttpSecurity.CsrfSpec::disable)
                .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
                .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
                .logout(ServerHttpSecurity.LogoutSpec::disable)
                .exceptionHandling(spec -> spec.authenticationEntryPoint(
                        new HttpStatusServerEntryPoint(HttpStatus.UNAUTHORIZED)))
                .authorizeExchange(spec -> spec
                        .pathMatchers("/api/v1/auth/**").permitAll()
                        .pathMatchers("/api/v1/lens/**").authenticated()
                        .pathMatchers("/actuator/health", "/actuator/health/**", "/actuator/info").permitAll()
                        .anyExchange().authenticated())
                .addFilterAt(jwtAuthenticationFilter, SecurityWebFiltersOrder.AUTHENTICATION)
                .build();
    }
}
