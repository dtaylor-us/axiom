package com.axiom.api.filter;

import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;

/**
 * Ensures routed pillar requests always carry validated user context headers.
 */
@Component
public class UserContextForwardingFilter
        extends AbstractGatewayFilterFactory<UserContextForwardingFilter.Config> {

    public UserContextForwardingFilter() {
        super(Config.class);
    }

    /**
     * Returns the YAML DSL filter name used in application route definitions.
     *
     * @return stable filter factory name
     */
    @Override
    public String name() {
        return "UserContextForwarding";
    }

    /**
     * Re-applies identity headers from exchange attributes to forwarded requests.
     *
     * @param config filter configuration placeholder
     * @return gateway filter
     */
    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = (String) exchange.getAttributes().get(JwtAuthenticationFilter.USER_ID_ATTRIBUTE);
            String email = (String) exchange.getAttributes().get(JwtAuthenticationFilter.EMAIL_ATTRIBUTE);

            if (userId == null || email == null) {
                return chain.filter(exchange);
            }

            ServerHttpRequest request = exchange.getRequest().mutate()
                    .header(JwtAuthenticationFilter.AXIOM_USER_ID_HEADER, userId)
                    .header(JwtAuthenticationFilter.AXIOM_EMAIL_HEADER, email)
                    .build();

            return chain.filter(exchange.mutate().request(request).build());
        };
    }

    /**
     * Marker configuration class for the Gateway filter factory.
     */
    public static class Config {
    }
}
