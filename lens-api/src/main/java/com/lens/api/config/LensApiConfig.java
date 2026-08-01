package com.lens.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "lens")
public record LensApiConfig() {}
