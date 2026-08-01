import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamChat, getPipelineStatus, getRunStatus, reattachStream } from '../api/chat';
import type { AgentEvent } from '../types/api';

// Helper to create a ReadableStream from string chunks
function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

describe('streamChat', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('parsesSSEDataLinesAndCallsOnEvent', async () => {
    const events: AgentEvent[] = [];
    const chunks = [
      'data: {"type":"STAGE_START","stage":"requirement_parsing"}\n',
      'data: {"type":"CHUNK","content":"hello"}\n',
      'data: {"type":"COMPLETE","payload":{"conversationId":"c1"}}\n',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await streamChat('token', 'message', undefined, (e) => events.push(e));

    expect(events).toHaveLength(3);
    expect(events[0].type).toBe('STAGE_START');
    expect(events[1].type).toBe('CHUNK');
    expect(events[1].content).toBe('hello');
    expect(events[2].type).toBe('COMPLETE');
  });

  it('parsesRawNDJSONLinesWithoutDataPrefix', async () => {
    const events: AgentEvent[] = [];
    const chunks = [
      '{"type":"STAGE_START","stage":"req"}\n{"type":"COMPLETE","payload":{}}\n',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await streamChat('token', 'msg', 'conv-1', (e) => events.push(e));

    expect(events).toHaveLength(2);
  });

  it('skipsUnparseableLines', async () => {
    const events: AgentEvent[] = [];
    const chunks = [
      'data: not-json\n',
      'data: {"type":"CHUNK","content":"ok"}\n',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await streamChat('token', 'msg', undefined, (e) => events.push(e));

    expect(events).toHaveLength(1);
    expect(events[0].content).toBe('ok');
  });

  it('throwsOnNon200Response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => 'Unauthorized',
    } as unknown as Response);

    await expect(
      streamChat('bad-token', 'msg', undefined, () => {}),
    ).rejects.toThrow('401');
  });

  it('throwsWhenNoResponseBody', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: null,
    } as unknown as Response);

    await expect(
      streamChat('token', 'msg', undefined, () => {}),
    ).rejects.toThrow('No response body');
  });

  it('handlesChunkedDataSplitAcrossReads', async () => {
    const events: AgentEvent[] = [];
    // Simulate data split across two reads
    const chunks = [
      'data: {"type":"CHUNK",',
      '"content":"split"}\n',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await streamChat('token', 'msg', undefined, (e) => events.push(e));

    expect(events).toHaveLength(1);
    expect(events[0].content).toBe('split');
  });

  it('sendsPOSTWithAuthHeaderAndBody', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream([]),
    } as unknown as Response);

    await streamChat('my-jwt', 'build me a thing', 'conv-99', () => {});

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/chat/stream',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer my-jwt',
          'Idempotency-Key': expect.any(String),
        }),
        body: JSON.stringify({ message: 'build me a thing', conversationId: 'conv-99' }),
      }),
    );
  });

  it('flushesRemainingBufferAfterStreamEnds', async () => {
    const events: AgentEvent[] = [];
    // The last chunk has no trailing newline — it stays in the buffer and must be flushed.
    const chunks = [
      'data: {"type":"COMPLETE","payload":{}}\ndata: {"type":"CHUNK","content":"buffered"}',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await streamChat('token', 'msg', undefined, (e) => events.push(e));

    expect(events.some((e) => e.content === 'buffered')).toBe(true);
  });
});

describe('getRunStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returnsNullOn404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
    } as unknown as Response);

    const result = await getRunStatus('conv-1', 'tok');
    expect(result).toBeNull();
  });

  it('returnsRunStatusDtoOn200', async () => {
    const dto = { runId: 'run-1', status: 'RUNNING', lastStageCompleted: null };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => dto,
    } as unknown as Response);

    const result = await getRunStatus('conv-1', 'tok');
    expect(result).toEqual(dto);
  });

  it('throwsOnNon404ErrorResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Server error',
    } as unknown as Response);

    await expect(getRunStatus('conv-1', 'tok')).rejects.toThrow('500');
  });

  it('sendsAuthorizationHeader', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ runId: 'r1', status: 'DONE', lastStageCompleted: null }),
    } as unknown as Response);

    await getRunStatus('conv-42', 'my-jwt');
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/sessions/conv-42/run/status',
      { headers: { Authorization: 'Bearer my-jwt' } },
    );
  });
});

describe('reattachStream', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('readsSSEEventsFromReattachEndpoint', async () => {
    const events: AgentEvent[] = [];
    const chunks = [
      'data: {"type":"STAGE_START","stage":"req"}\n',
      'data: {"type":"COMPLETE","payload":{}}\n',
    ];

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream(chunks),
    } as unknown as Response);

    await reattachStream('conv-1', 'tok', (e) => events.push(e));
    expect(events.length).toBeGreaterThan(0);
    expect(events[0].type).toBe('STAGE_START');
  });

  it('throwsOnNonOkResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
      text: async () => 'Forbidden',
    } as unknown as Response);

    await expect(reattachStream('conv-1', 'tok', () => {})).rejects.toThrow('403');
  });

  it('appendsRunIdToUrlWhenProvided', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: makeStream([]),
    } as unknown as Response);

    await reattachStream('conv-1', 'tok', () => {}, 'run-xyz');
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/sessions/conv-1/run/stream?runId=run-xyz',
      expect.objectContaining({ headers: { Authorization: 'Bearer tok' } }),
    );
  });
});

describe('getPipelineStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returnsNullOn404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
    } as unknown as Response);

    const result = await getPipelineStatus('conv-1', 'tok');
    expect(result).toBeNull();
  });

  it('returnsPipelineStatusOn200', async () => {
    const dto = {
      runId: 'run-1',
      status: 'RUNNING',
      lastStageCompleted: 'requirement_parsing',
      completedStages: ['requirement_parsing'],
      activeStage: 'requirement_challenge',
      events: [],
      governanceScore: null,
      hasGaps: false,
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => dto,
    } as unknown as Response);

    const result = await getPipelineStatus('conv-1', 'tok');
    expect(result).toEqual(dto);
  });

  it('throwsOnNon404ErrorResponse', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Server error',
    } as unknown as Response);

    await expect(getPipelineStatus('conv-1', 'tok')).rejects.toThrow('500');
  });
});
