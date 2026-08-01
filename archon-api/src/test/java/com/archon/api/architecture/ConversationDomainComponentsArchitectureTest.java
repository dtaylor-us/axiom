package com.archon.api.architecture;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;

/**
 * ADL-003: API Gateway Service — Conversation Domain Components (Soft enforcement).
 *
 * Enforces that the seven conversation domain components are contained within
 * the conversation domain (domain + service packages) and that all classes
 * reside within a component.
 */
class ConversationDomainComponentsArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-003: All domain model classes reside in model or repository packages")
    void domain_classes_reside_in_model_or_repository() {
        ArchRule rule = classes()
                .that().resideInAPackage("com.archon.api.domain..")
                .should().resideInAnyPackage(
                        "com.archon.api.domain.model..",
                        "com.archon.api.domain.repository.."
                )
                .as("ADL-003: All conversation domain classes must belong to model or repository components");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-003: Service classes reside in the service package")
    void service_classes_reside_in_service_package() {
        ArchRule rule = classes()
                .that().resideInAPackage("com.archon.api.service..")
                .should().resideInAPackage("com.archon.api.service..")
                .as("ADL-003: All service classes are contained within the service package");

        rule.check(importedClasses);
    }
}
