package com.memoria.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.memoria.api.client.ArchonMemoriaClient;
import com.memoria.api.client.LensMemoriaClient;
import com.memoria.api.client.SpecWeaverMemoriaClient;
import com.memoria.api.domain.model.DistillationJob;
import com.memoria.api.domain.model.DistillationJobStatus;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.repository.DistillationJobRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class BatchDistillationServiceTest {

    @Mock private ProjectRepository projectRepository;
    @Mock private ProjectSessionLinkRepository sessionLinkRepository;
    @Mock private DistillationJobRepository distillationJobRepository;
    @Mock private DistillationService distillationService;
    @Mock private ArchonMemoriaClient archonClient;
    @Mock private SpecWeaverMemoriaClient specweaverClient;
    @Mock private LensMemoriaClient lensClient;

    private BatchDistillationService service;
    private UUID projectId;
    private Project project;

    @BeforeEach
    void setUp() {
        service = new BatchDistillationService(
                projectRepository,
                sessionLinkRepository,
                distillationJobRepository,
                distillationService,
                archonClient,
                specweaverClient,
                lensClient,
                new ObjectMapper().findAndRegisterModules());

        projectId = UUID.randomUUID();
        project = Project.builder().id(projectId).name("Test Project").build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(projectRepository.getReferenceById(projectId)).thenReturn(project);
        when(distillationJobRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
    }

    @Test
    void distillAllLinkedSessions_noLinkedSessions_returnsEmptyCompleteJob() {
        when(sessionLinkRepository.findByProjectId(projectId)).thenReturn(List.of());

        DistillationJob job = service.distillAllLinkedSessions(projectId);

        assertThat(job.getStatus()).isEqualTo(DistillationJobStatus.COMPLETE);
        assertThat(job.getSessionCount()).isEqualTo(0);
        assertThat(job.getTotalPersisted()).isEqualTo(0);
    }

    @Test
    void distillAllLinkedSessions_allSucceed_returnsCompleteJob() {
        UUID sessionId = UUID.randomUUID();
        ProjectSessionLink link = ProjectSessionLink.builder()
                .id(UUID.randomUUID())
                .project(project)
                .pillar(Pillar.ARCHON)
                .sessionId(sessionId)
                .linkedAt(LocalDateTime.now())
                .build();
        when(sessionLinkRepository.findByProjectId(projectId)).thenReturn(List.of(link));
        when(archonClient.getConversationOutput(sessionId)).thenReturn(Optional.of(Map.of("content", "test")));
        when(distillationService.distillLinkedSession(any())).thenReturn(
                new DistillSessionResponse(projectId, sessionId, 3, 2, 1, List.of(), "ok"));

        DistillationJob job = service.distillAllLinkedSessions(projectId);

        assertThat(job.getStatus()).isEqualTo(DistillationJobStatus.COMPLETE);
        assertThat(job.getTotalCandidates()).isEqualTo(3);
        assertThat(job.getTotalPersisted()).isEqualTo(2);
        assertThat(job.getTotalSuperseded()).isEqualTo(1);
    }

    @Test
    void distillAllLinkedSessions_oneFailsOneSucceeds_returnsPartialJob() {
        UUID sessionId1 = UUID.randomUUID();
        UUID sessionId2 = UUID.randomUUID();
        ProjectSessionLink link1 = ProjectSessionLink.builder()
                .id(UUID.randomUUID()).project(project).pillar(Pillar.ARCHON)
                .sessionId(sessionId1).linkedAt(LocalDateTime.now()).build();
        ProjectSessionLink link2 = ProjectSessionLink.builder()
                .id(UUID.randomUUID()).project(project).pillar(Pillar.SPECWEAVER)
                .sessionId(sessionId2).linkedAt(LocalDateTime.now()).build();

        when(sessionLinkRepository.findByProjectId(projectId)).thenReturn(List.of(link1, link2));
        when(archonClient.getConversationOutput(sessionId1)).thenReturn(Optional.of(Map.of("content", "a")));
        when(specweaverClient.getSessionPackage(sessionId2)).thenReturn(Optional.of(Map.of("content", "b")));
        when(distillationService.distillLinkedSession(any()))
                .thenReturn(new DistillSessionResponse(projectId, sessionId1, 2, 1, 0, List.of(), "ok"))
                .thenThrow(new RuntimeException("Distillation failed"));

        DistillationJob job = service.distillAllLinkedSessions(projectId);

        assertThat(job.getStatus()).isEqualTo(DistillationJobStatus.PARTIAL);
        assertThat(job.getTotalPersisted()).isEqualTo(1);
    }

    @Test
    void distillAllLinkedSessions_allFail_returnsFailedJob() {
        UUID sessionId = UUID.randomUUID();
        ProjectSessionLink link = ProjectSessionLink.builder()
                .id(UUID.randomUUID()).project(project).pillar(Pillar.LENS)
                .sessionId(sessionId).linkedAt(LocalDateTime.now()).build();

        when(sessionLinkRepository.findByProjectId(projectId)).thenReturn(List.of(link));
        when(lensClient.getReviewReport(sessionId)).thenReturn(Optional.of(Map.of("content", "c")));
        when(distillationService.distillLinkedSession(any())).thenThrow(new RuntimeException("fail"));

        DistillationJob job = service.distillAllLinkedSessions(projectId);

        assertThat(job.getStatus()).isEqualTo(DistillationJobStatus.FAILED);
        assertThat(job.getTotalPersisted()).isEqualTo(0);
    }

    @Test
    void distillAllLinkedSessions_pillarClientReturnsEmpty_recordsSkipped() {
        UUID sessionId = UUID.randomUUID();
        ProjectSessionLink link = ProjectSessionLink.builder()
                .id(UUID.randomUUID()).project(project).pillar(Pillar.ARCHON)
                .sessionId(sessionId).linkedAt(LocalDateTime.now()).build();

        when(sessionLinkRepository.findByProjectId(projectId)).thenReturn(List.of(link));
        when(archonClient.getConversationOutput(sessionId)).thenReturn(Optional.empty());

        DistillationJob job = service.distillAllLinkedSessions(projectId);

        // Skipped session counts as a failure for overall job status.
        assertThat(job.getStatus()).isEqualTo(DistillationJobStatus.FAILED);
        assertThat(job.getTotalPersisted()).isEqualTo(0);
        assertThat(job.getSessionResults()).contains("SKIPPED");
    }

    @Test
    void listJobs_returnsJobsInDescendingOrder() {
        DistillationJob job1 = DistillationJob.builder()
                .id(UUID.randomUUID()).project(project).status(DistillationJobStatus.COMPLETE)
                .sessionCount(1).totalCandidates(3).totalPersisted(2).totalSuperseded(0).totalConflicts(0)
                .sessionResults("[]").createdAt(LocalDateTime.now().minusHours(2)).build();
        DistillationJob job2 = DistillationJob.builder()
                .id(UUID.randomUUID()).project(project).status(DistillationJobStatus.PARTIAL)
                .sessionCount(2).totalCandidates(5).totalPersisted(4).totalSuperseded(1).totalConflicts(0)
                .sessionResults("[]").createdAt(LocalDateTime.now()).build();

        when(distillationJobRepository.findByProjectIdOrderByCreatedAtDesc(projectId))
                .thenReturn(List.of(job2, job1));

        List<DistillationJob> result = service.listJobs(projectId, 10);

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getStatus()).isEqualTo(DistillationJobStatus.PARTIAL);
    }
}
