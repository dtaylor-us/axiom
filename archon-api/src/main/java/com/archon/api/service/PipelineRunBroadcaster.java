package com.archon.api.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * In-memory broadcaster for live durable run reattach.
 *
 * <p>Reattach replays persisted events, then registers an emitter to receive any
 * new events as they are forwarded in the primary stream.</p>
 */
@Service
@Slf4j
public class PipelineRunBroadcaster {

    private final Map<UUID, CopyOnWriteArrayList<SseEmitter>> subscribers = new ConcurrentHashMap<>();

    /**
     * Returns the total number of live reattach emitters.
     */
    public int activeCount() {
        return subscribers.values().stream().mapToInt(CopyOnWriteArrayList::size).sum();
    }

    public void register(UUID runId, SseEmitter emitter) {
        subscribers.computeIfAbsent(runId, _k -> new CopyOnWriteArrayList<>()).add(emitter);
        emitter.onCompletion(() -> unregister(runId, emitter));
        emitter.onTimeout(() -> unregister(runId, emitter));
        emitter.onError(e -> unregister(runId, emitter));
    }

    public void unregister(UUID runId, SseEmitter emitter) {
        CopyOnWriteArrayList<SseEmitter> list = subscribers.get(runId);
        if (list == null) return;
        list.remove(emitter);
        if (list.isEmpty()) subscribers.remove(runId);
    }

    public void publish(UUID runId, String jsonPayload) {
        CopyOnWriteArrayList<SseEmitter> list = subscribers.get(runId);
        if (list == null || list.isEmpty()) return;

        for (SseEmitter emitter : list) {
            try {
                emitter.send(SseEmitter.event().data(jsonPayload, MediaType.APPLICATION_JSON));
            } catch (Exception e) {
                unregister(runId, emitter);
            }
        }
    }

    public void complete(UUID runId) {
        CopyOnWriteArrayList<SseEmitter> list = subscribers.remove(runId);
        if (list == null) return;
        for (SseEmitter emitter : list) {
            try {
                emitter.complete();
            } catch (Exception e) {
                // ignore
            }
        }
    }
}
