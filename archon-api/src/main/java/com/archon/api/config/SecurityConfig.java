package com.archon.api.config;

import com.archon.api.security.GatewayHeaderAuthFilter;
import com.archon.api.security.InternalSecretAuthFilter;
import com.archon.api.security.JwtAuthFilter;
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
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Authentication configuration for archon-api.
 *
 * <p>Three auth paths in priority order:</p>
 *
 * <ol>
 *   <li><b>Internal service secret</b> — requests carrying X-Internal-Secret matching
 *       {@code axiom.gateway.internal-secret} are granted ROLE_INTERNAL_SERVICE and bypass
 *       user auth entirely. Used by Memoria (and other pillars) for service-to-service reads
 *       of architecture output, session packages, etc. without a user JWT.</li>
 *   <li><b>Gateway header</b> (BYPASS=false, production default) — expects X-Axiom-User-Id
 *       forwarded by axiom-api. Rejects protected requests without this header with 401.
 *       JWT is NOT validated here — axiom-api already did it.</li>
 *   <li><b>Direct JWT</b> (BYPASS=true, local development) — falls back to JWT validation.
 *       Allows testing archon-api without axiom-api running. Never enable in production.</li>
 * </ol>
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;
    private final GatewayHeaderAuthFilter gatewayHeaderAuthFilter;
    private final InternalSecretAuthFilter internalSecretAuthFilter;

    @Value("${axiom.gateway.bypass:false}")
    private boolean gatewayBypass;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Allow async dispatches (SseEmitter completion) without re-auth
                .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
                .requestMatchers(
                        "/api/v1/auth/forgot-password",
                        "/api/v1/auth/reset-password",
                        "/api/v1/auth/reset-password/validate"
                ).permitAll()
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                .requestMatchers("/health").permitAll()
                .requestMatchers("/api/v1/**").authenticated()
                .anyRequest().permitAll())
            .exceptionHandling(e -> e
                .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
            // InternalSecretAuthFilter runs first — internal service calls bypass user auth
            .addFilterBefore(
                    internalSecretAuthFilter,
                    UsernamePasswordAuthenticationFilter.class)
            // Then user auth — gateway header in production, JWT in local bypass mode
            .addFilterAfter(
                    gatewayBypass ? jwtAuthFilter : gatewayHeaderAuthFilter,
                    InternalSecretAuthFilter.class);
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
