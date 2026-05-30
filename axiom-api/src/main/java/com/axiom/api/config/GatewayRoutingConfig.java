package com.axiom.api.config;

import org.springframework.context.annotation.Configuration;

/**
 * Gateway routing configuration for Axiom platform.
 *
 * Routes are defined in application.yml using Spring Cloud Gateway's YAML route DSL.
 * This class holds only the programmatic configuration that cannot be expressed in YAML.
 *
 * Current routes (Step 1):
 *   /api/v1/archon/** -> archon-api:8081
 *
 * Future routes (added as pillars are built):
 *   /api/v1/specweaver/** -> specweaver-api:8082
 *   /api/v1/scout/**      -> scout-api:8083
 *   /api/v1/forge/**      -> forge-api:8084
 *
 * Auth endpoints (/api/v1/auth/**) are handled by axiom-api directly - they are not
 * routed to a pillar.
 */
@Configuration
public class GatewayRoutingConfig {
    // Most route definitions are intentionally kept in application.yml.
}
