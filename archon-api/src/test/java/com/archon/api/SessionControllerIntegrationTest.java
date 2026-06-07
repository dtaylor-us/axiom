package com.archon.api;

import com.archon.api.domain.model.*;
import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.domain.repository.MessageRepository;
import com.archon.api.domain.repository.PipelineEventRepository;
import com.archon.api.domain.repository.PipelineRunRepository;
import com.archon.api.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.util.UUID;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
class SessionControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @Autowired private ConversationRepository conversationRepo;
    @Autowired private MessageRepository messageRepo;
        @Autowired private PipelineRunRepository pipelineRunRepository;
        @Autowired private PipelineEventRepository pipelineEventRepository;

    private String validToken;

    @BeforeEach
    void setUp() {
        pipelineEventRepository.deleteAll();
        pipelineRunRepository.deleteAll();
        messageRepo.deleteAll();
        conversationRepo.deleteAll();
        validToken = jwtService.generateToken("test@example.com");
    }

    @Test
    void getPipelineStatus_returnsCompletedStagesForCompletedRun() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        PipelineRun run = pipelineRunRepository.save(PipelineRun.builder()
                .conversation(conv)
                .iteration(0)
                .status(PipelineRunStatus.COMPLETED)
                .lastStageCompleted("requirement_challenge")
                .governanceScore(83)
                .hasGaps(false)
                .build());

        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(0)
                .eventType("STAGE_START")
                .stageName("requirement_parsing")
                .payload("{\"type\":\"STAGE_START\",\"stage\":\"requirement_parsing\"}")
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(1)
                .eventType("STAGE_COMPLETE")
                .stageName("requirement_parsing")
                .payload("{\"type\":\"STAGE_COMPLETE\",\"stage\":\"requirement_parsing\"}")
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(2)
                .eventType("STAGE_START")
                .stageName("requirement_challenge")
                .payload("{\"type\":\"STAGE_START\",\"stage\":\"requirement_challenge\"}")
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(3)
                .eventType("STAGE_COMPLETE")
                .stageName("requirement_challenge")
                .payload("{\"type\":\"STAGE_COMPLETE\",\"stage\":\"requirement_challenge\"}")
                .build());

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/pipeline-status", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.runId").isEqualTo(run.getId().toString())
                .jsonPath("$.status").isEqualTo("COMPLETED")
                .jsonPath("$.lastStageCompleted").isEqualTo("requirement_challenge")
                .jsonPath("$.completedStages.length()").isEqualTo(2)
                .jsonPath("$.completedStages[0]").isEqualTo("requirement_parsing")
                .jsonPath("$.completedStages[1]").isEqualTo("requirement_challenge")
                .jsonPath("$.activeStage").isEmpty()
                .jsonPath("$.events.length()").isEqualTo(4)
                .jsonPath("$.governanceScore").isEqualTo(83)
                .jsonPath("$.hasGaps").isEqualTo(false);
    }

    @Test
    void getPipelineStatus_returnsRunningWithPartialEvents() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("running conv").build());

        PipelineRun run = pipelineRunRepository.save(PipelineRun.builder()
                .conversation(conv)
                .iteration(0)
                .status(PipelineRunStatus.RUNNING)
                .lastStageCompleted("requirement_parsing")
                .hasGaps(false)
                .build());

        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(0)
                .eventType("STAGE_START")
                .stageName("requirement_parsing")
                .payload("{\"type\":\"STAGE_START\",\"stage\":\"requirement_parsing\"}")
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(1)
                .eventType("STAGE_COMPLETE")
                .stageName("requirement_parsing")
                .payload("{\"type\":\"STAGE_COMPLETE\",\"stage\":\"requirement_parsing\"}")
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(2)
                .eventType("STAGE_START")
                .stageName("requirement_challenge")
                .payload("{\"type\":\"STAGE_START\",\"stage\":\"requirement_challenge\"}")
                .build());

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/pipeline-status", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.status").isEqualTo("RUNNING")
                .jsonPath("$.completedStages.length()").isEqualTo(1)
                .jsonPath("$.completedStages[0]").isEqualTo("requirement_parsing")
                .jsonPath("$.activeStage").isEqualTo("requirement_challenge")
                .jsonPath("$.events.length()").isEqualTo(3);
    }

    @Test
    void getPipelineStatus_returns404WhenNoRunExists() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/pipeline-status", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }

    @Test
    void getPipelineStatus_returns403ForOtherUsersConversation() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("someone-else@example.com").title("other conv").build());

        PipelineRun run = pipelineRunRepository.save(PipelineRun.builder()
                .conversation(conv)
                .iteration(0)
                .status(PipelineRunStatus.RUNNING)
                .build());
        pipelineEventRepository.save(PipelineEvent.builder()
                .run(run)
                .sequenceNum(0)
                .eventType("STAGE_START")
                .stageName("requirement_parsing")
                .payload("{\"type\":\"STAGE_START\",\"stage\":\"requirement_parsing\"}")
                .build());

        webTestClient.get()
                .uri("/api/v1/conversations/{id}/pipeline-status", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isForbidden();
    }

    @Test
    void getMessages_returnsMessagesInOrder() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("test conv").build());

        messageRepo.save(Message.builder()
                .conversation(conv).role(MessageRole.USER)
                .content("first message").build());
        messageRepo.save(Message.builder()
                .conversation(conv).role(MessageRole.ASSISTANT)
                .content("second message").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/messages", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(2)
                .jsonPath("$[0].content").isEqualTo("second message")
                .jsonPath("$[1].content").isEqualTo("first message");
    }

    @Test
    void getMessages_returns404ForUnknownId() {
        UUID unknownId = UUID.randomUUID();

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/messages", unknownId)
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentType("application/problem+json")
                .expectBody()
                .jsonPath("$.title").isEqualTo("Not Found")
                .jsonPath("$.status").isEqualTo(404);
    }

    @Test
    void getMessages_returns404ForOtherUsersConversation() {
        Conversation conv = conversationRepo.save(Conversation.builder()
                .userId("someone-else@example.com").title("other conv").build());

        messageRepo.save(Message.builder()
                .conversation(conv).role(MessageRole.USER)
                .content("secret").build());

        webTestClient.get()
                .uri("/api/v1/sessions/{id}/messages", conv.getId())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentType("application/problem+json")
                .expectBody()
                .jsonPath("$.title").isEqualTo("Not Found")
                .jsonPath("$.status").isEqualTo(404);
    }

    @Test
    void getMessages_returns401WithoutToken() {
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/messages", UUID.randomUUID())
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void listSessions_returnsOnlyUserSessions_mostRecentFirst() {
        conversationRepo.save(Conversation.builder()
                .userId("someone-else@example.com").title("other conv").build());

        conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("older").build());
        conversationRepo.save(Conversation.builder()
                .userId("test@example.com").title("newer").build());

        webTestClient.get()
                .uri("/api/v1/sessions")
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.length()").isEqualTo(2)
                .jsonPath("$[0].title").isEqualTo("newer")
                .jsonPath("$[1].title").isEqualTo("older");
    }

    @Test
    void unknownGovernanceRoute_returns404ProblemDetail() {
        // /risk-matrix does not exist as a mapped endpoint → NoHandlerFoundException → 404 ProblemDetail
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/risk-matrix", UUID.randomUUID())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentType("application/problem+json")
                .expectBody()
                .jsonPath("$.title").isEqualTo("Not Found")
                .jsonPath("$.status").isEqualTo(404);
    }

    @Test
    void tradeOffsRoute_returns404WhenNoArchitectureExists() {
        // Route exists but no architecture output for an unknown conversation → plain 404 (no body)
        webTestClient.get()
                .uri("/api/v1/sessions/{id}/trade-offs", UUID.randomUUID())
                .header("Authorization", "Bearer " + validToken)
                .exchange()
                .expectStatus().isNotFound();
    }
}
