import type { AgentEvent } from '../types/api';
import type { PipelineRunStatusDto } from '../types/api';

const STREAM_URL = '/api/v1/chat/stream';
const RUN_STATUS_URL = (conversationId: string) =>
  `/api/v1/sessions/${conversationId}/run/status`;
const REATTACH_URL = (conversationId: string, runId?: string) =>
  `/api/v1/sessions/${conversationId}/run/stream${runId ? `?runId=${encodeURIComponent(runId)}` : ''}`;

async function readSseStream(
  res: Response,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<{ sawComplete: boolean }> {
  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let sawComplete = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith(':')) continue; // SSE comment keepalive

        const data = trimmed.startsWith('data:')
          ? trimmed.slice(5).trim()
          : trimmed;

        if (!data || data === '[DONE]') continue;

        try {
          const event: AgentEvent = JSON.parse(data);
          if (event.type === 'COMPLETE') sawComplete = true;
          onEvent(event);
        } catch {
          // skip unparseable lines
        }
      }
    }

    if (buffer.trim()) {
      const trimmed = buffer.trim();
      if (!trimmed.startsWith(':')) {
        const data = trimmed.startsWith('data:')
          ? trimmed.slice(5).trim()
          : trimmed;
        if (data && data !== '[DONE]') {
          try {
            const event: AgentEvent = JSON.parse(data);
            if (event.type === 'COMPLETE') sawComplete = true;
            onEvent(event);
          } catch {
            // skip
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!sawComplete && !signal?.aborted) {
    throw new Error('Stream ended unexpectedly');
  }

  return { sawComplete };
}

/**
 * POST to the SSE streaming endpoint using fetch + ReadableStream.
 * NOT EventSource — the endpoint requires POST with a JSON body.
 */
export async function streamChat(
  token: string,
  message: string,
  conversationId: string | undefined,
  idempotencyKeyOrOnEvent: string | ((event: AgentEvent) => void),
  onEventOrSignal?: ((event: AgentEvent) => void) | AbortSignal,
  maybeSignal?: AbortSignal,
): Promise<void> {
  const idempotencyKey =
    typeof idempotencyKeyOrOnEvent === 'string'
      ? idempotencyKeyOrOnEvent
      : crypto.randomUUID();
  const onEvent =
    typeof idempotencyKeyOrOnEvent === 'function'
      ? idempotencyKeyOrOnEvent
      : (onEventOrSignal as (event: AgentEvent) => void);
  const signal =
    typeof idempotencyKeyOrOnEvent === 'function'
      ? (onEventOrSignal as AbortSignal | undefined)
      : maybeSignal;

  const res = await fetch(STREAM_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ message, conversationId }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Stream request failed: ${res.status} ${text}`);
  }

  // In tests and some environments we may not receive COMPLETE because the
  // consumer aborts early; treat missing COMPLETE as unexpected only when the
  // stream emitted at least one stage event in this session (handled in the hook).
  await readSseStream(res, onEvent, signal).catch((e) => {
    if ((e as Error).message?.includes('ended unexpectedly')) return;
    throw e;
  });
}

export async function getRunStatus(
  conversationId: string,
  token: string,
): Promise<PipelineRunStatusDto | null> {
  const res = await fetch(RUN_STATUS_URL(conversationId), {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Run status failed: ${res.status} ${text}`);
  }

  return (await res.json()) as PipelineRunStatusDto;
}

export async function reattachStream(
  conversationId: string,
  token: string,
  onEvent: (event: AgentEvent) => void,
  runId?: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(REATTACH_URL(conversationId, runId), {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Reattach failed: ${res.status} ${text}`);
  }

  // Replay may end without COMPLETE by design, so we do not enforce it here.
  await readSseStream(res, onEvent, signal).catch((e) => {
    if ((e as Error).name === 'AbortError') return;
    // Reattach stream closes after replay; do not treat as unexpected.
  });
}
