package com.aiarchitect.api.config;

import com.aiarchitect.api.security.JwtAuthFilter;
import jakarta.servlet.DispatcherType;
import lombok.RequiredArgsConstructor;
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
 * Security configuration for the application.
 * Configures authentication, authorization, and JWT-based security.
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    /**
     * Configures the security filter chain for HTTP requests.
     * Sets up stateless session management, authorization rules, and JWT filtering.
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
            // Use stateless sessions for JWT-based authentication
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Allow async dispatches (SseEmitter completion) without re-auth
                .dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()
                // Public authentication endpoints
                .requestMatchers("/api/v1/auth/**").permitAll()
                // Public actuator and health endpoints
                .requestMatchers("/actuator/**").permitAll()
                .requestMatchers("/health").permitAll()
                // All other API v1 endpoints require authentication
                .requestMatchers("/api/v1/**").authenticated()
                // Allow all other requests
                .anyRequest().permitAll())
            // Handle authentication failures with 401 Unauthorized
            .exceptionHandling(e -> e
                .authenticationEntryPoint(
                        new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
            // Add JWT filter before username/password authentication filter
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /**
     * Creates a BCrypt password encoder bean for password hashing.
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
