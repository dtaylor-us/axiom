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
 * ADL-004: API Gateway Service — LLM Call Prohibition (Hard enforcement).
 *
 * Ensures the API Gateway Service has no dependency on any LLM client library.
 * LLM client calls from the API gateway would bypass the agent's orchestration
 * pipeline, causing duplicate billing, inconsistent behavior, and scattered
 * API key usage.
 */
class LlmCallProhibitionArchitectureTest {

    private static JavaClasses importedClasses;

    @BeforeAll
    static void setUp() {
        importedClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.archon.api");
    }

    @Test
    @DisplayName("ADL-004: No dependency on OpenAI library")
    void no_dependency_on_openai() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api..")
                .should().dependOnClassesThat().resideInAPackage("com.theokanning.openai..")
                .as("ADL-004: API Gateway must not depend on OpenAI library");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-004: No dependency on Azure OpenAI library")
    void no_dependency_on_azure_openai() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api..")
                .should().dependOnClassesThat().resideInAPackage("com.azure.ai.openai..")
                .as("ADL-004: API Gateway must not depend on Azure OpenAI library");

        rule.check(importedClasses);
    }

    @Test
    @DisplayName("ADL-004: No dependency on LangChain library")
    void no_dependency_on_langchain() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("com.archon.api..")
                .should().dependOnClassesThat().resideInAPackage("dev.langchain4j..")
                .as("ADL-004: API Gateway must not depend on LangChain4j library");

        rule.check(importedClasses);
    }
}
