package com.aiarchitect.api.service;

import org.junit.jupiter.api.Test;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

/**
 * Unit tests for PipelineRunBroadcaster.
 *
 * <p>Verifies the in-memory SSE subscriber lifecycle: registration, event publication,
 * graceful completion, and automatic cleanup on emitter completion/timeout/error.</p>
 */
class PipelineRunBroadcasterTest {

    private final PipelineRunBroadcaster broadcaster = new PipelineRunBroadcaster();

    @Test
    void register_addsEmitterToSubscriberList() {
        UUID runId = UUID.randomUUID();
        SseEmitter emitter = mock(SseEmitter.class);

        broadcaster.register(runId, emitter);

        // Publishing to the runId should reach the registered emitter
        assertThatCode(() -> broadcaster.publish(runId, "{\"type\":\"CHUNK\"}"))
                .doesNotThrowAnyException();
    }

    @Test
    void publish_sendsPayloadToAllRegisteredEmitters() throws Exception {
        UUID runId = UUID.randomUUID();
        SseEmitter emitter1 = mock(SseEmitter.class);
        SseEmitter emitter2 = mock(SseEmitter.class);

        broadcaster.register(runId, emitter1);
        broadcaster.register(runId, emitter2);
        broadcaster.publish(runId, "{\"type\":\"STAGE_START\"}");

        verify(emitter1).send(org.mockito.ArgumentMatchers.any(SseEmitter.SseEventBuilder.class));
        verify(emitter2).send(org.mockito.ArgumentMatchers.any(SseEmitter.SseEventBuilder.class));
    }

    @Test
    void publish_doesNothingWhenNoSubscribersForRunId() {
        UUID runId = UUID.randomUUID();

        // Must not throw when there are no subscribers
        assertThatCode(() -> broadcaster.publish(runId, "{\"type\":\"CHUNK\"}"))
                .doesNotThrowAnyException();
    }

    @Test
    void publish_removesEmitterWhenSendThrows() throws Exception {
        UUID runId = UUID.randomUUID();
        SseEmitter failingEmitter = mock(SseEmitter.class);
        doThrow(new IllegalStateException("emitter closed"))
                .when(failingEmitter).send(org.mockito.ArgumentMatchers.any(SseEmitter.SseEventBuilder.class));

        broadcaster.register(runId, failingEmitter);
        broadcaster.publish(runId, "{\"type\":\"CHUNK\"}");

        // After a failed send the emitter is unregistered; a second publish must not rethrow
        assertThatCode(() -> broadcaster.publish(runId, "{\"type\":\"DONE\"}"))
                .doesNotThrowAnyException();
    }

    @Test
    void complete_callsCompleteOnAllEmittersAndClearsSubscribers() throws Exception {
        UUID runId = UUID.randomUUID();
        SseEmitter emitter1 = mock(SseEmitter.class);
        SseEmitter emitter2 = mock(SseEmitter.class);

        broadcaster.register(runId, emitter1);
        broadcaster.register(runId, emitter2);
        broadcaster.complete(runId);

        verify(emitter1).complete();
        verify(emitter2).complete();

        // After complete, the subscriber list is removed; publish must be a no-op
        assertThatCode(() -> broadcaster.publish(runId, "{}"))
                .doesNotThrowAnyException();
    }

    @Test
    void complete_doesNothingWhenNoSubscribersForRunId() {
        UUID runId = UUID.randomUUID();

        assertThatCode(() -> broadcaster.complete(runId))
                .doesNotThrowAnyException();
    }

    @Test
    void complete_continuesCompletingRemainingEmittersWhenOneFails() throws Exception {
        UUID runId = UUID.randomUUID();
        SseEmitter failingEmitter = mock(SseEmitter.class);
        SseEmitter successEmitter = mock(SseEmitter.class);
        doThrow(new IllegalStateException("already closed")).when(failingEmitter).complete();

        broadcaster.register(runId, failingEmitter);
        broadcaster.register(runId, successEmitter);

        // Must not propagate the exception from the failing emitter
        assertThatCode(() -> broadcaster.complete(runId)).doesNotThrowAnyException();
        verify(successEmitter).complete();
    }

    @Test
    void unregister_removesEmitterFromSubscriberList() throws Exception {
        UUID runId = UUID.randomUUID();
        SseEmitter emitter = mock(SseEmitter.class);

        broadcaster.register(runId, emitter);
        broadcaster.unregister(runId, emitter);

        // After unregistration, publish to runId must not invoke the emitter
        broadcaster.publish(runId, "{\"type\":\"CHUNK\"}");
        verify(emitter, org.mockito.Mockito.never())
                .send(org.mockito.ArgumentMatchers.any(SseEmitter.SseEventBuilder.class));
    }

    @Test
    void unregister_doesNothingWhenRunIdNotRegistered() {
        UUID runId = UUID.randomUUID();
        SseEmitter emitter = mock(SseEmitter.class);

        // Must not throw when unregistering from a run that was never registered
        assertThatCode(() -> broadcaster.unregister(runId, emitter))
                .doesNotThrowAnyException();
    }
}
