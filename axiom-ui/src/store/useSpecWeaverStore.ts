import { create } from 'zustand';

import type { ArchInputPackage, Session } from '../api/specweaver';
import { ApiError } from '../api/http';
import {
  createSession as createSpecWeaverSession,
  deleteDocument as deleteSpecWeaverDocument,
  generatePackage as generateSpecWeaverPackage,
  getPackage as getSpecWeaverPackage,
  getSession as getSpecWeaverSession,
  getSessions as getSpecWeaverSessions,
  sendToArchon as sendSpecWeaverToArchon,
  updateSessionTitle as updateSpecWeaverSessionTitle,
  uploadDocument as uploadSpecWeaverDocument,
} from '../api/specweaver';

const PACKAGE_POLL_INTERVAL_MS = 5_000;
// Package generation is asynchronous in the API; cap polling so the UI does not
// keep a stale request loop alive forever after a backend failure.
const PACKAGE_POLL_ATTEMPTS = 60;

const SPECWEAVER_GENERATION_STAGES = [
  'extraction',
  'classification',
  'output_formatting',
] as const;

export type SpecWeaverGenerationStageName = (typeof SPECWEAVER_GENERATION_STAGES)[number];
export type SpecWeaverGenerationStageStatus = 'pending' | 'running' | 'complete' | 'error';

export interface SpecWeaverGenerationStage {
  name: SpecWeaverGenerationStageName;
  status: SpecWeaverGenerationStageStatus;
}

function initialGenerationStages(): SpecWeaverGenerationStage[] {
  return SPECWEAVER_GENERATION_STAGES.map((name, index) => ({
    name,
    status: index === 0 ? 'running' : 'pending',
  }));
}

function advanceGenerationStage(
  stages: SpecWeaverGenerationStage[],
): SpecWeaverGenerationStage[] {
  const currentIndex = stages.findIndex((stage) => stage.status === 'running');
  if (currentIndex < 0) {
    return stages;
  }
  if (currentIndex === stages.length - 1) {
    return stages;
  }

  return stages.map((stage, index) => {
    if (index === currentIndex) {
      return { ...stage, status: 'complete' };
    }
    if (index === currentIndex + 1) {
      return { ...stage, status: 'running' };
    }
    return stage;
  });
}

function completeGenerationStages(
  stages: SpecWeaverGenerationStage[],
): SpecWeaverGenerationStage[] {
  return stages.map((stage) => ({ ...stage, status: 'complete' }));
}

function markRunningStageError(
  stages: SpecWeaverGenerationStage[],
): SpecWeaverGenerationStage[] {
  const runningIndex = stages.findIndex((stage) => stage.status === 'running');
  if (runningIndex >= 0) {
    return stages.map((stage, index) =>
      index === runningIndex ? { ...stage, status: 'error' } : stage,
    );
  }

  // If no stage is currently running, mark the final stage as failed.
  return stages.map((stage, index) =>
    index === stages.length - 1 ? { ...stage, status: 'error' } : stage,
  );
}

interface SpecWeaverState {
  sessions: Session[];
  currentSession: Session | null;
  currentPackage: ArchInputPackage | null;
  isGenerating: boolean;
  generationStages: SpecWeaverGenerationStage[];
  isSending: boolean;
  error: string | null;
}

interface SpecWeaverActions {
  loadSessions: (token: string) => Promise<void>;
  loadSession: (token: string, sessionId: string) => Promise<void>;
  createSession: (token: string, title?: string) => Promise<Session>;
  updateSessionTitle: (token: string, sessionId: string, title: string | null) => Promise<Session>;
  uploadDocument: (
    token: string,
    sessionId: string,
    file: File | null,
    text: string | null,
    documentType: string,
    sourceLabel?: string,
  ) => Promise<void>;
  deleteDocument: (token: string, sessionId: string, documentId: string) => Promise<void>;
  generatePackage: (token: string, sessionId: string) => Promise<void>;
  sendToArchon: (
    token: string,
    sessionId: string,
  ) => Promise<string>;
  clearError: () => void;
}

export type SpecWeaverStore = SpecWeaverState & SpecWeaverActions;

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function waitForNextPoll(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, PACKAGE_POLL_INTERVAL_MS);
  });
}

function sessionHasGeneratedPackage(status: Session['status']): boolean {
  return status === 'PACKAGE_READY' || status === 'SENT_TO_ARCHON';
}

export const useSpecWeaverStore = create<SpecWeaverStore>((set, get) => ({
  sessions: [],
  currentSession: null,
  currentPackage: null,
  isGenerating: false,
  generationStages: [],
  isSending: false,
  error: null,

  loadSessions: async (token) => {
    set({ error: null });
    try {
      const sessions = await getSpecWeaverSessions(token);
      set({ sessions });
    } catch (error) {
      set({ error: messageFromError(error, 'Failed to load SpecWeaver sessions') });
    }
  },

  loadSession: async (token, sessionId) => {
    set({ error: null });
    try {
      const session = await getSpecWeaverSession(token, sessionId);
      if (sessionHasGeneratedPackage(session.status)) {
        try {
          const generatedPackage = await getSpecWeaverPackage(token, sessionId);
          set({ currentSession: session, currentPackage: generatedPackage });
        } catch {
          // The session can report PACKAGE_READY briefly before package read is available.
          set({ currentSession: session });
        }
      } else {
        set({ currentSession: session, currentPackage: null });
      }
    } catch (error) {
      const message = error instanceof ApiError && error.status === 403
        ? 'You do not have access to this SpecWeaver session.'
        : messageFromError(error, 'Failed to load SpecWeaver session');
      set({
        error: message,
        currentSession: null,
        currentPackage: null,
      });
    }
  },

  createSession: async (token, title) => {
    set({ error: null });
    try {
      const session = await createSpecWeaverSession(token, title);
      set((state) => ({
        sessions: [session, ...state.sessions],
        currentSession: session,
      }));
      return session;
    } catch (error) {
      const message = messageFromError(error, 'Failed to create SpecWeaver session');
      set({ error: message });
      throw new Error(message);
    }
  },

  updateSessionTitle: async (token, sessionId, title) => {
    set({ error: null });
    try {
      const updatedSession = await updateSpecWeaverSessionTitle(token, sessionId, title);
      set((state) => ({
        currentSession:
          state.currentSession?.id === updatedSession.id
            ? {
                ...state.currentSession,
                ...updatedSession,
                documents: state.currentSession.documents,
              }
            : state.currentSession,
        sessions: state.sessions.map((session) =>
          session.id === updatedSession.id ? { ...session, ...updatedSession } : session,
        ),
      }));
      return updatedSession;
    } catch (error) {
      const message = error instanceof ApiError && error.status === 403
        ? 'You cannot edit this session title because it belongs to another user.'
        : messageFromError(error, 'Failed to update session title');
      set({ error: message });
      throw new Error(message);
    }
  },

  uploadDocument: async (token, sessionId, file, text, documentType, sourceLabel) => {
    set({ error: null });
    try {
      await uploadSpecWeaverDocument(token, sessionId, file, text, documentType, sourceLabel);
      const session = await getSpecWeaverSession(token, sessionId);
      set({ currentSession: session });
    } catch (error) {
      const message = messageFromError(error, 'Failed to add document');
      set({ error: message });
      throw new Error(message);
    }
  },

  deleteDocument: async (token, sessionId, documentId) => {
    set({ error: null });
    try {
      await deleteSpecWeaverDocument(token, sessionId, documentId);
      const session = await getSpecWeaverSession(token, sessionId);
      set({ currentSession: session });
    } catch (error) {
      const message = messageFromError(error, 'Failed to delete document');
      set({ error: message });
      throw new Error(message);
    }
  },

  generatePackage: async (token, sessionId) => {
    set({
      isGenerating: true,
      generationStages: initialGenerationStages(),
      error: null,
    });
    try {
      let generationError: unknown = null;
      let localStageAdvances = 0;
      const generationPromise = generateSpecWeaverPackage(token, sessionId)
        .then(() => undefined)
        .catch((error) => {
          generationError = error;
        });

      // Optimistically mark the session as processing so the UI reflects that
      // generation has started even while the backend is still in-flight.
      const processingSession = await getSpecWeaverSession(token, sessionId);
      set({ currentSession: processingSession, currentPackage: null });

      let generatedPackage: ArchInputPackage | null = null;

      for (let attempt = 0; attempt < PACKAGE_POLL_ATTEMPTS; attempt += 1) {
        if (attempt > 0) await waitForNextPoll();
        if (generationError) {
          throw generationError;
        }
        try {
          generatedPackage = await getSpecWeaverPackage(token, sessionId);
          break;
        } catch {
          const refreshedSession = await getSpecWeaverSession(token, sessionId);
          set({ currentSession: refreshedSession });

          // Session status changes can be delayed because generation is handled
          // in a single backend transaction. Advance visual stages whenever the
          // package is still unavailable so the user sees steady progress.
          if (localStageAdvances < SPECWEAVER_GENERATION_STAGES.length - 1) {
            localStageAdvances += 1;
            set((state) => ({
              generationStages: advanceGenerationStage(state.generationStages),
            }));
          }

          if (sessionHasGeneratedPackage(refreshedSession.status)) {
            generatedPackage = await getSpecWeaverPackage(token, sessionId);
            break;
          }
        }
      }

      await generationPromise;
      if (generationError) {
        throw generationError;
      }

      if (!generatedPackage) {
        throw new Error('Package generation is still running. Please check again shortly.');
      }

      const session = await getSpecWeaverSession(token, sessionId);
      set((state) => ({
        currentPackage: generatedPackage,
        currentSession: session,
        generationStages: completeGenerationStages(state.generationStages),
      }));
    } catch (error) {
      const message = messageFromError(error, 'Failed to generate package');
      set((state) => ({
        error: message,
        generationStages:
          state.generationStages.length > 0
            ? markRunningStageError(state.generationStages)
            : state.generationStages,
      }));
      throw new Error(message);
    } finally {
      set({ isGenerating: false });
    }
  },

  sendToArchon: async (token, sessionId) => {
    if (get().isSending) {
      throw new Error('Send to Archon is already in progress.');
    }

    set({ isSending: true, error: null });
    try {
      const response = await sendSpecWeaverToArchon(token, sessionId);
      return response.briefText;
    } catch (error) {
      const message = messageFromError(error, 'Failed to send to Archon. Please try again.');
      set({ error: message });
      throw new Error(message);
    } finally {
      set({ isSending: false });
    }
  },

  clearError: () => set({ error: null }),
}));
