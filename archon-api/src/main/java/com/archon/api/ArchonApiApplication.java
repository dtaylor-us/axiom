package com.archon.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class ArchonApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(ArchonApiApplication.class, args);
    }
}
