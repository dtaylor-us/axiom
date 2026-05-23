import { create } from 'zustand';
import type {
  AgentEvent,
  ChatMessage,
  StageName,
  StageState,
} from '../types/api';
import { PIPELINE_STAGES as STAGES } from '../types/api';

const STORAGE_KEYS = {
  auth: 'archon.auth',
  lastConversationId: 'archon.lastConversationId',
} as const;

type PersistedAuth = { token: string; username: string };

function safeGetItem(key: string): string | null {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string) {
  try {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(key, value);
  } catch {
    // ignore storage errors (private mode, quota, etc.)
  }
}

function safeRemoveItem(key: string) {
  try {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function readPersistedAuth(): PersistedAuth | null {
  const raw = safeGetItem(STORAGE_KEYS.auth);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedAuth>;
    if (typeof parsed.token === 'string' && typeof parsed.username === 'string') {
      return { token: parsed.token, username: parsed.username };
    }
    return null;
  } catch {
    return null;
  }
}

function persistAuth(token: string, username: string) {
  safeSetItem(STORAGE_KEYS.auth, JSON.stringify({ token, username } satisfies PersistedAuth));
}

function clearPersistedAuth() {
  safeRemoveItem(STORAGE_KEYS.auth);
}

function persistConversationId(id: string | null) {
  if (!id) {
    safeRemoveItem(STORAGE_KEYS.lastConversationId);
    return;
  }
  safeSetItem(STORAGE_KEYS.lastConversationId, id);
}

/* ── Slice types ─────────────────────────────────── */

interface AuthSlice {
  token: string | null;
  username: string | null;
  setAuth: (token: string, username: string) => void;
  clearAuth: () => void;
}

interface ConversationSlice {
  conversationId: string | null;
  messages: ChatMessage[];
  streamingText: string;
  isStreaming: boolean;
  error: string | null;
  stages: StageState[];
  overrideWarning: string | null;
  /** Incremented each time a COMPLETE event is received — lets hooks re-fetch. */
  pipelineVersion: number;
  runId: string | null;
  runStatus: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'COMPLETED_WITH_GAPS' | null;
  canReattach: boolean;
  lastStageCompleted: string | null;
  setConversationId: (id: string) => void;
  loadConversation: (id: string, messages: ChatMessage[]) => void;
  setStreaming: (v: boolean) => void;
  setError: (msg: string | null) => void;
  setRunState: (state: {
    runId?: string | null;
    runStatus?: ConversationSlice['runStatus'];
    canReattach?: boolean;
    lastStageCompleted?: string | null;
  }) => void;
  beginUserTurn: (content: string) => void;
  appendChunk: (text: string) => void;
  handleEvent: (event: AgentEvent) => void;
  abortStreaming: () => void;
  clearStages: () => void;
  resetConversation: () => void;
}

export type AppStore = AuthSlice & ConversationSlice;

function initialStages(): StageState[] {
  return (STAGES as readonly StageName[]).map((name) => ({
    name,
    status: 'pending',
  }));
}

const persistedAuth = readPersistedAuth();

export const useStore = create<AppStore>((set, get) => ({
  /* ── Auth ─────────────────────────────────────── */
  token: persistedAuth?.token ?? null,
  username: persistedAuth?.username ?? null,
  setAuth: (token, username) => {
    persistAuth(token, username);
    set({ token, username });
  },
  clearAuth: () => {
    clearPersistedAuth();
    set({ token: null, username: null });
  },

  /* ── Conversation ─────────────────────────────── */
  conversationId: null,
  messages: [],
  streamingText: '',
  isStreaming: false,
  error: null,
  stages: initialStages(),
  overrideWarning: null,
  pipelineVersion: 0,
  runId: null,
  runStatus: null,
  canReattach: false,
  lastStageCompleted: null,

  setConversationId: (id) => {
    persistConversationId(id);
    set({ conversationId: id });
  },
  loadConversation: (id, messages) =>
    (persistConversationId(id),
    set({
      conversationId: id,
      messages,
      streamingText: '',
      isStreaming: false,
      error: null,
      stages: initialStages(),
      overrideWarning: null,
      runId: null,
      runStatus: null,
      canReattach: false,
      lastStageCompleted: null,
    })),
  setStreaming: (v) => set({ isStreaming: v }),
  setError: (msg) => set({ error: msg }),
  setRunState: (state) => set(state),
  beginUserTurn: (content) =>
    set((s) => ({
      messages: [...s.messages, { role: 'USER', content }],
      streamingText: '',
      error: null,
      stages: initialStages(),
      overrideWarning: null,
      canReattach: false,
      lastStageCompleted: null,
    })),
  appendChunk: (text) =>
    set((s) => ({ streamingText: s.streamingText + text })),

  abortStreaming: () =>
    set((s) => ({
      isStreaming: false,
      stages: s.stages.map((st) =>
        st.status === 'running' ? { ...st, status: 'aborted' } : st,
      ),
      messages:
        s.streamingText.trim().length > 0
          ? [...s.messages, { role: 'ASSISTANT', content: s.streamingText }]
          : s.messages,
      streamingText: '',
    })),

  clearStages: () => set({ stages: initialStages() }),

  handleEvent: (event: AgentEvent) => {
    const state = get();

    switch (event.type) {
      case 'CHUNK':
        if (event.content) {
          set({ streamingText: state.streamingText + event.content });
        }
        break;

      case 'STAGE_START':
        if (event.stage) {
          set({
            stages: state.stages.map((s) =>
              s.name === event.stage ? { ...s, status: 'running' } : s,
            ),
          });
        }
        break;

      case 'STAGE_COMPLETE':
        if (event.stage) {
          if (event.stage === 'architecture_generation') {
            const warning = (event.payload?.override_warning as string | undefined) ?? '';
            if (warning && warning.trim().length > 0) {
              set({ overrideWarning: warning });
            }
          }
          set({
            stages: state.stages.map((s) =>
              s.name === event.stage
                ? { ...s, status: 'complete', payload: event.payload }
                : s,
            ),
            lastStageCompleted: event.stage,
          });
        }
        break;

      case 'COMPLETE':
        persistConversationId(
          event.conversationId ??
            (event.payload?.conversationId as string | undefined) ??
            state.conversationId,
        );
        set((s) => ({
          isStreaming: false,
          conversationId:
            event.conversationId ??
            (event.payload?.conversationId as string) ??
            s.conversationId,
          messages:
            s.streamingText.trim().length > 0
              ? [...s.messages, { role: 'ASSISTANT', content: s.streamingText }]
              : s.messages,
          streamingText: '',
          pipelineVersion: s.pipelineVersion + 1,
          runStatus: 'COMPLETED',
          canReattach: false,
        }));
        break;

      case 'RE_ITERATE':
        // Reset stages to pending for a new iteration pass
        set({
          stages: initialStages(),
        });
        break;

      case 'RUN_CREATED':
        set({
          runId: (event.payload?.runId as string | undefined) ?? null,
          runStatus: 'RUNNING',
          canReattach: false,
        });
        break;

      case 'ERROR':
        set({
          isStreaming: false,
          error: event.content ?? 'An unknown error occurred',
          stages: state.stages.map((s) =>
            s.status === 'running' ? { ...s, status: 'error' } : s,
          ),
          runStatus: 'FAILED',
        });
        break;

      // handleEvent never throws for unknown event types
      default:
        break;
    }
  },

  resetConversation: () =>
    (persistConversationId(null),
    set({
      conversationId: null,
      messages: [],
      streamingText: '',
      isStreaming: false,
      error: null,
      stages: initialStages(),
      overrideWarning: null,
      pipelineVersion: 0,
      runId: null,
      runStatus: null,
      canReattach: false,
      lastStageCompleted: null,
    })),
}));
