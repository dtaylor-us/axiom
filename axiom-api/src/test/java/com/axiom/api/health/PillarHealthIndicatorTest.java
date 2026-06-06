package com.axiom.api.health;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.util.Map;

import com.axiom.api.config.PillarRegistryConfig;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.actuate.health.Health;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * Verifies pillar aggregation semantics, degraded behavior, and caching.
 */
class PillarHealthIndicatorTest {

    private MockWebServer archonServer;
    private MockWebServer specweaverServer;

    @BeforeEach
    void setup() throws IOException {
        archonServer = new MockWebServer();
        archonServer.start();
        specweaverServer = new MockWebServer();
        specweaverServer.start();
    }

    @AfterEach
    void cleanup() throws IOException {
        archonServer.shutdown();
        specweaverServer.shutdown();
    }

    /**
     * Returns UP when all enabled pillars report healthy status.
     */
    @Test
    @SuppressWarnings("unchecked")
    void returnsUpWhenAllEnabledPillarsAreHealthy() {
        archonServer.enqueue(new MockResponse().setResponseCode(200));
        specweaverServer.enqueue(new MockResponse().setResponseCode(200));

        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), defaultRegistry(true));

        Health health = indicator.health().block();
        Map<String, Object> components = (Map<String, Object>) health.getDetails().get("components");

        assertEquals("UP", health.getStatus().getCode());
        assertEquals("UP", ((Map<String, Object>) components.get("gateway")).get("status"));
        assertEquals("UP", ((Map<String, Object>) components.get("archon")).get("status"));
        assertEquals("UP", ((Map<String, Object>) components.get("specweaver")).get("status"));
    }

    /**
     * Returns DEGRADED when Archon responds but is unhealthy.
     */
    @Test
    @SuppressWarnings("unchecked")
    void returnsDegradedWhenArchonHealthEndpointReturns503() {
        archonServer.enqueue(new MockResponse().setResponseCode(503));
        specweaverServer.enqueue(new MockResponse().setResponseCode(200));

        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), defaultRegistry(true));

        Health health = indicator.health().block();
        Map<String, Object> components = (Map<String, Object>) health.getDetails().get("components");

        assertEquals("DEGRADED", ((Map<String, Object>) components.get("archon")).get("status"));
        assertEquals("UP", health.getStatus().getCode());
    }

    /**
     * Disabled pillars are OUT_OF_SERVICE by design.
     */
    @Test
    @SuppressWarnings("unchecked")
    void returnsOutOfServiceForDisabledPillars() {
        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), defaultRegistry(false));

        Health health = indicator.health().block();
        Map<String, Object> components = (Map<String, Object>) health.getDetails().get("components");

        assertEquals("OUT_OF_SERVICE", ((Map<String, Object>) components.get("archon")).get("status"));
        assertEquals("OUT_OF_SERVICE", ((Map<String, Object>) components.get("specweaver")).get("status"));
        assertEquals("OUT_OF_SERVICE", ((Map<String, Object>) components.get("scout")).get("status"));
        assertEquals("OUT_OF_SERVICE", ((Map<String, Object>) components.get("forge")).get("status"));
    }

    /**
     * Unreachable pillars degrade platform component status but do not mark it DOWN.
     */
    @Test
    @SuppressWarnings("unchecked")
    void returnsDownWhenArchonIsUnreachable() {
        PillarRegistryConfig registryConfig = defaultRegistry(true);

        PillarRegistryConfig.PillarDefinition archon = new PillarRegistryConfig.PillarDefinition();
        archon.setBaseUrl("http://127.0.0.1:6553");
        archon.setEnabled(true);
        archon.setHealthPath("/actuator/health");
        registryConfig.setArchon(archon);

        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), registryConfig);

        Health health = indicator.health().block();
        Map<String, Object> components = (Map<String, Object>) health.getDetails().get("components");

        assertEquals("DOWN", ((Map<String, Object>) components.get("archon")).get("status"));
        assertEquals("UP", health.getStatus().getCode());
    }

    /**
     * Overall status remains UP when one pillar is degraded.
     */
    @Test
    @SuppressWarnings("unchecked")
    void overallStatusRemainsUpWhenOnePillarIsDegraded() {
        archonServer.enqueue(new MockResponse().setResponseCode(503));
        specweaverServer.enqueue(new MockResponse().setResponseCode(200));

        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), defaultRegistry(true));

        Health health = indicator.health().block();
        Map<String, Object> components = (Map<String, Object>) health.getDetails().get("components");

        assertEquals("UP", health.getStatus().getCode());
        assertEquals("DEGRADED", ((Map<String, Object>) components.get("archon")).get("status"));
        assertEquals("UP", ((Map<String, Object>) components.get("specweaver")).get("status"));
    }

    /**
     * Caches health for 30 seconds to prevent fan-out storms under probe load.
     */
    @Test
    @SuppressWarnings("unchecked")
    void healthResultIsCachedForThirtySeconds() {
        archonServer.enqueue(new MockResponse().setResponseCode(200));
        specweaverServer.enqueue(new MockResponse().setResponseCode(200));
        archonServer.enqueue(new MockResponse().setResponseCode(503));
        specweaverServer.enqueue(new MockResponse().setResponseCode(503));

        PillarHealthIndicator indicator = new PillarHealthIndicator(WebClient.builder(), defaultRegistry(true));

        Health first = indicator.health().block();
        Health second = indicator.health().block();

        Map<String, Object> firstComponents = (Map<String, Object>) first.getDetails().get("components");
        Map<String, Object> secondComponents = (Map<String, Object>) second.getDetails().get("components");

        assertEquals("UP", ((Map<String, Object>) firstComponents.get("archon")).get("status"));
        assertEquals("UP", ((Map<String, Object>) secondComponents.get("archon")).get("status"));
        assertEquals(1, archonServer.getRequestCount());
        assertEquals(1, specweaverServer.getRequestCount());
    }

    private PillarRegistryConfig defaultRegistry(boolean enabled) {
        PillarRegistryConfig config = new PillarRegistryConfig();

        PillarRegistryConfig.PillarDefinition archon = new PillarRegistryConfig.PillarDefinition();
        archon.setBaseUrl(archonServer.url("/").toString());
        archon.setEnabled(enabled);
        archon.setHealthPath("/actuator/health");

        PillarRegistryConfig.PillarDefinition specweaver = new PillarRegistryConfig.PillarDefinition();
        specweaver.setBaseUrl(specweaverServer.url("/").toString());
        specweaver.setEnabled(enabled);
        specweaver.setHealthPath("/actuator/health");

        PillarRegistryConfig.PillarDefinition disabled = new PillarRegistryConfig.PillarDefinition();
        disabled.setBaseUrl("http://localhost:9999");
        disabled.setEnabled(false);
        disabled.setHealthPath("/actuator/health");

        config.setArchon(archon);
        config.setSpecweaver(specweaver);
        config.setScout(disabled);
        config.setForge(disabled);

        return config;
    }
}
