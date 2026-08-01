package com.archon.api.config;

import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Tracer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Exposes OpenTelemetry beans for manual span creation.
 *
 * Spring Boot auto-configures the OTel SDK via Micrometer bridge
 * (micrometer-tracing-bridge-otel). This config class provides a
 * named Tracer bean for cases where manual instrumentation is needed
 * beyond what Micrometer annotation-driven tracing covers.
 */
@Configuration
public class ObservabilityConfig {

    /**
     * Named tracer scoped to the archon-api service.
     * Inject this in any service that needs custom child spans.
     */
    @Bean
    public Tracer archonTracer(OpenTelemetry openTelemetry) {
        return openTelemetry.getTracer("archon-api");
    }
}
