import { useCallback, useRef } from 'react';
import { getRunStatus, reattachStream, streamChat } from '../api/chat';
import { useStore } from '../store/useStore';

/**
 * Hook that manages SSE streaming via fetch + ReadableStream.
 * Returns a `send` function that starts the stream and an `abort` function.
 */
export function useSSEStream() {
  const abortRef = useRef<AbortController | null>(null);
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);
  const runId = useStore((s) => s.runId);
  const handleEvent = useStore((s) => s.handleEvent);
  const setStreaming = useStore((s) => s.setStreaming);
  const setError = useStore((s) => s.setError);
  const setRunState = useStore((s) => s.setRunState);
  const beginUserTurn = useStore((s) => s.beginUserTurn);
  const abortStreaming = useStore((s) => s.abortStreaming);
  const startStream = useStore((s) => s.startStream);

  const send = useCallback(
    async (message: string) => {
      if (!token) {
        setError('Not authenticated');
        return;
      }
      const state = useStore.getState();
      if (state.isStreaming) {
        console.error(
          'ROUTING_GUARD: submit blocked - stream already active. ' +
            'conversationId=' + state.conversationId,
        );
        return;
      }
      const activeConversationId = state.conversationId;
      const idempotencyKey = crypto.randomUUID();

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const tryReattachActiveRun = async (): Promise<boolean> => {
        if (!activeConversationId) return false;
        try {
          const status = await getRunStatus(activeConversationId, token);
          if (!status || status.status !== 'RUNNING') return false;

          startStream(activeConversationId);
          setRunState({
            runId: status.runId,
            runStatus: status.status,
            lastStageCompleted: status.lastStageCompleted ?? null,
            canReattach: false,
          });
          // Reset stage progress so replayed events rebuild state deterministically.
          useStore.getState().clearStages();
          await reattachStream(
            activeConversationId,
            token,
            handleEvent,
            status.runId,
            controller.signal,
          );
          return true;
        } catch {
          return false;
        }
      };

      // Avoid duplicate-run collisions by attaching to an existing active run first.
      if (await tryReattachActiveRun()) {
        return;
      }

      startStream(activeConversationId);
      beginUserTurn(message);

      try {
        await streamChat(
          token,
          message,
          activeConversationId ?? undefined,
          idempotencyKey,
          handleEvent,
          controller.signal,
        );
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          const errorMessage = (err as Error).message ?? 'Stream failed';

          // Race guard: if another stream was started milliseconds earlier,
          // recover by attaching to the active run instead of surfacing an error.
          if (
            errorMessage.includes('duplicate-pipeline-run') ||
            errorMessage.includes('already active') ||
            errorMessage.includes('Stream request failed: 409')
          ) {
            const reattached = await tryReattachActiveRun();
            if (reattached) {
              setError(null);
              return;
            }
          }

          setError(errorMessage);

          // The API stream may end without a COMPLETE when a proxy disconnects.
          // Detect that case by polling durable run status.
          if (activeConversationId) {
            try {
              const status = await getRunStatus(activeConversationId, token);
              if (status && status.status === 'RUNNING') {
                setRunState({
                  runId: status.runId,
                  runStatus: status.status,
                  lastStageCompleted: status.lastStageCompleted ?? null,
                  canReattach: true,
                });
              }
            } catch (_e) {
              // Best-effort only; leave banner suppressed if status can't be retrieved.
            }
          }
        }
      } finally {
        setStreaming(false);
      }
    },
    [token, handleEvent, setError, setRunState, beginUserTurn, startStream],
  );

  const reconnect = useCallback(async () => {
    if (!token || !conversationId) {
      setError('Not authenticated');
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setRunState({ canReattach: false });
    setError(null);

    try {
      // Reset stage progress so replayed events rebuild state deterministically.
      useStore.getState().clearStages();
      await reattachStream(conversationId, token, handleEvent, runId ?? undefined, controller.signal);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message ?? 'Reconnect failed');
      }
    }
  }, [token, conversationId, handleEvent, runId, setError, setRunState]);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortStreaming();
  }, [abortStreaming]);

  return { send, abort, reconnect };
}
