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
 * ADL-025: Cross-Service — Qdrant Access Prohibition (Hard enforcement).
 *
 * Ensures the API Gateway Service has no dependency on the Qdrant Java client.
 * The API service must not access Qdrant directly; only the agent service owns
 * vector data.
 */
class QdrantAccessProhibitionArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-025: No dependency on Qdrant Java client")
    void no_dependency_on_qdrant() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api..")
                .should().dependOnClassesThat().resideInAPackage("io.qdrant..")
                .as("ADL-025: API Gateway must not depend on Qdrant Java client");

        rule.check(importedClasses);
    }
}
