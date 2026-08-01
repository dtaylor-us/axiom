package com.axiom.api.config;

import com.axiom.api.filter.JwtAuthenticationFilter;
import com.axiom.api.filter.UserContextForwardingFilter;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Registers programmatic gateway filter factories referenced from YAML routes.
 */
@Configuration
public class GatewayRoutingConfig {

    /**
     * Registers the user context forwarding filter factory used by default gateway filters.
     *
     * @param jwtAuthenticationFilter filter that establishes the request user context
     * @return configured forwarding filter
     */
    @Bean
    public UserContextForwardingFilter userContextForwardingFilter(
            JwtAuthenticationFilter jwtAuthenticationFilter,
            @Value("${axiom.internal.secret:}") String internalSecret) {
        return new UserContextForwardingFilter(jwtAuthenticationFilter, internalSecret);
    }
}
