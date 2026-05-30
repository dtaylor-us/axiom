package com.archon.api.architecture;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

/**
 * Architecture tests for durable run lifecycle boundaries.
 */
class DurableRunArchitectureTest {

    private final JavaClasses classes = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages("com.archon.api");

    @Test
    void controllers_haveNoDependencyOnPipelineRunRepository() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("..controller..")
                .should().dependOnClassesThat()
                .haveFullyQualifiedName("com.archon.api.domain.repository.PipelineRunRepository")
                .because("Controllers must not bypass the service layer for durable run persistence.");
        rule.check(classes);
    }

    @Test
    void chatService_dependsOnPipelineRunService() {
        ArchRule rule = classes()
                .that().haveFullyQualifiedName("com.archon.api.service.ChatService")
                .should().dependOnClassesThat().haveFullyQualifiedName("com.archon.api.service.PipelineRunService");
        rule.check(classes);
    }
}

