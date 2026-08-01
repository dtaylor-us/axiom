package com.specweaver.api.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import com.specweaver.api.domain.model.Session;
import com.specweaver.api.dto.ArchInputPackageDto;
import com.specweaver.api.dto.ConflictItemDto;
import com.specweaver.api.dto.GapAreaDto;

/**
 * Formats package payloads as plain-language briefs for manual Archon chat submission.
 *
 * <p>The output is designed for a user-reviewed handoff, so it favors clear summaries
 * and deterministic truncation over raw JSON fidelity.</p>
 */
@Component
@RequiredArgsConstructor
public class BriefFormatter {

    static final int MAX_BRIEF_CHARS = 4_000;
    static final int MAX_REQUIREMENTS = 30;

    private final ObjectMapper objectMapper;

    /**
     * Builds a plain-language requirements brief suitable for the Archon chat input.
     *
     * @param pkg parsed package payload from SpecWeaver
     * @param session owning session context
     * @return formatted and size-capped brief
     */
    public String format(ArchInputPackageDto pkg, Session session) {
        String systemDescription = valueOrDefault(pkg.systemDescription(), "Not provided.");
        String summaryLine = formatSummary(pkg);
        String gapsSection = formatGaps(pkg.gaps());
        String conflictsSection = formatConflicts(pkg.conflicts());
        String sourceSection = formatSources(pkg.sourceDocuments());

        String header = "## Requirements Package from SpecWeaver\n\n"
                + "**System:** " + systemDescription + "\n\n"
                + "**Summary:** " + summaryLine + "\n\n"
                + "**Session:** " + session.getId() + "\n\n"
                + "**Requirements:**\n";

        String footer = "\n"
                + gapsSection + "\n\n"
                + conflictsSection + "\n\n"
                + sourceSection;

        List<String> requirementLines = formatRequirementLines(pkg.requirements());
        int maxRequirementChars = Math.max(0, MAX_BRIEF_CHARS - header.length() - footer.length());
        String requirementsBody = fitRequirements(requirementLines, maxRequirementChars);

        String brief = header + requirementsBody + footer;
        if (brief.length() <= MAX_BRIEF_CHARS) {
            return brief;
        }

        // Preserve system description, gaps, and conflicts. If still too long,
        // trim source metadata first because it is the least critical section.
        String trimmedSource = trimSourceSectionToFit(
                sourceSection,
                MAX_BRIEF_CHARS - header.length() - requirementsBody.length() - gapsSection.length() - conflictsSection.length() - 6);

        return header
                + requirementsBody
                + "\n"
                + gapsSection
                + "\n\n"
                + conflictsSection
                + "\n\n"
                + trimmedSource;
    }

    private String formatSummary(ArchInputPackageDto pkg) {
        int total = Math.max(pkg.totalRequirements(), sizeOf(pkg.requirements()));
        int high = pkg.highConfidenceCount();
        int inferred = pkg.inferredCount();
        int gaps = Math.max(pkg.gapCount(), sizeOf(pkg.gaps()));
        int conflicts = Math.max(pkg.conflictCount(), sizeOf(pkg.conflicts()));
        int readinessPercent = toReadinessPercent(pkg.readinessScore());
        return "%d requirements (%d high confidence, %d inferred) - %d gaps - %d conflicts - Readiness: %d%%"
                .formatted(total, high, inferred, gaps, conflicts, readinessPercent);
    }

    private int toReadinessPercent(BigDecimal score) {
        if (score == null) {
            return 0;
        }
        return score
                .multiply(BigDecimal.valueOf(100))
                .setScale(0, RoundingMode.HALF_UP)
                .intValue();
    }

    private String formatGaps(List<GapAreaDto> gaps) {
        if (gaps == null || gaps.isEmpty()) {
            return "**Gaps to address:**\n- None identified.";
        }

        StringBuilder sb = new StringBuilder("**Gaps to address:**\n");
        for (GapAreaDto gap : gaps) {
            sb.append("- ")
                    .append(valueOrDefault(gap.severity(), "unknown"))
                    .append(": ")
                    .append(valueOrDefault(gap.area(), "Unspecified area"))
                    .append(" — ")
                    .append(valueOrDefault(gap.clarificationQuestion(), "Clarification needed"))
                    .append("\n");
        }
        return sb.toString().trim();
    }

    private String formatConflicts(List<ConflictItemDto> conflicts) {
        if (conflicts == null || conflicts.isEmpty()) {
            return "**Conflicts to resolve:**\n- None identified.";
        }

        StringBuilder sb = new StringBuilder("**Conflicts to resolve:**\n");
        for (ConflictItemDto conflict : conflicts) {
            sb.append("- ")
                    .append(valueOrDefault(conflict.description(), "Unspecified conflict"))
                    .append(" — ")
                    .append(valueOrDefault(conflict.clarificationQuestion(), "Clarification needed"))
                    .append("\n");
        }
        return sb.toString().trim();
    }

    private String formatSources(List<Object> sourceDocuments) {
        List<String> labels = new ArrayList<>();
        if (sourceDocuments != null) {
            for (Object sourceDocument : sourceDocuments) {
                Map<String, Object> sourceMap = toMap(sourceDocument);
                String label = valueOrDefault(
                        toStringOrNull(sourceMap.get("sourceLabel")),
                        toStringOrNull(sourceMap.get("filename"))
                );
                if (label != null && !label.isBlank()) {
                    labels.add(label);
                }
            }
        }

        String joinedLabels = labels.isEmpty() ? "none" : String.join(", ", labels);
        return "**Source documents:** %d document(s) analysed (%s)"
                .formatted(sizeOf(sourceDocuments), joinedLabels);
    }

    private String trimSourceSectionToFit(String sourceSection, int maxChars) {
        if (maxChars <= 0) {
            return "**Source documents:** metadata omitted for brevity.";
        }
        if (sourceSection.length() <= maxChars) {
            return sourceSection;
        }
        if (maxChars <= 3) {
            return sourceSection.substring(0, maxChars);
        }
        return sourceSection.substring(0, maxChars - 3) + "...";
    }

    private String fitRequirements(List<String> requirementLines, int maxChars) {
        if (requirementLines.isEmpty() || maxChars <= 0) {
            return "- None identified.";
        }

        StringBuilder sb = new StringBuilder();
        int included = 0;
        int maxLines = Math.min(requirementLines.size(), MAX_REQUIREMENTS);

        for (int i = 0; i < maxLines; i++) {
            String line = requirementLines.get(i) + "\n";
            if (sb.length() + line.length() > maxChars) {
                break;
            }
            sb.append(line);
            included += 1;
        }

        int omitted = requirementLines.size() - included;
        if (omitted > 0) {
            String omissionLine = "- ... %d additional requirement(s) omitted for brevity.\n".formatted(omitted);
            if (sb.length() + omissionLine.length() <= maxChars) {
                sb.append(omissionLine);
            }
        }

        if (included == 0) {
            return "- Requirements omitted to keep the brief within size limits.";
        }

        return sb.toString().trim();
    }

    private List<String> formatRequirementLines(List<Object> requirements) {
        if (requirements == null || requirements.isEmpty()) {
            return List.of();
        }

        Map<String, List<RequirementSummary>> grouped = new LinkedHashMap<>();
        for (Object requirement : requirements) {
            RequirementSummary summary = toRequirementSummary(requirement);
            grouped.computeIfAbsent(summary.category(), ignored -> new ArrayList<>()).add(summary);
        }

        List<String> lines = new ArrayList<>();
        grouped.forEach((category, values) -> {
            values.sort(Comparator.comparingInt(RequirementSummary::priority));
            for (RequirementSummary requirement : values) {
                lines.add(toRequirementLine(requirement));
            }
        });

        lines.sort(Comparator
                .comparingInt((String line) -> line.contains("[FUNCTIONAL]") ? 0 : 1)
                .thenComparingInt(this::confidencePriority));
        return lines;
    }

    private int confidencePriority(String line) {
        if (line.contains("[HIGH]")) {
            return 0;
        }
        if (line.contains("[MEDIUM]")) {
            return 1;
        }
        if (line.contains("[LOW]")) {
            return 2;
        }
        if (line.contains("[INFERRED]")) {
            return 3;
        }
        return 4;
    }

    private String toRequirementLine(RequirementSummary requirement) {
        StringBuilder line = new StringBuilder("- [")
                .append(requirement.category())
                .append("] ")
                .append(requirement.statement())
                .append("  [")
                .append(requirement.confidence())
                .append("]");

        if (requirement.isInferred() && requirement.reasoning() != null && !requirement.reasoning().isBlank()) {
            line.append(" — ").append(requirement.reasoning());
        }

        return line.toString();
    }

    private RequirementSummary toRequirementSummary(Object rawRequirement) {
        Map<String, Object> requirement = toMap(rawRequirement);

        String category = valueOrDefault(toStringOrNull(requirement.get("category")), "UNKNOWN")
                .toUpperCase(Locale.ROOT);
        String statement = valueOrDefault(toStringOrNull(requirement.get("statement")), "Requirement statement missing.");
        String confidence = valueOrDefault(toStringOrNull(requirement.get("confidence")), "UNKNOWN")
                .toUpperCase(Locale.ROOT);
        boolean inferred = Boolean.TRUE.equals(requirement.get("isInferred")) || "INFERRED".equals(confidence);
        String reasoning = toStringOrNull(requirement.get("inferenceReasoning"));

        int priority = 10;
        if ("FUNCTIONAL".equals(category) && "HIGH".equals(confidence)) {
            priority = 0;
        } else if ("FUNCTIONAL".equals(category)) {
            priority = 1;
        } else if ("HIGH".equals(confidence)) {
            priority = 2;
        } else if (inferred) {
            priority = 4;
        } else {
            priority = 3;
        }

        return new RequirementSummary(category, statement, confidence, inferred, reasoning, priority);
    }

    private Map<String, Object> toMap(Object value) {
        if (value == null) {
            return Map.of();
        }
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> mapped = new LinkedHashMap<>();
            rawMap.forEach((key, mapValue) -> mapped.put(String.valueOf(key), mapValue));
            return mapped;
        }
        return objectMapper.convertValue(value, objectMapper.getTypeFactory().constructMapType(
                LinkedHashMap.class,
                String.class,
                Object.class
        ));
    }

    private String toStringOrNull(Object value) {
        if (value == null) {
            return null;
        }
        return String.valueOf(value);
    }

    private int sizeOf(List<?> values) {
        return values == null ? 0 : values.size();
    }

    private String valueOrDefault(String value, String fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value;
    }

    private record RequirementSummary(
            String category,
            String statement,
            String confidence,
            boolean isInferred,
            String reasoning,
            int priority
    ) {
    }
}
