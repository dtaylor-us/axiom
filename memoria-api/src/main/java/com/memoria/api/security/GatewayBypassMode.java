package com.memoria.api.security;

import org.springframework.core.env.Environment;

import java.util.Locale;
import java.util.Map;

public final class GatewayBypassMode {

    private static final String AXIOM_GATEWAY_BYPASS_DOT_KEY = "axiom.gateway.bypass";
    private static final String AXIOM_GATEWAY_BYPASS_ENV_KEY = "AXIOM_GATEWAY_BYPASS";

    private GatewayBypassMode() {
    }

    public static boolean isEnabled(Environment environment) {
        return isEnabled(environment, System.getenv());
    }

    static boolean isEnabled(Environment environment, Map<String, String> systemEnvironment) {
        String value = firstNonBlank(
                environment.getProperty(AXIOM_GATEWAY_BYPASS_DOT_KEY),
                environment.getProperty(AXIOM_GATEWAY_BYPASS_ENV_KEY),
                systemEnvironment.get(AXIOM_GATEWAY_BYPASS_ENV_KEY));
        if (value == null) {
            return false;
        }
        String normalized = value.trim().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "1", "true", "yes", "y", "on" -> true;
            default -> false;
        };
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }
}