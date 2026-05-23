import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store/useStore';
import type { AgentEvent } from '../types/api';

describe('useStore', () => {
  beforeEach(() => {
    // Reset store between tests
    useStore.setState({
      token: null,
      username: null,
      conversationId: null,
      streamingText: '',
      isStreaming: false,
      error: null,
      stages: useStore.getState().stages.map((s) => ({
        ...s,
        status: 'pending',
        payload: undefined,
      })),
    });
    window.localStorage.removeItem('archon.auth');
    window.localStorage.removeItem('archon.lastConversationId');
  });

  describe('auth', () => {
    it('setAuth_storesTokenAndUsername', () => {
      useStore.getState().setAuth('jwt-token', 'alice');
      const state = useStore.getState();
      expect(state.token).toBe('jwt-token');
      expect(state.username).toBe('alice');
    });

    it('clearAuth_removesTokenAndUsername', () => {
      useStore.getState().setAuth('jwt-token', 'alice');
      useStore.getState().clearAuth();
      const state = useStore.getState();
      expect(state.token).toBeNull();
      expect(state.username).toBeNull();
    });

    it('setAuth_persistsAuthToLocalStorage', () => {
      useStore.getState().setAuth('jwt-token', 'alice');
      const raw = window.localStorage.getItem('archon.auth');
      expect(raw).toContain('jwt-token');
      expect(raw).toContain('alice');
    });

    it('clearAuth_removesPersistedAuth', () => {
      useStore.getState().setAuth('jwt-token', 'alice');
      useStore.getState().clearAuth();
      expect(window.localStorage.getItem('archon.auth')).toBeNull();
    });
  });

  describe('conversation', () => {
    it('setConversationId_updatesConversationId', () => {
      useStore.getState().setConversationId('conv-123');
      expect(useStore.getState().conversationId).toBe('conv-123');
    });

    it('setConversationId_persistsLastConversationId', () => {
      useStore.getState().setConversationId('conv-123');
      expect(window.localStorage.getItem('archon.lastConversationId')).toBe('conv-123');
    });

    it('appendChunk_concatenatesText', () => {
      useStore.getState().appendChunk('hello');
      useStore.getState().appendChunk(' world');
      expect(useStore.getState().streamingText).toBe('hello world');
    });

    it('resetConversation_clearsAllConversationState', () => {
      useStore.getState().setConversationId('conv-123');
      useStore.getState().appendChunk('some text');
      useStore.getState().setStreaming(true);
      useStore.getState().setError('some error');

      useStore.getState().resetConversation();

      const state = useStore.getState();
      expect(state.conversationId).toBeNull();
      expect(state.streamingText).toBe('');
      expect(state.isStreaming).toBe(false);
      expect(state.error).toBeNull();
      expect(state.stages.every((s) => s.status === 'pending')).toBe(true);
      expect(window.localStorage.getItem('archon.lastConversationId')).toBeNull();
    });
  });

  describe('handleEvent', () => {
    it('CHUNK_appendsContentToStreamingText', () => {
      const event: AgentEvent = { type: 'CHUNK', content: 'hello' };
      useStore.getState().handleEvent(event);
      expect(useStore.getState().streamingText).toBe('hello');
    });

    it('CHUNK_withNoContent_doesNotAppend', () => {
      const event: AgentEvent = { type: 'CHUNK' };
      useStore.getState().handleEvent(event);
      expect(useStore.getState().streamingText).toBe('');
    });

    it('STAGE_START_setsStageToRunning', () => {
      const event: AgentEvent = { type: 'STAGE_START', stage: 'requirement_parsing' };
      useStore.getState().handleEvent(event);
      const stage = useStore.getState().stages.find((s) => s.name === 'requirement_parsing');
      expect(stage?.status).toBe('running');
    });

    it('STAGE_COMPLETE_setsStageToCompleteWithPayload', () => {
      const event: AgentEvent = {
        type: 'STAGE_COMPLETE',
        stage: 'conflict_analysis',
        payload: { conflict_count: 5 },
      };
      useStore.getState().handleEvent(event);
      const stage = useStore.getState().stages.find((s) => s.name === 'conflict_analysis');
      expect(stage?.status).toBe('complete');
      expect(stage?.payload).toEqual({ conflict_count: 5 });
    });

    it('COMPLETE_setsStreamingFalseAndUpdatesConversationId', () => {
      useStore.getState().setStreaming(true);
      const event: AgentEvent = {
        type: 'COMPLETE',
        conversationId: 'conv-done',
        payload: { message: 'Pipeline completed.' },
      };
      useStore.getState().handleEvent(event);
      const state = useStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.conversationId).toBe('conv-done');
    });

    it('COMPLETE_fallsBackToPayloadConversationId', () => {
      useStore.getState().setStreaming(true);
      const event: AgentEvent = {
        type: 'COMPLETE',
        payload: { conversationId: 'conv-payload' },
      };
      useStore.getState().handleEvent(event);
      expect(useStore.getState().conversationId).toBe('conv-payload');
    });

    it('ERROR_setsStreamingFalseAndRecordsError', () => {
      // Set a stage to running first
      useStore.getState().handleEvent({ type: 'STAGE_START', stage: 'scenario_modeling' });
      useStore.getState().setStreaming(true);

      const event: AgentEvent = { type: 'ERROR', content: 'Pipeline failed' };
      useStore.getState().handleEvent(event);

      const state = useStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.error).toBe('Pipeline failed');
      // Running stage should become error
      const stage = state.stages.find((s) => s.name === 'scenario_modeling');
      expect(stage?.status).toBe('error');
    });

    it('unknownEventType_doesNotThrow', () => {
      const event = { type: 'FUTURE_EVENT', payload: { foo: 'bar' } } as unknown as AgentEvent;
      expect(() => useStore.getState().handleEvent(event)).not.toThrow();
    });
  });
});
