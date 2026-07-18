package com.memoria.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MemoriaApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(MemoriaApiApplication.class, args);
    }
}
