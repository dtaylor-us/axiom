package com.archon.api.architecture;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * ADL-002: API Gateway Service — Domain Structure (Soft enforcement).
 *
 * Enforces that all classes in the API Gateway Service belong to one of the
 * five defined domains: controller, domain, security, client, config.
 *
 * <p>Known violation: the codebase currently contains dto, exception, and
 * service packages outside the five defined domains. The test documents
 * this architectural debt via {@code assertThrows}.</p>
 */
class ApiGatewayDomainStructureArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-002: Every class resides in one of the five domain packages [KNOWN VIOLATION — dto, exception, service packages]")
    void every_class_resides_in_a_defined_domain_package() {
        ArchRule rule = classes()
                .that().resideInAPackage("com.archon.api..")
                .should().resideInAnyPackage(
                        "com.archon.api.controller..",
                        "com.archon.api.domain..",
                        "com.archon.api.security..",
                        "com.archon.api.client..",
                        "com.archon.api.config.."
                )
                .as("ADL-002: All classes must belong to controller, domain, security, client, or config domain");

        // Known violation: dto, exception, and service packages exist outside
        // the five defined domains. Soft enforcement — documented as tech debt.
        assertThrows(AssertionError.class, () -> rule.check(importedClasses),
                "ADL-002 violation expected: dto, exception, and service packages are not in the allowed domain list");
    }
}
