package com.aiarchitect.api.service;

import com.aiarchitect.api.domain.model.Conversation;
import com.aiarchitect.api.domain.model.PipelineEvent;
import com.aiarchitect.api.domain.model.PipelineRun;
import com.aiarchitect.api.domain.model.PipelineRunStatus;
import com.aiarchitect.api.domain.repository.PipelineEventRepository;
import com.aiarchitect.api.domain.repository.PipelineRunRepository;
import com.aiarchitect.api.exception.DuplicatePipelineRunException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PipelineRunServiceTest {

    @Mock private PipelineRunRepository runRepository;
    @Mock private PipelineEventRepository eventRepository;

    private PipelineRunService service;

    @BeforeEach
    void setUp() {
        service = new PipelineRunService(runRepository, eventRepository);
    }

    @Test
    void createRun_returnsRunIdWhenPersistenceSucceeds() {
        Conversation conversation = Conversation.builder().id(UUID.randomUUID()).build();
        PipelineRun saved = PipelineRun.builder().id(UUID.randomUUID()).build();
        when(runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING))
                .thenReturn(Optional.empty());
        when(runRepository.save(any())).thenReturn(saved);

        Optional<UUID> runId = service.createRun(conversation, 0);

        assertTrue(runId.isPresent());
        assertEquals(saved.getId(), runId.get());
    }

    @Test
    void createRun_returnsEmptyOptionalWhenPersistenceFailsWithoutThrowing() {
        Conversation conversation = Conversation.builder().id(UUID.randomUUID()).build();
        when(runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING))
                .thenReturn(Optional.empty());
        when(runRepository.save(any())).thenThrow(new RuntimeException("db down"));

        Optional<UUID> runId = service.createRun(conversation, 0);

        assertTrue(runId.isEmpty());
    }

    @Test
    void startRun_throwsDuplicatePipelineRunExceptionWhenRunningRunExists() {
        Conversation conversation = Conversation.builder().id(UUID.randomUUID()).build();
        PipelineRun existing = PipelineRun.builder()
                .id(UUID.randomUUID())
                .conversation(conversation)
                .status(PipelineRunStatus.RUNNING)
                .build();
        when(runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING))
                .thenReturn(Optional.of(existing));

        DuplicatePipelineRunException thrown = assertThrows(
                DuplicatePipelineRunException.class,
                () -> service.startRun(conversation, 0));

        assertTrue(thrown.getMessage().contains(existing.getId().toString()));
        verify(runRepository, never()).save(any());
    }

    @Test
    void startRun_succeedsWhenNoRunningRunExists() {
        Conversation conversation = Conversation.builder().id(UUID.randomUUID()).build();
        PipelineRun saved = PipelineRun.builder().id(UUID.randomUUID()).build();
        when(runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING))
                .thenReturn(Optional.empty());
        when(runRepository.save(any())).thenReturn(saved);

        PipelineRun result = service.startRun(conversation, 1);

        assertEquals(saved.getId(), result.getId());
        verify(runRepository).save(any(PipelineRun.class));
    }

    @Test
    void startRun_succeedsWhenCompletedRunExistsForSameConversation() {
        Conversation conversation = Conversation.builder().id(UUID.randomUUID()).build();
        PipelineRun saved = PipelineRun.builder().id(UUID.randomUUID()).build();
        when(runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING))
                .thenReturn(Optional.empty());
        when(runRepository.save(any())).thenReturn(saved);

        PipelineRun result = service.startRun(conversation, 2);

        assertEquals(saved.getId(), result.getId());
        verify(runRepository).findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING);
    }

    @Test
    void appendEvent_savesEventWithCorrectSequenceNumber() {
        UUID runId = UUID.randomUUID();
        when(eventRepository.countByRunId(runId)).thenReturn(5);
        when(runRepository.getReferenceById(runId)).thenReturn(PipelineRun.builder().id(runId).build());

        service.appendEvent(runId, "STAGE_COMPLETE", "stage", "{\"x\":1}");

        ArgumentCaptor<PipelineEvent> captor = ArgumentCaptor.forClass(PipelineEvent.class);
        verify(eventRepository).save(captor.capture());
        assertEquals(5, captor.getValue().getSequenceNum());
        assertEquals("STAGE_COMPLETE", captor.getValue().getEventType());
    }

    @Test
    void appendEvent_handlesPersistenceFailureWithoutThrowing() {
        UUID runId = UUID.randomUUID();
        when(eventRepository.countByRunId(runId)).thenThrow(new RuntimeException("db down"));

        assertDoesNotThrow(() -> service.appendEvent(runId, "CHUNK", null, "{}"));
    }

    @Test
    void completeRun_setsStatusCompletedWhenHasGapsFalse() {
        UUID runId = UUID.randomUUID();
        PipelineRun run = PipelineRun.builder().id(runId).status(PipelineRunStatus.RUNNING).build();
        when(runRepository.findById(runId)).thenReturn(Optional.of(run));

        service.completeRun(runId, 80, "high", false, null, 10, new BigDecimal("0.1234"));

        assertEquals(PipelineRunStatus.COMPLETED, run.getStatus());
        assertNotNull(run.getCompletedAt());
    }

    @Test
    void completeRun_setsStatusCompletedWithGapsWhenHasGapsTrue() {
        UUID runId = UUID.randomUUID();
        PipelineRun run = PipelineRun.builder().id(runId).status(PipelineRunStatus.RUNNING).build();
        when(runRepository.findById(runId)).thenReturn(Optional.of(run));

        service.completeRun(runId, 80, "high", true, "gap", null, null);

        assertEquals(PipelineRunStatus.COMPLETED_WITH_GAPS, run.getStatus());
        assertEquals("gap", run.getGapSummary());
    }

    @Test
    void failRun_setsStatusFailedWithErrorDetails() {
        UUID runId = UUID.randomUUID();
        PipelineRun run = PipelineRun.builder().id(runId).status(PipelineRunStatus.RUNNING).build();
        when(runRepository.findById(runId)).thenReturn(Optional.of(run));

        service.failRun(runId, "stage", "boom");

        assertEquals(PipelineRunStatus.FAILED, run.getStatus());
        assertEquals("stage", run.getErrorStage());
        assertEquals("boom", run.getErrorMessage());
    }

    @Test
    void getEvents_returnsEventsInSequenceOrder() {
        UUID runId = UUID.randomUUID();
        List<PipelineEvent> events = List.of(
                PipelineEvent.builder().sequenceNum(0).eventType("A").build(),
                PipelineEvent.builder().sequenceNum(1).eventType("B").build()
        );
        when(eventRepository.findByRunIdOrderBySequenceNumAsc(runId)).thenReturn(events);

        List<PipelineEvent> result = service.getEvents(runId);

        assertEquals(2, result.size());
        assertEquals("A", result.get(0).getEventType());
    }

    @Test
    void getEvents_returnsEmptyListWhenPersistenceFails() {
        UUID runId = UUID.randomUUID();
        when(eventRepository.findByRunIdOrderBySequenceNumAsc(runId)).thenThrow(new RuntimeException("db down"));

        List<PipelineEvent> result = service.getEvents(runId);

        assertTrue(result.isEmpty());
    }
}
