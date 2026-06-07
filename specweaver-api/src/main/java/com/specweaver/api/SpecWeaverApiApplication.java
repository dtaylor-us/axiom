package com.specweaver.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Spring Boot entry point for the SpecWeaver API service.
 *
 * @author OpenAI
 */
@SpringBootApplication
public class SpecWeaverApiApplication {

    /**
     * Starts the SpecWeaver API process.
     *
     * @param args command-line arguments
     */
    public static void main(String[] args) {
        SpringApplication.run(SpecWeaverApiApplication.class, args);
    }
}
