package com.axiom.api.config;

import com.axiom.api.filter.JwtAuthenticationFilter;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.SecurityWebFiltersOrder;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.authentication.HttpStatusServerEntryPoint;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

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

    private static final List<String> ALLOWED_METHODS = List.of(
            HttpMethod.GET.name(),
            HttpMethod.POST.name(),
            HttpMethod.PUT.name(),
            HttpMethod.PATCH.name(),
            HttpMethod.DELETE.name(),
            HttpMethod.OPTIONS.name());

    private static final List<String> ALLOWED_HEADERS = List.of("*");
    private static final List<String> EXPOSED_HEADERS = List.of("Authorization");

    private final List<String> allowedOrigins;

    public SecurityConfig(
            @Value("${axiom.cors.allowed-origins:http://localhost:3000,https://axiom-dev.eastus2.cloudapp.azure.com}")
            String allowedOriginsCsv) {
        this.allowedOrigins = Arrays.stream(allowedOriginsCsv.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isBlank())
                .collect(Collectors.toList());
    }

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
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .csrf(ServerHttpSecurity.CsrfSpec::disable)
                .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
                .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
                .logout(ServerHttpSecurity.LogoutSpec::disable)
                .exceptionHandling(spec -> spec.authenticationEntryPoint(
                        new HttpStatusServerEntryPoint(HttpStatus.UNAUTHORIZED)))
                .authorizeExchange(spec -> spec
                        .pathMatchers("/api/v1/auth/**").permitAll()
                        .pathMatchers("/actuator/health", "/actuator/health/**", "/actuator/info").permitAll()
                        .anyExchange().authenticated())
                .addFilterAt(jwtAuthenticationFilter, SecurityWebFiltersOrder.AUTHENTICATION)
                .build();
    }

        /**
         * Configures CORS for browser requests routed through the public gateway.
         *
         * @return CORS configuration source scoped to all routes
         */
        @Bean
        public CorsConfigurationSource corsConfigurationSource() {
                CorsConfiguration configuration = new CorsConfiguration();
                configuration.setAllowedOrigins(allowedOrigins);
                configuration.setAllowedMethods(ALLOWED_METHODS);
                configuration.setAllowedHeaders(ALLOWED_HEADERS);
                configuration.setExposedHeaders(EXPOSED_HEADERS);
                configuration.setAllowCredentials(true);

                UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
                source.registerCorsConfiguration("/**", configuration);
                return source;
        }
}
