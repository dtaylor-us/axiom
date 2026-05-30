package com.archon.api.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Configuration class for web MVC settings, including CORS configuration.
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {
    
    /**
     * Configures CORS mappings to allow cross-origin requests from localhost.
     *
     * @param registry the CORS registry
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                // Allow requests from any localhost port
                .allowedOriginPatterns("http://localhost:*")
                // Allow specified HTTP methods
                .allowedMethods("GET", "POST", "DELETE", "OPTIONS")
                // Allow all headers
                .allowedHeaders("*")
                // Allow credentials to be sent with requests
                .allowCredentials(true)
                // Cache CORS preflight response for 1 hour
                .maxAge(3600);
    }
}
