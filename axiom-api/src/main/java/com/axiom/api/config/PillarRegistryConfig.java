package com.axiom.api.config;

import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Binds per-pillar endpoints and enablement flags from configuration.
 */
@Component
@ConfigurationProperties(prefix = "axiom.pillars")
public class PillarRegistryConfig {

    private PillarDefinition archon = new PillarDefinition();
    private PillarDefinition specweaver = new PillarDefinition();
    private PillarDefinition lens = new PillarDefinition();

    public PillarDefinition getArchon() {
        return archon;
    }

    public void setArchon(PillarDefinition archon) {
        this.archon = archon;
    }

    public PillarDefinition getSpecweaver() {
        return specweaver;
    }

    public void setSpecweaver(PillarDefinition specweaver) {
        this.specweaver = specweaver;
    }

    public PillarDefinition getLens() {
        return lens;
    }

    public void setLens(PillarDefinition lens) {
        this.lens = lens;
    }

    /**
     * Returns all pillar definitions in a stable order for deterministic health output.
     *
     * @return ordered pillar map keyed by pillar name
     */
    public Map<String, PillarDefinition> asOrderedMap() {
        Map<String, PillarDefinition> pillars = new LinkedHashMap<>();
        pillars.put("archon", archon);
        pillars.put("specweaver", specweaver);
        pillars.put("lens", lens);
        return pillars;
    }

    /**
     * Per-pillar connection configuration.
     */
    public static class PillarDefinition {

        private String baseUrl = "";
        private boolean enabled;
        private String healthPath = "/actuator/health";

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getHealthPath() {
            return healthPath;
        }

        public void setHealthPath(String healthPath) {
            this.healthPath = healthPath;
        }
    }
}
