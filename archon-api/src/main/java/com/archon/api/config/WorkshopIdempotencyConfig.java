package com.archon.api.config;

import com.archon.api.workshop.service.WorkshopService;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.TimeUnit;

/**
 * Configures the short-lived workshop submission idempotency cache.
 *
 * <p>The cache suppresses browser double-clicks and rapid client retries
 * without making genuine later submissions impossible.</p>
 */
@Configuration
public class WorkshopIdempotencyConfig {
    private static final int IDEMPOTENCY_TTL_MINUTES = 5;
    private static final int IDEMPOTENCY_MAX_ENTRIES = 10_000;

    /**
     * Stores completed send-to-pipeline results by client-generated key.
     *
     * @return Caffeine cache with a five-minute TTL.
     */
    @Bean
    public Cache<String, WorkshopService.SendToPipelineResult> idempotencyCache() {
        return Caffeine.newBuilder()
                .expireAfterWrite(IDEMPOTENCY_TTL_MINUTES, TimeUnit.MINUTES)
                .maximumSize(IDEMPOTENCY_MAX_ENTRIES)
                .build();
    }
}
