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
 * ADL-005: API Gateway Service — RestTemplate Prohibition (Hard enforcement).
 *
 * Ensures no class in the API Gateway Service depends on RestTemplate.
 * RestTemplate is blocking and will deadlock the SSE streaming threads,
 * causing observable runtime failures.
 */
class RestTemplateProhibitionArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-005: No class depends on RestTemplate")
    void no_dependency_on_rest_template() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api..")
                .should().dependOnClassesThat()
                .haveFullyQualifiedName("org.springframework.web.client.RestTemplate")
                .as("ADL-005: No class must depend on RestTemplate");

        rule.check(importedClasses);
    }
}
