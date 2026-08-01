package com.archon.api;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@OpenAPIDefinition(info = @Info(title = "Archon API", version = "v1"))
@SpringBootApplication
@ConfigurationPropertiesScan
public class ArchonApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(ArchonApiApplication.class, args);
    }
}
