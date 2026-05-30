package com.axiom.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

/**
 * Entry point for the Axiom platform gateway service.
 */
@SpringBootApplication
@ConfigurationPropertiesScan
public class AxiomApiApplication {

    /**
     * Starts the reactive gateway application.
     *
     * @param args JVM startup arguments
     */
    public static void main(String[] args) {
        SpringApplication.run(AxiomApiApplication.class, args);
    }
}
