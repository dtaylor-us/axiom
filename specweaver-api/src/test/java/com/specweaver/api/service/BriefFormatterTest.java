package com.specweaver.api.service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import com.specweaver.api.domain.model.Session;
import com.specweaver.api.dto.ArchInputPackageDto;
import com.specweaver.api.dto.ConflictItemDto;
import com.specweaver.api.dto.GapAreaDto;

import static org.junit.jupiter.api.Assertions.assertTrue;

class BriefFormatterTest {

    private final BriefFormatter briefFormatter = new BriefFormatter(new ObjectMapper());

    @Test
    void format_includesSystemDescription() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("**System:** Claims and payments platform"));
    }

    @Test
    void format_groupsRequirementsByCategory() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("[FUNCTIONAL]"));
        assertTrue(brief.contains("[NON_FUNCTIONAL]"));
    }

    @Test
    void format_includesHighConfidenceRequirements() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("[HIGH]"));
        assertTrue(brief.contains("Users can submit claims"));
    }

    @Test
    void format_includesInferredRequirementsWithReasoning() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("[INFERRED]"));
        assertTrue(brief.contains("EU residency implies GDPR obligations"));
    }

    @Test
    void format_includesGapClarificationQuestions() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("What is the maximum acceptable payment authorization latency?"));
    }

    @Test
    void format_includesConflictDescriptions() {
        String brief = briefFormatter.format(basePackage(), session());

        assertTrue(brief.contains("Database must be relational and document-first"));
    }

    @Test
    void format_staysUnderFourThousandCharactersForLargePackages() {
        String brief = briefFormatter.format(largePackage(48), session());

        assertTrue(brief.length() <= BriefFormatter.MAX_BRIEF_CHARS);
    }

    @Test
    void format_truncatesRequirementsGracefullyWhenTooLong() {
        String brief = briefFormatter.format(largePackage(60), session());

        assertTrue(brief.contains("additional requirement(s) omitted for brevity"));
    }

    @Test
    void format_neverTruncatesSystemDescriptionOrGaps() {
        String systemDescription = "Critical healthcare claims workflow for cross-border reimbursements";
        GapAreaDto gap = new GapAreaDto(
                "GAP-9",
                "Regulatory audit controls",
                "critical",
                "Audit controls are missing.",
                "Which retention and audit standards are mandatory?",
                List.of("non_functional")
        );

        ArchInputPackageDto pkg = new ArchInputPackageDto(
                "pkg-1",
                "sw-1",
                "2026-06-01T00:00:00Z",
                systemDescription,
                largeRequirements(70),
                List.of(gap),
                List.of(),
                List.of(Map.of("sourceLabel", "workshop-notes")),
                new BigDecimal("0.72"),
                70,
                40,
                20,
                0,
                1,
                0
        );

        String brief = briefFormatter.format(pkg, session());

        assertTrue(brief.contains(systemDescription));
        assertTrue(brief.contains("Which retention and audit standards are mandatory?"));
    }

    private ArchInputPackageDto basePackage() {
        return new ArchInputPackageDto(
                "pkg-1",
                "sw-1",
                "2026-06-01T00:00:00Z",
                "Claims and payments platform",
                List.of(
                        Map.of(
                                "category", "functional",
                                "statement", "Users can submit claims",
                                "confidence", "HIGH",
                                "isInferred", false
                        ),
                        Map.of(
                                "category", "non_functional",
                                "statement", "System must achieve 99.9% monthly availability",
                                "confidence", "HIGH",
                                "isInferred", false
                        ),
                        Map.of(
                                "category", "inferred",
                                "statement", "Data processing must satisfy GDPR",
                                "confidence", "INFERRED",
                                "isInferred", true,
                                "inferenceReasoning", "EU residency implies GDPR obligations"
                        )
                ),
                List.of(
                        new GapAreaDto(
                                "GAP-1",
                                "Latency target",
                                "high",
                                "No explicit latency target was provided.",
                                "What is the maximum acceptable payment authorization latency?",
                                List.of("non_functional")
                        )
                ),
                List.of(
                        new ConflictItemDto(
                                "C-1",
                                List.of("REQ-1", "REQ-2"),
                                "Database must be relational and document-first",
                                List.of("Use PostgreSQL", "Use Cosmos DB"),
                                "Which datastore is authoritative for claims writes?"
                        )
                ),
                List.of(
                        Map.of("sourceLabel", "stakeholder-workshop"),
                        Map.of("filename", "requirements.docx")
                ),
                new BigDecimal("0.81"),
                3,
                2,
                1,
                0,
                1,
                1
        );
    }

    private ArchInputPackageDto largePackage(int requirementCount) {
        return new ArchInputPackageDto(
                "pkg-1",
                "sw-1",
                "2026-06-01T00:00:00Z",
                "Large package for truncation behavior",
                largeRequirements(requirementCount),
                List.of(
                        new GapAreaDto(
                                "GAP-1",
                                "Resilience",
                                "high",
                                "Resilience strategy is not explicit.",
                                "What recovery target should be met after a regional outage?",
                                List.of("non_functional")
                        )
                ),
                List.of(
                        new ConflictItemDto(
                                "C-1",
                                List.of("REQ-1", "REQ-2"),
                                "Synchronous writes conflict with event-only propagation",
                                List.of(),
                                "Which consistency model should be prioritized?"
                        )
                ),
                List.of(Map.of("sourceLabel", "bulk-upload")),
                new BigDecimal("0.70"),
                requirementCount,
                20,
                10,
                0,
                1,
                1
        );
    }

    private List<Object> largeRequirements(int requirementCount) {
        List<Object> requirements = new ArrayList<>();
        for (int i = 0; i < requirementCount; i++) {
            requirements.add(Map.of(
                    "category", i % 2 == 0 ? "functional" : "non_functional",
                    "statement", "Requirement statement " + i + " describing behavior and constraints for the architecture decision pipeline.",
                    "confidence", i % 3 == 0 ? "HIGH" : "MEDIUM",
                    "isInferred", false
            ));
        }
        return requirements;
    }

    private Session session() {
        return Session.builder()
                .id(UUID.randomUUID())
                .build();
    }
}
