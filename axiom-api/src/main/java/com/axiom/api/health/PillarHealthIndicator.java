package com.axiom.api.health;

import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import com.axiom.api.config.PillarRegistryConfig;
import com.axiom.api.config.PillarRegistryConfig.PillarDefinition;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.ReactiveHealthIndicator;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import reactor.core.publisher.Mono;

/**
 * Aggregates health from all enabled pillar services.
 *
 * Exposed through Spring Boot Actuator health endpoints.
 */
@Component
public class PillarHealthIndicator implements ReactiveHealthIndicator {

    private static final Duration PILLAR_TIMEOUT = Duration.ofSeconds(3);
    private static final Duration CACHE_TTL = Duration.ofSeconds(30);
    private static final String STATUS_UP = "UP";
    private static final String STATUS_DEGRADED = "DEGRADED";
    private static final String STATUS_OUT_OF_SERVICE = "OUT_OF_SERVICE";

    private final WebClient webClient;
    private final PillarRegistryConfig pillarRegistry;

    private volatile CachedHealth cachedHealth;

    public PillarHealthIndicator(WebClient.Builder webClientBuilder, PillarRegistryConfig pillarRegistry) {
        this.webClient = webClientBuilder.build();
        this.pillarRegistry = pillarRegistry;
    }

    /**
     * Returns cached pillar health when available, otherwise refreshes it.
     *
     * @return platform health containing per-pillar component states
     */
    @Override
    public Mono<Health> health() {
        CachedHealth currentCache = cachedHealth;
        if (currentCache != null && currentCache.expiresAt().isAfter(Instant.now())) {
            return Mono.just(currentCache.health());
        }

        return refreshHealth().doOnNext(health ->
                cachedHealth = new CachedHealth(Instant.now().plus(CACHE_TTL), health));
    }

    private Mono<Health> refreshHealth() {
        Map<String, Mono<String>> statusMonos = new LinkedHashMap<>();

        for (Map.Entry<String, PillarDefinition> entry : pillarRegistry.asOrderedMap().entrySet()) {
            String pillarName = entry.getKey();
            PillarDefinition definition = entry.getValue();

            if (!definition.isEnabled()) {
                statusMonos.put(pillarName, Mono.just(STATUS_OUT_OF_SERVICE));
                continue;
            }

            statusMonos.put(pillarName, resolvePillarStatus(definition));
        }

        return Mono.zip(statusMonos.values(), values -> {
            Map<String, Object> components = new LinkedHashMap<>();
            int i = 0;
            for (String pillarName : statusMonos.keySet()) {
                components.put(pillarName, Map.of("status", values[i++]));
            }
            return Health.up().withDetail("components", components).build();
        });
    }

    private Mono<String> resolvePillarStatus(PillarDefinition definition) {
        String healthUrl = normalizeBaseUrl(definition.getBaseUrl()) + definition.getHealthPath();

        return webClient.get()
                .uri(healthUrl)
                .exchangeToMono(response -> {
                    if (response.statusCode().is2xxSuccessful()) {
                        return Mono.just(STATUS_UP);
                    }
                    return Mono.just(STATUS_DEGRADED);
                })
                .timeout(PILLAR_TIMEOUT)
                .onErrorReturn(STATUS_DEGRADED);
    }

    private String normalizeBaseUrl(String baseUrl) {
        if (baseUrl.endsWith("/")) {
            return baseUrl.substring(0, baseUrl.length() - 1);
        }
        return baseUrl;
    }

    private record CachedHealth(Instant expiresAt, Health health) {
    }
}
