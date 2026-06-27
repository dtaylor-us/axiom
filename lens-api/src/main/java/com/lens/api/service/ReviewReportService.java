package com.lens.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.lens.api.domain.model.OverallRating;
import com.lens.api.domain.model.ReviewFinding;
import com.lens.api.domain.model.ReviewReport;
import com.lens.api.domain.model.ReviewRisk;
import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;
import com.lens.api.exception.ResourceNotFoundException;
import com.lens.api.repository.ReviewFindingRepository;
import com.lens.api.repository.ReviewReportRepository;
import com.lens.api.repository.ReviewRiskRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ReviewReportService {

    private final ObjectMapper objectMapper;
    private final ReviewReportRepository reviewReportRepository;
    private final ReviewRiskRepository reviewRiskRepository;
    private final ReviewFindingRepository reviewFindingRepository;
    private final ReviewSessionService reviewSessionService;

    public ReviewReportService(
            ObjectMapper objectMapper,
            ReviewReportRepository reviewReportRepository,
            ReviewRiskRepository reviewRiskRepository,
            ReviewFindingRepository reviewFindingRepository,
            ReviewSessionService reviewSessionService) {
        this.objectMapper = objectMapper;
        this.reviewReportRepository = reviewReportRepository;
        this.reviewRiskRepository = reviewRiskRepository;
        this.reviewFindingRepository = reviewFindingRepository;
        this.reviewSessionService = reviewSessionService;
    }

    @Transactional
    public ReviewReport saveReport(UUID sessionId, Map<String, Object> agentReport) {
        reviewReportRepository.findBySessionId(sessionId).ifPresent(existing -> {
            reviewFindingRepository.deleteByReportId(existing.getId());
            reviewRiskRepository.deleteByReportId(existing.getId());
            reviewReportRepository.delete(existing);
        });

        ReviewReport report = new ReviewReport();
        report.setId(UUID.randomUUID());
        report.setSessionId(sessionId);
        report.setExecutiveSummary(asText(agentReport.get("executiveSummary")));
        report.setOverallRating(toOverallRating(asText(agentReport.get("overallRating"))));
        report.setAzureWafScorecard(toJson(agentReport.get("azureWafScorecard")));
        report.setAtamAnalysis(toJson(agentReport.get("atamAnalysis")));
        report.setSeiAnalysis(toJson(agentReport.get("seiAnalysis")));
        report.setStructuralAnalysis(toJson(agentReport.get("structuralAnalysis")));
        report.setInsufficientInfoGaps(toJson(agentReport.get("insufficientInfoFindings")));
        report.setRecommendationRoadmap(toJson(agentReport.get("recommendations")));
        report.setGeneratedAt(LocalDateTime.now());

        ReviewReport saved = reviewReportRepository.save(report);

        List<ReviewRisk> risks = mapRisks(saved.getId(), asList(agentReport.get("risks")));
        if (!risks.isEmpty()) {
            reviewRiskRepository.saveAll(risks);
        }

        List<ReviewFinding> findings = mapFindings(saved.getId(), asList(agentReport.get("insufficientInfoFindings")));
        if (!findings.isEmpty()) {
            reviewFindingRepository.saveAll(findings);
        }

        saved.setRisks(risks);
        saved.setFindings(findings);
        return saved;
    }

    @Transactional(readOnly = true)
    public ReviewReport getReport(UUID sessionId, String userId) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getStatus() != ReviewStatus.COMPLETE) {
            throw new ResourceNotFoundException("Review report is not available until the session is complete");
        }

        ReviewReport report = reviewReportRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Review report not found"));

        report.setFindings(reviewFindingRepository.findByReportId(report.getId()));
        report.setRisks(reviewRiskRepository.findByReportId(report.getId()));
        return report;
    }

    private OverallRating toOverallRating(String value) {
        if (value == null || value.isBlank()) {
            return OverallRating.NEEDS_REWORK;
        }
        try {
            return OverallRating.valueOf(value);
        } catch (IllegalArgumentException ignored) {
            return OverallRating.NEEDS_REWORK;
        }
    }

    private JsonNode toJson(Object value) {
        return objectMapper.valueToTree(value);
    }

    private String asText(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> asList(Object value) {
        if (value instanceof List<?> list) {
            return list.stream()
                    .filter(Map.class::isInstance)
                    .map(item -> (Map<String, Object>) item)
                    .toList();
        }
        return List.of();
    }

    private List<ReviewRisk> mapRisks(UUID reportId, List<Map<String, Object>> riskPayload) {
        List<ReviewRisk> risks = new ArrayList<>();
        for (Map<String, Object> rawRisk : riskPayload) {
            ReviewRisk risk = new ReviewRisk();
            risk.setId(UUID.randomUUID());
            risk.setReportId(reportId);
            risk.setTitle(asText(rawRisk.get("title")));
            risk.setDescription(asText(rawRisk.get("description")));
            risk.setSeverity(defaultText(rawRisk.get("severity"), "MEDIUM"));
            risk.setLikelihood(defaultText(rawRisk.get("likelihood"), "MEDIUM"));
            risk.setAffectedArea(defaultText(rawRisk.get("affected_area"), asText(rawRisk.get("area"))));
            risk.setMitigationStrategy(defaultText(rawRisk.get("mitigation_strategy"), asText(rawRisk.get("mitigation"))));
            risk.setFrameworkReference(asText(rawRisk.get("framework_reference")));
            risks.add(risk);
        }
        return risks;
    }

    private List<ReviewFinding> mapFindings(UUID reportId, List<Map<String, Object>> findingPayload) {
        List<ReviewFinding> findings = new ArrayList<>();
        for (Map<String, Object> rawFinding : findingPayload) {
            ReviewFinding finding = new ReviewFinding();
            finding.setId(UUID.randomUUID());
            finding.setReportId(reportId);
            finding.setFindingType("INSUFFICIENT_INFORMATION");
            finding.setCategory(asText(rawFinding.get("category")));
            finding.setTitle(defaultText(rawFinding.get("title"), "Insufficient information"));
            finding.setDescription(defaultText(rawFinding.get("description"), "Required evidence was not provided."));
            finding.setEvidence(asText(rawFinding.get("evidence")));
            finding.setFrameworkReference(asText(rawFinding.get("framework_reference")));
            finding.setSeverity(defaultText(rawFinding.get("severity"), "MEDIUM"));
            findings.add(finding);
        }
        return findings;
    }

    private String defaultText(Object value, String fallback) {
        String text = asText(value);
        if (text == null || text.isBlank()) {
            return fallback;
        }
        return text;
    }
}
