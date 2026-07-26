package com.memoria.api.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class GatewayBypassModeTest {

    @Test
    void isEnabled_usesPropertyWhenDefined() {
        MockEnvironment environment = new MockEnvironment()
                .withProperty("axiom.gateway.bypass", "true");

        boolean enabled = GatewayBypassMode.isEnabled(environment, Map.of());

        assertThat(enabled).isTrue();
    }

    @Test
    void isEnabled_fallsBackToEnvVariableWhenPropertyMissing() {
        MockEnvironment environment = new MockEnvironment();

        boolean enabled = GatewayBypassMode.isEnabled(environment, Map.of("AXIOM_GATEWAY_BYPASS", "true"));

        assertThat(enabled).isTrue();
    }

    @Test
    void isEnabled_defaultsToFalseWhenUnset() {
        MockEnvironment environment = new MockEnvironment();

        boolean enabled = GatewayBypassMode.isEnabled(environment, Map.of());

        assertThat(enabled).isFalse();
    }
}