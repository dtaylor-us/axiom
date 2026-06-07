package com.archon.api.architecture;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

/**
 * ADL-007: API Gateway Service — Database Access Boundary (Hard enforcement).
 *
 * Ensures chat controller and agent bridge client have no dependency on JPA or
 * JDBC libraries. Direct database access from controllers or bridge clients
 * bypasses the repository layer's validation and transaction management,
 * risking data corruption.
 */
class DatabaseAccessBoundaryArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-007: Chat domain has no dependency on JPA")
    void chat_has_no_dependency_on_jpa() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api.controller..")
                .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..")
                .as("ADL-007: Chat (controller) must not depend on JPA");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-007: Chat domain has no dependency on JDBC")
    void chat_has_no_dependency_on_jdbc() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api.controller..")
                .should().dependOnClassesThat().resideInAPackage("org.springframework.jdbc..")
                .as("ADL-007: Chat (controller) must not depend on JDBC");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-007: Bridge domain has no dependency on JPA")
    void bridge_has_no_dependency_on_jpa() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api.client..")
                .should().dependOnClassesThat().resideInAPackage("jakarta.persistence..")
                .as("ADL-007: Bridge (client) must not depend on JPA");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-007: Bridge domain has no dependency on JDBC")
    void bridge_has_no_dependency_on_jdbc() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api.client..")
                .should().dependOnClassesThat().resideInAPackage("org.springframework.jdbc..")
                .as("ADL-007: Bridge (client) must not depend on JDBC");

        rule.check(importedClasses);
    }
}
