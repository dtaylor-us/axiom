package com.lens.api.config;

import com.lens.api.security.GatewayHeaderAuthFilter;
import com.lens.api.security.JwtAuthFilter;
import jakarta.servlet.DispatcherType;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Authentication configuration for lens-api.
 *
 * <p>AXIOM_GATEWAY_BYPASS=false (production default):
 * Expects X-Axiom-User-Id header forwarded by axiom-api.
 * Rejects protected requests without this header with 401.
 *
 * <p>AXIOM_GATEWAY_BYPASS=true (local development):
 * Falls back to direct JWT validation.
 * Never enable in production.
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;
    private final GatewayHeaderAuthFilter gatewayHeaderAuthFilter;

    @Value("${axiom.gateway.bypass:false}")
    private boolean gatewayBypass;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
                        .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                        .requestMatchers("/api/v1/**").authenticated()
                        .anyRequest().permitAll())
                .exceptionHandling(e -> e.authenticationEntryPoint(
                        new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
                .addFilterBefore(
                        gatewayBypass ? jwtAuthFilter : gatewayHeaderAuthFilter,
                        UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
