package com.specweaver.api.config;

import com.specweaver.api.security.GatewayHeaderAuthFilter;
import com.specweaver.api.security.JwtAuthFilter;
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
 * Authentication configuration for specweaver-api.
 *
 * <p>AXIOM_GATEWAY_BYPASS=true validates JWTs directly for local development.
 * AXIOM_GATEWAY_BYPASS=false trusts identity headers from axiom-api.</p>
 *
 * @author OpenAI
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;
    private final GatewayHeaderAuthFilter gatewayHeaderAuthFilter;

    @Value("${axiom.gateway.bypass:false}")
    private boolean gatewayBypass;

    /**
     * Configures stateless authentication and public health endpoints.
     *
     * @param http security builder
     * @return configured filter chain
     * @throws Exception when Spring Security cannot build the chain
     */
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
