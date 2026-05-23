package com.aiarchitect.api.workshop;

import com.aiarchitect.api.service.ConversationService;
import com.aiarchitect.api.workshop.client.WorkshopAgentClient;
import com.aiarchitect.api.workshop.domain.model.WorkshopAttribute;
import com.aiarchitect.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopMessageRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopSessionRepository;
import com.aiarchitect.api.workshop.dto.ArchitectureImplicationDto;
import com.aiarchitect.api.workshop.dto.UtilityTreeDto;
import com.aiarchitect.api.workshop.dto.WorkshopScenarioDto;
import com.aiarchitect.api.workshop.service.WorkshopService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class WorkshopFormatterTest {

    @Mock private WorkshopSessionRepository sessionRepo;
    @Mock private WorkshopAttributeRepository attributeRepo;
    @Mock private WorkshopMessageRepository messageRepo;
    @Mock private ConversationService conversationService;
    @Mock private WorkshopAgentClient workshopAgentClient;

    @InjectMocks private WorkshopService service;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "objectMapper", objectMapper);
    }

    @Test
    void formatWorkshopOutputAsRequirements_includesAllQualityAttributes() {
        String output = format(List.of(
                attribute("Availability", "confirmed"),
                attribute("Recoverability", "inferred"),
                attribute("Performance", "tentative")));

        assertThat(output).contains("Availability");
        assertThat(output).contains("Recoverability");
        assertThat(output).contains("Performance");
    }

    @Test
    void formatWorkshopOutputAsRequirements_includesDriverScenarioStimulus() {
        String output = format(List.of(attribute("Safety", "confirmed")));

        assertThat(output).contains("Stimulus: safety signal arrives during peak load");
    }

    @Test
    void formatWorkshopOutputAsRequirements_includesDriverScenarioResponseMeasure() {
        String output = format(List.of(attribute("Safety", "confirmed")));

        assertThat(output).contains("Response measure: robots halt within 100ms");
    }

    @Test
    void formatWorkshopOutputAsRequirements_includesTradeoffTextFromMustImplications() {
        String output = format(List.of(attribute("Safety", "confirmed")));

        assertThat(output).contains("Tradeoff Hierarchy");
        assertThat(output).contains("prioritises safety over throughput");
    }

    @Test
    void formatWorkshopOutputAsRequirements_includesOpenQuestionsSection() {
        String output = format(List.of(attribute("Safety", "confirmed")));

        assertThat(output).contains("# Open Questions");
        assertThat(output).contains("What is the maximum outage duration?");
    }

    @Test
    void formatWorkshopOutputAsRequirements_excludesConsensusProtocol() {
        String output = formatWithMechanismImplication("consensus protocol");

        assertThat(output).doesNotContain("consensus protocol");
    }

    @Test
    void formatWorkshopOutputAsRequirements_excludesCircuitBreaker() {
        String output = formatWithMechanismImplication("circuit breaker");

        assertThat(output).doesNotContain("circuit breaker");
    }

    @Test
    void formatWorkshopOutputAsRequirements_excludesAsyncWorkerPool() {
        String output = formatWithMechanismImplication("async worker pool");

        assertThat(output).doesNotContain("async worker pool");
    }

    @Test
    void formatWorkshopOutputAsRequirements_matchesWarehouseRoboticsSmokeChecks() {
        String output = format(List.of(
                attribute("Availability", "confirmed"),
                attribute("Recoverability", "confirmed"),
                attribute("Performance", "confirmed"),
                attribute("Safety", "confirmed"),
                attribute("Observability", "inferred"),
                attribute("Operational Continuity", "confirmed"),
                attribute("Security", "inferred"),
                attribute("Interoperability", "confirmed")));

        assertThat(output)
                .contains("Availability")
                .contains("Recoverability")
                .contains("Performance")
                .contains("Safety")
                .contains("Observability")
                .contains("Operational Continuity")
                .contains("Security")
                .contains("Interoperability")
                .contains("Stimulus:")
                .contains("Environment:")
                .contains("Response:")
                .contains("Response measure:")
                .contains("Tradeoff Hierarchy")
                .contains("prioritises safety over throughput")
                .contains("Open Questions")
                .doesNotContain("async worker pool")
                .doesNotContain("consensus protocol")
                .doesNotContain("circuit breaker")
                .doesNotContain("event sourcing")
                .doesNotContain("saga");
    }

    @Test
    void formatWorkshopOutputAsRequirements_neverRepeatsDriverInSupportingScenarios() {
        String output = ReflectionTestUtils.invokeMethod(
                service,
                "formatWorkshopOutputAsRequirements",
                "Warehouse Robotics",
                List.of(attribute("Safety", "confirmed")),
                List.of(requirementImplication()),
                utilityTree(),
                List.of(driverScenario()),
                List.of());

        assertThat(output).contains("## [Driver] Collision prevention under peak load");
        assertThat(output).doesNotContain("## Collision prevention under peak load");
    }

    @Test
    void formatWorkshopOutputAsRequirements_groupsOpenQuestionsByImpact() throws Exception {
        String output = ReflectionTestUtils.invokeMethod(
                service,
                "formatWorkshopOutputAsRequirements",
                "Warehouse Robotics",
                List.of(attribute("Safety", "confirmed")),
                List.of(requirementImplication()),
                utilityTree(),
                List.of(driverScenario()),
                List.of(openQuestion(
                        "What is the uptime target?",
                        "critical",
                        "blocks_attribute_confirmation")));

        assertThat(output)
                .contains("## Blocking")
                .contains("[CRITICAL] What is the uptime target?");
    }

    @Test
    void formatWorkshopOutputAsRequirements_requirementLabelsIncludeClassification() {
        String output = format(List.of(attribute("Safety", "confirmed")));

        assertThat(output).contains("[QUALITY CONSTRAINT] safety");
    }

    private String format(List<WorkshopAttribute> attributes) {
        return ReflectionTestUtils.invokeMethod(
                service,
                "formatWorkshopOutputAsRequirements",
                "Warehouse Robotics",
                attributes,
                List.of(requirementImplication()),
                utilityTree(),
                List.of(driverScenario()),
                List.of("What is the maximum outage duration?"));
    }

    private String formatWithMechanismImplication(String mechanism) {
        return ReflectionTestUtils.invokeMethod(
                service,
                "formatWorkshopOutputAsRequirements",
                "Warehouse Robotics",
                List.of(attribute("Safety", "confirmed")),
                List.of(mechanismImplication(mechanism)),
                utilityTree(),
                List.of(driverScenario()),
                List.of());
    }

    private WorkshopAttribute attribute(String name, String confidence) {
        return WorkshopAttribute.builder()
                .attributeId("QA-" + name)
                .name(name)
                .category(name.toLowerCase())
                .importance("high")
                .confidence(confidence)
                .description(name + " requirement")
                .scenarioJson("""
                        {
                          "stimulus": "a peak fulfilment load occurs",
                          "response": "continue processing safe assignments",
                          "response_measure": "p95 assignment latency under 500ms"
                        }
                        """)
                .evidenceQuotes("[\"" + name + " matters during peak load\"]")
                .openQuestions("[\"How strict is " + name + "?\"]")
                .build();
    }

    private ArchitectureImplicationDto requirementImplication() {
        return new ArchitectureImplicationDto(
                "IMP-001",
                "SC-004",
                "Collision prevention under peak load",
                "Because safety signals arrive during peak load, robot movement must halt within 100ms.",
                "Tradeoff: this requirement prioritises safety over throughput.",
                List.of("Safety", "Performance"),
                "safety",
                "quality_constraint",
                "must",
                "robots halt within 100ms");
    }

    private ArchitectureImplicationDto mechanismImplication(String mechanism) {
        return new ArchitectureImplicationDto(
                "IMP-002",
                "SC-004",
                "Collision prevention under peak load",
                "Because failures occur, the architecture must include a " + mechanism + ".",
                "Tradeoff: this requirement prioritises availability over simplicity.",
                List.of("Availability"),
                "availability",
                "quality_constraint",
                "must",
                "recover within 30 seconds");
    }

    private UtilityTreeDto utilityTree() {
        return new UtilityTreeDto(3, 1, List.of("SC-004"), List.of(), "driver");
    }

    private WorkshopScenarioDto driverScenario() {
        return new WorkshopScenarioDto(
                "SC-004",
                "Collision prevention under peak load",
                "safety signal arrives during peak load",
                "robot safety controller",
                "peak fulfilment window",
                "robot fleet",
                "robots halt safely",
                "robots halt within 100ms",
                List.of("Safety", "Performance"),
                "robots must stop quickly",
                2,
                "complete");
    }

    private Object openQuestion(
            String question,
            String priority,
            String architecturalImpact) throws Exception {
        Class<?> type = Class.forName(
                "com.aiarchitect.api.workshop.service.WorkshopService$OpenQuestionForPipeline");
        var constructor = type.getDeclaredConstructor(
                String.class, String.class, String.class);
        constructor.setAccessible(true);
        return constructor.newInstance(question, priority, architecturalImpact);
    }
}
