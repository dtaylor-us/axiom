import { useEffect, useState, useRef } from 'react';
import {
  BrowserRouter,
  useLocation,
  useNavigate,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom';

import { useStore } from './store/useStore';
import { ChatView } from './views/ChatView';
import { ForgotPasswordView } from './views/ForgotPasswordView';
import { LoginView } from './views/LoginView';
import { ArchitectureView } from './views/ArchitectureView';
import { GovernanceView } from './views/GovernanceView';
import { ArchDocView } from './views/ArchDocView';
import { AxiomHomePage } from './views/AxiomHomePage';
import { ResetPasswordView } from './views/ResetPasswordView';
import { LensHomePage } from './views/lens/LensHomePage';
import { LensReviewPage } from './views/lens/LensReviewPage';
import { MemoriaHomePage, MemoriaNewProjectPage, MemoriaWorkspacePage } from './views/memoria/MemoriaHomePage';
import { WorkshopView } from './views/workshop/WorkshopView';
import { ArchonHomePage } from './views/archon/ArchonHomePage';
import { PackageDetailView } from './views/specweaver/PackageDetailView';
import { SessionListView } from './views/specweaver/SessionListView';
import { SessionView } from './views/specweaver/SessionView';
import { SpecWeaverHomePage } from './views/specweaver/SpecWeaverHomePage';
import { StageProgress } from './components/StageProgress';
import { PillarNav } from './components/PillarNav';
import { PillarIcon } from './components/PillarIcon';
import { ToastProvider, emitToast } from './components/Toast';
import { ThemeToggle } from './components/ThemeToggle';
import { getToken } from './api/auth';
import { getPipelineStatus, getRunStatus, reattachStream } from './api/chat';
import { listReviewSessions, type ReviewSession as LensReviewSession } from './api/lens';
import { getSessionMessages, listSessions } from './api/sessions';
import { listWorkshopSessions } from './api/workshop';
import type { Session as SpecWeaverSession } from './api/specweaver';
import type { AgentEvent, ChatMessage, PipelineStatusEventDto, SessionSummary } from './types/api';
import type { WorkshopSessionSummary } from './types/workshop';
import { useSpecWeaverStore } from './store/useSpecWeaverStore';

type View = 'home' | 'chat' | 'architecture' | 'governance' | 'workshop' | 'specweaver' | 'archdoc';
type Pillar = 'axiom' | 'archon' | 'specweaver' | 'lens' | 'memoria';

interface MobileBottomNavItem {
  id: string;
  label: string;
  icon: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}

const STORAGE_KEYS = {
  lastView: 'archon.lastView',
  lastConversationId: 'archon.lastConversationId',
} as const;

const CONVERSATION_HYDRATION_RETRY_ATTEMPTS = 5;
const CONVERSATION_HYDRATION_RETRY_DELAY_MS = 400;

function getCurrentPillar(pathname: string): Pillar {
  if (pathname.startsWith('/specweaver')) return 'specweaver';
  if (pathname.startsWith('/lens')) return 'lens';
  if (pathname.startsWith('/memoria')) return 'memoria';
  if (pathname === '/') return 'axiom';
  return 'archon';
}

function getPillarTitle(pathname: string): string {
  const pillar = getCurrentPillar(pathname);
  if (pillar === 'specweaver') return 'SpecWeaver — Requirements Intelligence | Axiom';
  if (pillar === 'archon') return 'Archon — Architecture Reasoning | Axiom';
  if (pillar === 'lens') return 'Lens — Architecture Review Intelligence | Axiom';
  if (pillar === 'memoria') return 'Memoria — Project Memory | Axiom';
  return 'Axiom — Architecture Intelligence Platform';
}

function getPillarFavicon(pillar: Pillar): string {
  const iconMap: Record<typeof pillar, { stroke: string; path: string }> = {
    axiom: {
      stroke: '%237B2FBE',
      path: 'M12 3l8 4v10l-8 4-8-4V7l8-4 M12 7l4 2v6l-4 2-4-2V9l4-2',
    },
    archon: {
      stroke: '%2310A37F',
      path: 'M4 6h16 M4 12h10 M4 18h14',
    },
    specweaver: {
      stroke: '%23118AB2',
      path: 'M7 3h7l5 5v13H7a2 2 0 01-2-2V5a2 2 0 012-2z M14 3v5h5 M9 11h6 M9 14h6 M9 17h5',
    },
    lens: {
      stroke: '%23F77F00',
      path: 'M10.5 5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 0 0 0-11m4.3 9.3L20 20M9 10.5h3m-1.5-1.5v3',
    },
    memoria: {
      stroke: '%23DF5E8D',
      path: 'M5 5.5A2.5 2.5 0 0 1 7.5 3H19v15H7.5A2.5 2.5 0 0 0 5 20.5z M5 5.5v15M9 7h6M9 11h6M9 15h4',
    },
  };

  const { stroke, path } = iconMap[pillar];

  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='${stroke}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='${path}'/%3E%3C/svg%3E`;
}

function getSidebarPillarClass(pillar: Pillar): string {
  return `sidebar-pillar-active--${pillar}`;
}

function getActiveSidebarItemClass(pillar: Pillar): string {
  return `${getSidebarPillarClass(pillar)} sidebar-active-item`;
}

function getActiveSidebarNavClass(pillar: Pillar): string {
  return `${getSidebarPillarClass(pillar)} sidebar-active-nav`;
}

function getActiveSidebarDotClass(pillar: Pillar): string {
  return `${getSidebarPillarClass(pillar)} sidebar-active-dot`;
}

function getConversationIdFromPath(pathname: string): string | null {
  if (pathname.startsWith('/archon/conversations/')) {
    const value = pathname.split('/').filter(Boolean)[2];
    return value || null;
  }
  if (pathname.startsWith('/conversations/')) {
    const value = pathname.split('/').filter(Boolean)[1];
    return value || null;
  }
  return null;
}

async function getHydratedConversationMessages(
  conversationId: string,
  token: string,
): Promise<ChatMessage[]> {
  let lastMessages: ChatMessage[] = [];

  for (let attempt = 0; attempt < CONVERSATION_HYDRATION_RETRY_ATTEMPTS; attempt += 1) {
    const messages = await getSessionMessages(conversationId, token);
    lastMessages = messages;

    if (messages.length > 0) {
      return messages;
    }

    if (attempt < CONVERSATION_HYDRATION_RETRY_ATTEMPTS - 1) {
      await new Promise((resolve) => window.setTimeout(resolve, CONVERSATION_HYDRATION_RETRY_DELAY_MS));
    }
  }

  return lastMessages;
}

function parsePipelineEventPayload(payload: string | null): Record<string, unknown> | undefined {
  if (!payload) return undefined;
  try {
    const parsed = JSON.parse(payload) as Record<string, unknown>;
    return parsed.payload as Record<string, unknown> | undefined;
  } catch {
    return undefined;
  }
}

function toAgentEvent(event: PipelineStatusEventDto): AgentEvent {
  return {
    type: event.type as AgentEvent['type'],
    stage: event.stage ?? undefined,
    payload: parsePipelineEventPayload(event.payload),
  };
}

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
    // ignore storage errors
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

function readLastView(): View | null {
  const raw = safeGetItem(STORAGE_KEYS.lastView);
  if (raw === 'home' || raw === 'chat' || raw === 'architecture' || raw === 'governance' || raw === 'workshop' || raw === 'specweaver' || raw === 'archdoc') return raw;
  return null;
}

const NAV_ITEMS: { key: View; label: string; icon: string }[] = [
  {
    key: 'home',
    label: 'Home',
    icon: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2h-4v-7H9v7H5a2 2 0 0 1-2-2z',
  },
  {
    key: 'chat',
    label: 'Chat',
    icon: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z',
  },
  {
    key: 'architecture',
    label: 'Architecture',
    icon: 'M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11',
  },
  {
    key: 'governance',
    label: 'Governance',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  },
  {
    key: 'archdoc' as View,
    label: 'Arch Docs',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    key: 'workshop' as View,
    label: 'Workshop',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M12 12h.01M8 12h.01M16 12h.01',
  },
];

const MOBILE_ICON_PATHS = {
  home: NAV_ITEMS[0].icon,
  sessions: 'M4 6h16M4 12h16M4 18h10',
  package: 'M6 4h9l5 5v11a1 1 0 01-1 1H6a2 2 0 01-2-2V6a2 2 0 012-2zm8 1v4h4',
  plus: 'M12 5v14M5 12h14',
  review: 'M9 11l2 2 4-4M7 3h10a2 2 0 012 2v14l-3-2-3 2-3-2-3 2V5a2 2 0 012-2z',
} as const;

const SPECWEAVER_STATUS_LABELS: Record<SpecWeaverSession['status'], string> = {
  ACTIVE: 'Active',
  PROCESSING: 'Processing',
  PACKAGE_READY: 'Package Ready',
  SENT_TO_ARCHON: 'Sent to Archon',
};

function getSpecWeaverSessionId(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(Boolean);
  if (pathParts[0] !== 'specweaver') return null;
  if (pathParts[1] !== 'sessions') return null;
  if (!pathParts[2]) return null;
  return pathParts[2];
}

function getSpecWeaverSessionTitle(session: SpecWeaverSession): string {
  return session.title?.trim() ? session.title : 'Untitled session';
}

function getLensSessionId(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(Boolean);
  if (pathParts[0] !== 'lens') return null;
  if (pathParts[1] !== 'sessions') return null;
  if (!pathParts[2]) return null;
  return pathParts[2];
}

function AppContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const token = useStore((s) => s.token);
  const username = useStore((s) => s.username);
  const setAuth = useStore((s) => s.setAuth);
  const clearAuth = useStore((s) => s.clearAuth);
  const conversationId = useStore((s) => s.conversationId);
  const stages = useStore((s) => s.stages);
  const setRunState = useStore((s) => s.setRunState);
  const isStreaming = useStore((s) => s.isStreaming);
  const resetConversation = useStore((s) => s.resetConversation);
  const clearStages = useStore((s) => s.clearStages);
  const loadConversation = useStore((s) => s.loadConversation);
  const setConversationId = useStore((s) => s.setConversationId);
  const setWorkshopSeed = useStore((s) => s.setWorkshopSeed);
  const handleEvent = useStore((s) => s.handleEvent);
  const setStreaming = useStore((s) => s.setStreaming);
  const specWeaverSessions = useSpecWeaverStore((s) => s.sessions);
  const loadSpecWeaverSessions = useSpecWeaverStore((s) => s.loadSessions);
  const createSpecWeaverSession = useSpecWeaverStore((s) => s.createSession);
  const [activeView, setActiveViewState] = useState<View>(() =>
    window.location.pathname.startsWith('/specweaver') ? 'specweaver' : readLastView() ?? 'home',
  );
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [workshopSessions, setWorkshopSessions] = useState<WorkshopSessionSummary[]>([]);
  const [workshopSessionsLoading, setWorkshopSessionsLoading] = useState(false);
  const [workshopSessionsError, setWorkshopSessionsError] = useState<string | null>(null);
  const [lensSessions, setLensSessions] = useState<LensReviewSession[]>([]);
  const [lensSessionsLoading, setLensSessionsLoading] = useState(false);
  const [lensSessionsError, setLensSessionsError] = useState<string | null>(null);
  const [selectedWorkshopSessionId, setSelectedWorkshopSessionId] = useState<string | null>(null);
  const [workshopRefreshKey, setWorkshopRefreshKey] = useState(0);
  const [newWorkshopKey, setNewWorkshopKey] = useState(0);
  const [specWeaverSessionsLoading, setSpecWeaverSessionsLoading] = useState(false);
  const [specWeaverSessionsError, setSpecWeaverSessionsError] = useState<string | null>(null);
  const [isCreatingSpecWeaverSession, setIsCreatingSpecWeaverSession] = useState(false);
  const [isRehydratingAuth, setIsRehydratingAuth] = useState(() => !!username && !token);

  const hasConversation = !!conversationId;
  const allStagesDone = stages.every((s) => s.status === 'complete' || s.status === 'error' || s.status === 'aborted');
  const wasAborted = !isStreaming && stages.some((s) => s.status === 'aborted');
  const hasActiveStages = stages.some((s) => s.status !== 'pending') && (isStreaming || !allStagesDone || wasAborted);

  /* Auto-dismiss the pipeline panel 3 s after abort or all stages done */
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initializedPipelineRunRef = useRef<string | null>(null);
  const consumedSpecWeaverPrefillRef = useRef<string | null>(null);

  const setActiveView = (v: View) => {
    setActiveViewState(v);
    safeSetItem(STORAGE_KEYS.lastView, v);
  };

  const isPlatformHomeRoute = location.pathname === '/';
  const isSpecWeaverRoute = location.pathname.startsWith('/specweaver');
  const isLensRoute = location.pathname.startsWith('/lens');
  const isMemoriaRoute = location.pathname.startsWith('/memoria');
  const isArchonHomeRoute = location.pathname === '/archon';
  const isArchonChatRoute = location.pathname === '/archon/chat';
  const isConversationRoute = !!getConversationIdFromPath(location.pathname);
  const activeSidebarPillar: Pillar = isSpecWeaverRoute ? 'specweaver' : isLensRoute ? 'lens' : isMemoriaRoute ? 'memoria' : 'archon';
  const activeSidebarItemClass = getActiveSidebarItemClass(activeSidebarPillar);
  const activeSidebarNavClass = getActiveSidebarNavClass(activeSidebarPillar);
  const activeSidebarDotClass = getActiveSidebarDotClass(activeSidebarPillar);
  const activeSpecWeaverSessionId = isSpecWeaverRoute
    ? getSpecWeaverSessionId(location.pathname)
    : null;
  const activeLensSessionId = isLensRoute ? getLensSessionId(location.pathname) : null;

  useEffect(() => {
    document.title = getPillarTitle(location.pathname);

    const faviconHref = getPillarFavicon(getCurrentPillar(location.pathname));
    let link = document.querySelector("link[rel='icon']") as HTMLLinkElement | null;
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = faviconHref;
  }, [location.pathname]);

  const loadSpecWeaverSessionHistory = async () => {
    if (!token) return;
    setSpecWeaverSessionsLoading(true);
    setSpecWeaverSessionsError(null);
    try {
      await loadSpecWeaverSessions(token);
    } catch (error) {
      setSpecWeaverSessionsError((error as Error).message ?? 'Failed to load SpecWeaver sessions');
    } finally {
      setSpecWeaverSessionsLoading(false);
    }
  };

  const handleCreateSpecWeaverSession = async () => {
    if (!token || isCreatingSpecWeaverSession) return;
    setIsCreatingSpecWeaverSession(true);
    setSpecWeaverSessionsError(null);
    try {
      const session = await createSpecWeaverSession(token, undefined);
      await loadSpecWeaverSessionHistory();
      navigate(`/specweaver/sessions/${session.id}`);
      setMobileDrawerOpen(false);
    } catch (error) {
      setSpecWeaverSessionsError((error as Error).message ?? 'Failed to create SpecWeaver session');
    } finally {
      setIsCreatingSpecWeaverSession(false);
    }
  };

  const handleOpenSpecWeaverSession = (sessionId: string) => {
    navigate(`/specweaver/sessions/${sessionId}`);
    setMobileDrawerOpen(false);
  };

  const handleCreateLensSession = () => {
    navigate('/lens/new');
    setMobileDrawerOpen(false);
  };

  const handleOpenLensSession = (sessionId: string) => {
    navigate(`/lens/sessions/${sessionId}`);
    setMobileDrawerOpen(false);
  };

  // Rehydrate token on hard refresh using persisted username. Token itself is
  // never stored in localStorage (ADL-023), but we can request a fresh one.
  useEffect(() => {
    let cancelled = false;
    if (token || !username) {
      setIsRehydratingAuth(false);
      return;
    }

    setIsRehydratingAuth(true);
    getToken(username)
      .then((freshToken) => {
        if (!cancelled) {
          setAuth(freshToken, username);
        }
      })
      .catch(() => {
        if (!cancelled) {
          clearAuth();
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsRehydratingAuth(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token, username, setAuth, clearAuth]);

  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    if (activeView !== 'workshop') return;

    setWorkshopSessionsLoading(true);
    setWorkshopSessionsError(null);
    listWorkshopSessions(token)
      .then((s) => {
        if (!cancelled) setWorkshopSessions(s);
      })
      .catch((err) => {
        if (!cancelled) setWorkshopSessionsError((err as Error).message ?? 'Failed to load workshops');
      })
      .finally(() => {
        if (!cancelled) setWorkshopSessionsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, activeView, workshopRefreshKey]);

  useEffect(() => {
    if (!token) return;
    if (!isSpecWeaverRoute) return;

    void loadSpecWeaverSessionHistory();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isSpecWeaverRoute]);

  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    if (!isLensRoute) return;

    setLensSessionsLoading(true);
    setLensSessionsError(null);
    listReviewSessions(token)
      .then((items) => {
        if (!cancelled) setLensSessions(items);
      })
      .catch((error) => {
        if (!cancelled) setLensSessionsError((error as Error).message ?? 'Failed to load Lens reviews');
      })
      .finally(() => {
        if (!cancelled) setLensSessionsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, isLensRoute, location.pathname]);

  // Conversation and chat URLs should render the chat shell immediately, even
  // while message hydration is still in-flight.
  useEffect(() => {
    if (!token) return;
    if (!(isArchonChatRoute || isConversationRoute)) return;
    if (activeView !== 'chat') {
      setActiveView('chat');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isArchonChatRoute, isConversationRoute, token]);

  // SpecWeaver handoff can arrive on /archon with prefill state.
  // Force chat mode so the input is immediately visible for review.
  useEffect(() => {
    const state = location.state as { prefillMessage?: string } | null;
    if (!state?.prefillMessage) return;

    // Only consume each prefill payload once. Without this guard, stale
    // location state can keep forcing Chat mode even after the user switches
    // to Architecture or Governance.
    const prefillKey = `${location.pathname}:${state.prefillMessage}`;
    if (consumedSpecWeaverPrefillRef.current === prefillKey) {
      return;
    }
    consumedSpecWeaverPrefillRef.current = prefillKey;

    if (activeView !== 'chat') {
      setActiveView('chat');
    }
  }, [activeView, location.pathname, location.state]);

  // Recover from a persisted SpecWeaver view after navigating away from
  // SpecWeaver routes, which otherwise can render an empty main panel.
  useEffect(() => {
    if (!token) return;
    if (isSpecWeaverRoute) return;
    if (isConversationRoute) return;
    if (activeView !== 'specweaver') return;

    setActiveView('chat');
  }, [activeView, isConversationRoute, isSpecWeaverRoute, token]);

  // If a conversation is open after refresh, recover durable run state so the
  // user can reconnect to an in-flight pipeline.
  useEffect(() => {
    let cancelled = false;
    if (!token || !conversationId || isStreaming) return;

    getRunStatus(conversationId, token)
      .then((status) => {
        if (cancelled || !status) return;
        if (status.status === 'RUNNING') {
          setRunState({
            runId: status.runId,
            runStatus: status.status,
            canReattach: true,
            lastStageCompleted: status.lastStageCompleted ?? null,
          });
        }
      })
      .catch(() => {
        // Best-effort only — UI still functions without durable status.
      });

    return () => {
      cancelled = true;
    };
  }, [token, conversationId, isStreaming, setRunState]);

  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    if (isStreaming) return;

    setSessionsLoading(true);
    setSessionsError(null);
    listSessions(token)
      .then((s) => {
        if (!cancelled) setSessions(s);
      })
      .catch((err) => {
        if (!cancelled) setSessionsError((err as Error).message ?? 'Failed to load history');
      })
      .finally(() => {
        if (!cancelled) setSessionsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, conversationId, isStreaming]);

  // Restore last opened conversation on page reload (auth is rehydrated in the store)
  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    if (isStreaming) return;
    if (conversationId) return;

    const lastId = safeGetItem(STORAGE_KEYS.lastConversationId);
    if (!lastId) return;

    setLoadingSessionId(lastId);
    getHydratedConversationMessages(lastId, token)
      .then((msgs) => {
        if (cancelled) return;
        loadConversation(lastId, [...msgs].reverse());
        setActiveView('chat');
      })
      .catch(() => {
        if (cancelled) return;
        safeRemoveItem(STORAGE_KEYS.lastConversationId);
      })
      .finally(() => {
        if (cancelled) return;
        setLoadingSessionId(null);
      });

    return () => {
      cancelled = true;
    };
  }, [token, isStreaming, conversationId, loadConversation]);

  useEffect(() => {
    if (!token) return;
    const pathConversationId = getConversationIdFromPath(location.pathname);
    if (!pathConversationId) return;
    if (isStreaming) return;
    if (!pathConversationId || pathConversationId === conversationId) {
      return;
    }

    setLoadingSessionId(pathConversationId);
    getHydratedConversationMessages(pathConversationId, token)
      .then((msgs) => {
        loadConversation(pathConversationId, [...msgs].reverse());
        setActiveView('chat');
      })
      .catch(() => {
        setConversationId(pathConversationId);
        setActiveView('chat');
      })
      .finally(() => setLoadingSessionId(null));
  }, [conversationId, isStreaming, loadConversation, location.pathname, setConversationId, token]);

  // Rebuild pipeline progress from persisted events immediately on mount.
  // This closes the gap where early stages finish before the client is connected.
  useEffect(() => {
    let cancelled = false;
    if (!token || !conversationId || isStreaming) return;
    if (!getConversationIdFromPath(location.pathname)) return;

    const initializePipelineProgress = async () => {
      try {
        const status = await getPipelineStatus(conversationId, token);
        if (cancelled || !status) return;

        const runKey = `${conversationId}:${status.runId}`;
        if (initializedPipelineRunRef.current === runKey) {
          return;
        }
        initializedPipelineRunRef.current = runKey;

        clearStages();
        status.events.forEach((event) => {
          handleEvent(toAgentEvent(event));
        });

        setRunState({
          runId: status.runId,
          runStatus: status.status,
          canReattach: status.status === 'RUNNING',
          lastStageCompleted: status.lastStageCompleted,
        });

        if (status.status !== 'RUNNING') {
          return;
        }

        setStreaming(true);
        await reattachStream(
          conversationId,
          token,
          (event) => {
            if (!cancelled) {
              handleEvent(event);
            }
          },
          status.runId,
        );
      } catch {
        // 404 or transient errors should not block normal chat behavior.
      } finally {
        if (!cancelled) {
          setStreaming(false);
        }
      }
    };

    void initializePipelineProgress();

    return () => {
      cancelled = true;
    };
  }, [
    clearStages,
    conversationId,
    handleEvent,
    isStreaming,
    location.pathname,
    setRunState,
    setStreaming,
    token,
  ]);

  // Without an active conversation, don't allow "empty" architecture/governance views
  useEffect(() => {
    if (!token) return;
    if (!hasConversation && (activeView === 'architecture' || activeView === 'governance' || activeView === 'archdoc')) {
      setActiveView('chat');
    }
    // workshop is always accessible — no conversation required
  }, [token, hasConversation, activeView]);

  useEffect(() => {
    if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    if (!isStreaming && allStagesDone && hasActiveStages) {
      dismissTimerRef.current = setTimeout(clearStages, 3000);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStreaming, allStagesDone, hasActiveStages]);

  const handleLoadWorkshopSession = (sessionId: string) => {
    setSelectedWorkshopSessionId(sessionId);
    setMobileDrawerOpen(false);
  };

  const handleStartNewChat = () => {
    resetConversation();
    setActiveView('chat');
    navigate('/archon/chat');
    setMobileDrawerOpen(false);
  };

  const handleNavigatePrimaryView = (view: View) => {
    if (view === 'home') {
      setActiveView('home');
      navigate('/archon');
      return;
    }
    if (view === 'chat') {
      setActiveView('chat');
      navigate('/archon/chat');
      return;
    }
    setActiveView(view);
    if (!location.pathname.startsWith('/archon') && !location.pathname.startsWith('/conversations/')) {
      navigate('/archon/chat');
    }
  };

  const handleWorkshopSessionCreated = () => {
    // Only refresh the sidebar list; do NOT change selectedWorkshopSessionId so
    // the current WorkshopView component is not remounted (which would wipe the
    // welcome message and conversation state for the session just started).
    setWorkshopRefreshKey((k) => k + 1);
  };

  const handleLoadSession = async (sessionId: string) => {
    if (!token || isStreaming) return;
    setLoadingSessionId(sessionId);
    try {
      const msgs = await getSessionMessages(sessionId, token);
      // API returns messages newest-first (DESC); reverse to oldest-first so
      // the chat view renders chronologically with the latest at the bottom.
      loadConversation(sessionId, [...msgs].reverse());
      setActiveView('chat');
      navigate(`/archon/conversations/${sessionId}`);
      setMobileDrawerOpen(false);
    } catch {
      // keep UI minimal: the view itself will surface any downstream errors
    } finally {
      setLoadingSessionId(null);
    }
  };

  // Handle session expiry fired by authFetchJson when any request returns 401
  useEffect(() => {
    const handler = () => {
      clearAuth();
      emitToast('Your session has expired. Please sign in again.', 'warning');
    };
    window.addEventListener('archon:session-expired', handler);
    return () => window.removeEventListener('archon:session-expired', handler);
  }, [clearAuth]);

  /* ---------- Not authenticated → show login ---------- */
  if (!token) {
    if (isRehydratingAuth) {
      return (
        <ToastProvider>
          <div className="flex h-dvh items-center justify-center bg-gray-50 text-gray-600" data-testid="auth-rehydrating">
            Restoring your session...
          </div>
        </ToastProvider>
      );
    }

    return (
      <ToastProvider>
        <Routes>
          <Route path="/" element={<AxiomHomePage />} />
          <Route path="/login" element={<LoginView />} />
          <Route path="/forgot-password" element={<ForgotPasswordView />} />
          <Route path="/reset-password" element={<ResetPasswordView />} />
          <Route path="*" element={<Navigate replace to="/login" />} />
        </Routes>
      </ToastProvider>
    );
  }

  const activeViewLabel =
    isPlatformHomeRoute
      ? 'Axiom'
      : isSpecWeaverRoute
      ? 'SpecWeaver'
      : isLensRoute
      ? 'Lens'
      : isMemoriaRoute
      ? 'Memoria'
      : isArchonHomeRoute
      ? 'Archon'
      : activeView === 'home'
      ? 'Home'
      : activeView === 'chat'
      ? 'Chat'
      : activeView === 'architecture'
        ? 'Architecture'
        : activeView === 'governance'
          ? 'Governance'
          : activeView === 'workshop'
            ? 'Workshop'
            : 'SpecWeaver';

  const mobileBottomNavItems: MobileBottomNavItem[] = isSpecWeaverRoute
    ? [
      {
        id: 'specweaver-home',
        label: 'Home',
        icon: MOBILE_ICON_PATHS.home,
        active: location.pathname === '/specweaver',
        onClick: () => navigate('/specweaver'),
      },
      {
        id: 'specweaver-sessions',
        label: 'Sessions',
        icon: MOBILE_ICON_PATHS.sessions,
        active: location.pathname === '/specweaver/sessions',
        onClick: () => navigate('/specweaver/sessions'),
      },
      ...(activeSpecWeaverSessionId
        ? [
          {
            id: 'specweaver-session',
            label: 'Session',
            icon: MOBILE_ICON_PATHS.sessions,
            active: location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}`,
            onClick: () => navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}`),
          },
          {
            id: 'specweaver-package',
            label: 'Package',
            icon: MOBILE_ICON_PATHS.package,
            active: location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}/package`,
            onClick: () => navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}/package`),
          },
        ]
        : []),
      {
        id: 'specweaver-new',
        label: 'New',
        icon: MOBILE_ICON_PATHS.plus,
        active: false,
        disabled: isCreatingSpecWeaverSession,
        onClick: () => {
          void handleCreateSpecWeaverSession();
        },
      },
    ]
    : isLensRoute
      ? [
        {
          id: 'lens-home',
          label: 'Home',
          icon: MOBILE_ICON_PATHS.home,
          active: location.pathname === '/lens',
          onClick: () => navigate('/lens'),
        },
        {
          id: 'lens-new',
          label: 'New',
          icon: MOBILE_ICON_PATHS.plus,
          active: location.pathname === '/lens/new',
          onClick: handleCreateLensSession,
        },
        ...(activeLensSessionId
          ? [
            {
              id: 'lens-review',
              label: 'Review',
              icon: MOBILE_ICON_PATHS.review,
              active: location.pathname === `/lens/sessions/${activeLensSessionId}`,
              onClick: () => navigate(`/lens/sessions/${activeLensSessionId}`),
            },
          ]
          : []),
      ]
      : isMemoriaRoute
        ? [
          {
            id: 'memoria-home',
            label: 'Memory',
            icon: MOBILE_ICON_PATHS.package,
            active: location.pathname === '/memoria',
            onClick: () => navigate('/memoria'),
          },
        ]
        : NAV_ITEMS.map(({ key, label, icon }) => ({
        id: key,
        label,
        icon,
        active: activeView === key,
        disabled: (key === 'architecture' || key === 'governance' || key === 'archdoc') && !hasConversation,
        onClick: () => handleNavigatePrimaryView(key),
      }));
  const mobileBottomGridClass = mobileBottomNavItems.length >= 5
    ? 'grid-cols-5'
    : mobileBottomNavItems.length === 4
      ? 'grid-cols-4'
      : mobileBottomNavItems.length === 3
        ? 'grid-cols-3'
        : 'grid-cols-2';

  return (
    <ToastProvider>
    <div className="flex h-dvh overflow-hidden" data-testid="app-shell">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-[280px] shrink-0 bg-sidebar flex-col min-h-0 overflow-hidden" data-testid="sidebar">
        <div className="border-b border-sidebar-border px-4 py-4">
          <div className="axiom-brand flex items-center gap-3">
            <div className="axiom-brand-icon shrink-0">
              <PillarIcon pillar="axiom" size={20} />
            </div>
            <div className="min-w-0">
              <div className="axiom-brand-name leading-tight">Axiom</div>
              <div className="axiom-brand-tagline text-[11px] font-medium uppercase tracking-[0.16em] text-gray-300">
                Architecture Intelligence
              </div>
            </div>
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto sidebar-scroll">
          <PillarNav />
          <div className="p-2 flex flex-col gap-1.5">
            {isMemoriaRoute ? null : isSpecWeaverRoute ? (
              <button
                onClick={() => {
                  void handleCreateSpecWeaverSession();
                }}
                disabled={isCreatingSpecWeaverSession}
                className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-2.5 text-[13px] text-gray-200 hover:bg-sidebar-hover transition-colors"
                data-testid="new-specweaver-session"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M8 3v10M3 8h10" />
                </svg>
                {isCreatingSpecWeaverSession ? 'Creating session...' : 'New session'}
              </button>
            ) : isLensRoute ? (
              <button
                onClick={handleCreateLensSession}
                className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-2.5 text-[13px] text-gray-200 hover:bg-sidebar-hover transition-colors"
                data-testid="new-lens-review"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M8 3v10M3 8h10" />
                </svg>
                New architecture review
              </button>
            ) : (
              <>
                <button
                  onClick={handleStartNewChat}
                  disabled={isStreaming}
                  className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-2.5 text-[13px] text-gray-200 hover:bg-sidebar-hover transition-colors disabled:opacity-40"
                  data-testid="new-chat"
                >
                  <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M8 3v10M3 8h10" />
                  </svg>
                  New chat
                </button>
                {activeView === 'workshop' && (
                  <button
                    onClick={() => { setSelectedWorkshopSessionId(null); setNewWorkshopKey((k) => k + 1); }}
                    className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-2.5 text-[13px] text-gray-200 hover:bg-sidebar-hover transition-colors"
                    data-testid="new-workshop"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M8 3v10M3 8h10" />
                    </svg>
                    New workshop
                  </button>
                )}
              </>
            )}
          </div>

          <nav className="flex flex-col gap-0.5 px-2 mt-1">
            {isMemoriaRoute ? (
              <button
                onClick={() => {
                  navigate('/memoria');
                  setMobileDrawerOpen(false);
                }}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${activeSidebarNavClass}`}
                data-testid="nav-memoria-memory"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H19v15H7.5A2.5 2.5 0 0 0 5 20.5z M5 5.5v15M9 7h6M9 11h6M9 15h4" />
                </svg>
                Memory workspace
              </button>
            ) : isSpecWeaverRoute ? (
              <button
                onClick={() => {
                  navigate('/specweaver/sessions');
                  setMobileDrawerOpen(false);
                }}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${activeSidebarNavClass}`}
                data-testid="nav-specweaver-sessions"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 6h16M4 12h16M4 18h10" />
                </svg>
                Sessions
              </button>
            ) : isLensRoute ? (
              <button
                onClick={() => {
                  navigate('/lens');
                  setMobileDrawerOpen(false);
                }}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${activeSidebarNavClass}`}
                data-testid="nav-lens-reviews"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.5 5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 0 0 0-11m4.3 9.3L20 20M9 10.5h3m-1.5-1.5v3" />
                </svg>
                Reviews
              </button>
            ) : (
              NAV_ITEMS.filter(({ key }) => key === 'home' || key === 'chat' || key === 'workshop').map(({ key, label, icon }) => (
                <button
                  key={key}
                  onClick={() => handleNavigatePrimaryView(key)}
                  className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${
                    activeView === key
                      ? activeSidebarNavClass
                      : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                  }`}
                  data-testid={`nav-${key}`}
                >
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d={icon} />
                  </svg>
                  {label}
                </button>
              ))
            )}
          </nav>

          {isSpecWeaverRoute && activeSpecWeaverSessionId && (
            <div className="mx-2 mt-2 rounded-lg border border-sidebar-border bg-sidebar-hover/30">
              <div className="px-3 pt-2 pb-1 flex items-center gap-1.5">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest truncate">
                  Active session
                </span>
              </div>
              <nav className="flex flex-col gap-0.5 px-1 pb-1.5">
                <button
                  onClick={() => {
                    navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}`);
                    setMobileDrawerOpen(false);
                  }}
                  className={`flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] transition-colors ${
                    location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}`
                      ? activeSidebarNavClass
                      : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                  }`}
                  data-testid="nav-specweaver-session"
                >
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 6h16M4 12h16M4 18h10" />
                  </svg>
                  Session
                </button>
                <button
                  onClick={() => {
                    navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}/package`);
                    setMobileDrawerOpen(false);
                  }}
                  className={`flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] transition-colors ${
                    location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}/package`
                      ? activeSidebarNavClass
                      : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                  }`}
                  data-testid="nav-specweaver-package"
                >
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 4h9l5 5v11a1 1 0 01-1 1H6a2 2 0 01-2-2V6a2 2 0 012-2zm8 1v4h4" />
                  </svg>
                  Package
                </button>
              </nav>
            </div>
          )}

          {!isSpecWeaverRoute && !isLensRoute && !isMemoriaRoute && hasConversation && (
            <div className="mx-2 mt-2 rounded-lg border border-sidebar-border bg-sidebar-hover/30">
              <div className="px-3 pt-2 pb-1 flex items-center gap-1.5">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest truncate">
                  Active session
                </span>
              </div>
              <nav className="flex flex-col gap-0.5 px-1 pb-1.5">
                {NAV_ITEMS.filter(({ key }) => key !== 'home' && key !== 'chat').map(({ key, label, icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveView(key)}
                    className={`flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] transition-colors ${
                      activeView === key
                        ? activeSidebarNavClass
                        : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                    }`}
                    data-testid={`nav-${key}`}
                  >
                    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d={icon} />
                    </svg>
                    {label}
                  </button>
                ))}
              </nav>
            </div>
          )}

          <div className="mt-3 px-2">
            <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest px-3 mb-1.5">
              {isMemoriaRoute ? 'Memory' : isSpecWeaverRoute ? 'Sessions' : isLensRoute ? 'Reviews' : activeView === 'workshop' ? 'Workshops' : 'History'}
            </h3>
            {isMemoriaRoute ? (
              <div className="px-3 py-2 text-[12px] text-gray-500">Project memory, ADRs, and session links</div>
            ) : isSpecWeaverRoute ? (
              specWeaverSessionsLoading ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
              ) : specWeaverSessionsError ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">{specWeaverSessionsError}</div>
              ) : specWeaverSessions.length === 0 ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">No SpecWeaver sessions yet</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {specWeaverSessions.map((session) => {
                    const active = session.id === activeSpecWeaverSessionId;
                    return (
                      <button
                        key={session.id}
                        onClick={() => handleOpenSpecWeaverSession(session.id)}
                        className={`text-left rounded-lg px-3 py-2 text-[12px] transition-colors ${
                          active
                            ? activeSidebarItemClass
                            : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                        }`}
                        title={getSpecWeaverSessionTitle(session)}
                        data-testid={`specweaver-history-${session.id}`}
                      >
                        <div className="flex items-center gap-2">
                          {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                          <span className={`truncate ${active ? 'font-medium' : ''}`}>{getSpecWeaverSessionTitle(session)}</span>
                        </div>
                        <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                          {SPECWEAVER_STATUS_LABELS[session.status]}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )
            ) : isLensRoute ? (
              lensSessionsLoading ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">Loading...</div>
              ) : lensSessionsError ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">{lensSessionsError}</div>
              ) : lensSessions.length === 0 ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">No Lens reviews yet</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {lensSessions.map((session) => {
                    const active = session.id === activeLensSessionId;
                    return (
                      <button
                        key={session.id}
                        onClick={() => handleOpenLensSession(session.id)}
                        className={`text-left rounded-lg px-3 py-2 text-[12px] transition-colors ${
                          active
                            ? activeSidebarItemClass
                            : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                        }`}
                        title={session.title}
                        data-testid={`lens-history-${session.id}`}
                      >
                        <div className="flex items-center gap-2">
                          {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                          <span className={`truncate ${active ? 'font-medium' : ''}`}>{session.title || 'Untitled review'}</span>
                        </div>
                        <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                          {session.status.replace(/_/g, ' ')}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )
            ) : activeView === 'workshop' ? (
              workshopSessionsLoading ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
              ) : workshopSessionsError ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">{workshopSessionsError}</div>
              ) : workshopSessions.length === 0 ? (
                <div className="px-3 py-2 text-[12px] text-gray-500">No workshops yet</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {workshopSessions.map((ws) => {
                    const active = ws.sessionId === selectedWorkshopSessionId;
                    return (
                      <button
                        key={ws.sessionId}
                        onClick={() => handleLoadWorkshopSession(ws.sessionId)}
                        className={`text-left rounded-lg px-3 py-2 text-[12px] transition-colors ${
                          active
                            ? activeSidebarItemClass
                            : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                        }`}
                        title={ws.systemName}
                        data-testid={`workshop-history-${ws.sessionId}`}
                      >
                        <div className="flex items-center gap-2">
                          {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                          <span className={`truncate ${active ? 'font-medium' : ''}`}>{ws.systemName}</span>
                        </div>
                        <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                          {ws.workshopPhase.replace(/_/g, ' ')}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )
            ) : sessionsLoading ? (
              <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
            ) : sessionsError ? (
              <div className="px-3 py-2 text-[12px] text-gray-500">{sessionsError}</div>
            ) : sessions.length === 0 ? (
              <div className="px-3 py-2 text-[12px] text-gray-500">No chats yet</div>
            ) : (
              <div className="flex flex-col gap-1">
                {sessions.map((s) => {
                  const active = s.id === conversationId;
                  const loading = loadingSessionId === s.id;
                  return (
                    <button
                      key={s.id}
                      onClick={() => handleLoadSession(s.id)}
                      disabled={isStreaming || loading}
                      className={`text-left rounded-lg px-3 py-2 text-[12px] transition-colors relative ${
                        active
                          ? activeSidebarItemClass
                          : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                      } ${isStreaming || loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title={s.title}
                      data-testid={`history-${s.id}`}
                    >
                      <div className="flex items-center gap-2">
                        {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                        <span className={`truncate ${active ? 'font-medium' : ''}`}>{s.title}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {!isSpecWeaverRoute && hasActiveStages && (
            <div className="mt-3 px-2 pb-2">
              <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest px-3 mb-1.5">Pipeline</h3>
              <StageProgress stages={stages} />
            </div>
          )}
        </div>

        <div className="border-t border-sidebar-border p-2">
          <div className="flex items-center gap-2.5 px-3 py-1.5 mb-1">
            <div className="w-6 h-6 shrink-0 rounded-full bg-accent/80 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">{(username ?? 'U')[0].toUpperCase()}</span>
            </div>
            <span className="text-[12px] text-gray-400 truncate">{username}</span>
          </div>
          <button
            onClick={() => {
              clearAuth();
              resetConversation();
              safeRemoveItem(STORAGE_KEYS.lastView);
              safeRemoveItem(STORAGE_KEYS.lastConversationId);
            }}
            className="flex items-center gap-2.5 w-full rounded-lg px-3 py-2 text-[13px] text-gray-400 hover:bg-sidebar-hover hover:text-gray-200 transition-colors"
            data-testid="nav-logout"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Mobile drawer overlay ── */}
      {mobileDrawerOpen && (
        <div className="md:hidden fixed inset-0 z-50" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileDrawerOpen(false)}
            aria-label="Close menu"
          />
          <div className="absolute left-0 top-0 bottom-0 w-[92%] max-w-[380px] bg-sidebar flex flex-col pt-[env(safe-area-inset-top)]">
            <div className="border-b border-sidebar-border px-4 py-4">
              <div className="axiom-brand flex items-center gap-3">
                <div className="axiom-brand-icon axiom-brand-icon--mobile shrink-0">
                  <PillarIcon pillar="axiom" size={16} />
                </div>
                <div className="min-w-0">
                  <div className="axiom-brand-name text-[17px] leading-tight">Axiom</div>
                  <div className="axiom-brand-tagline text-[10px] font-medium uppercase tracking-[0.14em] text-gray-300">
                    Architecture Intelligence
                  </div>
                </div>
              </div>
            </div>

            <div className="p-2 flex items-center justify-between border-b border-sidebar-border">
              <div className="flex min-w-0 items-center gap-2 px-2 py-1">
                <span className="text-xs font-semibold text-gray-300">Menu</span>
                <span className="text-[11px] text-gray-500 truncate">{activeViewLabel}</span>
              </div>
              <button
                type="button"
                className="p-2 rounded-lg text-gray-300 hover:bg-sidebar-hover"
                onClick={() => setMobileDrawerOpen(false)}
                aria-label="Close menu"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M4 4l8 8M12 4l-8 8" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto sidebar-scroll px-2 py-3 space-y-3">
              <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/20">
                <PillarNav mobile />
              </section>

              <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/20 p-2 flex flex-col gap-1.5">
                {isSpecWeaverRoute ? (
                  <button
                    onClick={() => {
                      void handleCreateSpecWeaverSession();
                    }}
                    disabled={isCreatingSpecWeaverSession}
                    className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-3 text-[14px] text-gray-100 hover:bg-sidebar-hover transition-colors disabled:opacity-40"
                    data-testid="mobile-new-specweaver-session"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M8 3v10M3 8h10" />
                    </svg>
                    {isCreatingSpecWeaverSession ? 'Creating session...' : 'New session'}
                  </button>
                ) : isLensRoute ? (
                  <button
                    onClick={handleCreateLensSession}
                    className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-3 text-[14px] text-gray-100 hover:bg-sidebar-hover transition-colors"
                    data-testid="mobile-new-lens-review"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M8 3v10M3 8h10" />
                    </svg>
                    New architecture review
                  </button>
                ) : (
                  <>
                    <button
                      onClick={handleStartNewChat}
                      disabled={isStreaming}
                      className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-3 text-[14px] text-gray-100 hover:bg-sidebar-hover transition-colors disabled:opacity-40"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M8 3v10M3 8h10" />
                      </svg>
                      New chat
                    </button>
                    <button
                      onClick={() => {
                        setActiveView('workshop');
                        navigate('/archon/chat');
                        setSelectedWorkshopSessionId(null);
                        setNewWorkshopKey((k) => k + 1);
                        setMobileDrawerOpen(false);
                      }}
                      className="flex items-center gap-2 w-full border border-sidebar-border rounded-lg px-3 py-3 text-[14px] text-gray-100 hover:bg-sidebar-hover transition-colors"
                    >
                      <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M8 3v10M3 8h10" />
                      </svg>
                      New workshop
                    </button>
                  </>
                )}
              </section>

              <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/20 p-2">
                <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest px-2 pb-1">Navigate</h3>
                <nav className="flex flex-col gap-1">
                  {isSpecWeaverRoute ? (
                    <button
                      onClick={() => {
                        navigate('/specweaver/sessions');
                        setMobileDrawerOpen(false);
                      }}
                      className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[14px] transition-colors ${activeSidebarNavClass}`}
                      data-testid="mobile-drawer-nav-specweaver-sessions"
                    >
                      <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 6h16M4 12h16M4 18h10" />
                      </svg>
                      Sessions
                    </button>
                  ) : isLensRoute ? (
                    <button
                      onClick={() => {
                        navigate('/lens');
                        setMobileDrawerOpen(false);
                      }}
                      className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[14px] transition-colors ${activeSidebarNavClass}`}
                      data-testid="mobile-drawer-nav-lens-reviews"
                    >
                      <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M10.5 5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 0 0 0-11m4.3 9.3L20 20M9 10.5h3m-1.5-1.5v3" />
                      </svg>
                      Reviews
                    </button>
                  ) : (
                    NAV_ITEMS.filter(({ key }) => key === 'home' || key === 'chat' || key === 'workshop').map(({ key, label, icon }) => (
                      <button
                        key={key}
                        onClick={() => {
                          handleNavigatePrimaryView(key);
                          setMobileDrawerOpen(false);
                        }}
                        className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[14px] transition-colors ${
                          activeView === key
                            ? activeSidebarNavClass
                            : 'text-gray-300 hover:bg-sidebar-hover hover:text-gray-100'
                        }`}
                        data-testid={`mobile-drawer-nav-${key}`}
                      >
                        <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d={icon} />
                        </svg>
                        {label}
                      </button>
                    ))
                  )}
                </nav>
              </section>

              {isSpecWeaverRoute && activeSpecWeaverSessionId && (
                <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/30 p-2">
                  <div className="px-2 pt-1 pb-1 flex items-center gap-1.5">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />
                    <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest truncate">
                      Active session
                    </span>
                  </div>
                  <nav className="flex flex-col gap-1 px-1 pb-1">
                    <button
                      onClick={() => {
                        navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}`);
                        setMobileDrawerOpen(false);
                      }}
                      className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors ${
                        location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}`
                          ? activeSidebarNavClass
                          : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                      }`}
                      data-testid="mobile-drawer-nav-specweaver-session"
                    >
                      <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 6h16M4 12h16M4 18h10" />
                      </svg>
                      Session
                    </button>
                    <button
                      onClick={() => {
                        navigate(`/specweaver/sessions/${activeSpecWeaverSessionId}/package`);
                        setMobileDrawerOpen(false);
                      }}
                      className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors ${
                        location.pathname === `/specweaver/sessions/${activeSpecWeaverSessionId}/package`
                          ? activeSidebarNavClass
                          : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                      }`}
                      data-testid="mobile-drawer-nav-specweaver-package"
                    >
                      <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M6 4h9l5 5v11a1 1 0 01-1 1H6a2 2 0 01-2-2V6a2 2 0 012-2zm8 1v4h4" />
                      </svg>
                      Package
                    </button>
                  </nav>
                </section>
              )}

              {!isSpecWeaverRoute && !isLensRoute && hasConversation && (
                <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/30 p-2">
                  <div className="px-2 pt-1 pb-1 flex items-center gap-1.5">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />
                    <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest truncate">
                      Active session
                    </span>
                  </div>
                  <nav className="flex flex-col gap-1 px-1 pb-1">
                    {NAV_ITEMS.filter(({ key }) => key === 'architecture' || key === 'governance' || key === 'archdoc').map(({ key, label, icon }) => (
                      <button
                        key={key}
                        onClick={() => {
                          setActiveView(key);
                          setMobileDrawerOpen(false);
                        }}
                        className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors ${
                          activeView === key
                            ? activeSidebarNavClass
                            : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                        }`}
                        data-testid={`mobile-drawer-nav-${key}`}
                      >
                        <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d={icon} />
                        </svg>
                        {label}
                      </button>
                    ))}
                  </nav>
                </section>
              )}

              <details className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/20" open>
                <summary className="list-none cursor-pointer px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-widest flex items-center justify-between">
                  <span>{isSpecWeaverRoute ? 'Sessions' : isLensRoute ? 'Reviews' : activeView === 'workshop' ? 'Workshops' : 'History'}</span>
                  <span className="text-gray-400 text-[11px] normal-case">Toggle</span>
                </summary>
                <div className="px-2 pb-3">
                  {isSpecWeaverRoute ? (
                    specWeaverSessionsLoading ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
                    ) : specWeaverSessionsError ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">{specWeaverSessionsError}</div>
                    ) : specWeaverSessions.length === 0 ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">No SpecWeaver sessions yet</div>
                    ) : (
                      <div className="flex flex-col gap-1">
                        {specWeaverSessions.map((session) => {
                          const active = session.id === activeSpecWeaverSessionId;
                          return (
                            <button
                              key={session.id}
                              onClick={() => handleOpenSpecWeaverSession(session.id)}
                              className={`text-left rounded-lg px-3 py-2.5 text-[12px] transition-colors ${
                                active
                                  ? activeSidebarItemClass
                                  : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                              }`}
                              title={getSpecWeaverSessionTitle(session)}
                              data-testid={`mobile-specweaver-history-${session.id}`}
                            >
                              <div className="flex items-center gap-2">
                                {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                                <span className={`truncate ${active ? 'font-medium' : ''}`}>{getSpecWeaverSessionTitle(session)}</span>
                              </div>
                              <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                                {SPECWEAVER_STATUS_LABELS[session.status]}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )
                  ) : isLensRoute ? (
                    lensSessionsLoading ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">Loading...</div>
                    ) : lensSessionsError ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">{lensSessionsError}</div>
                    ) : lensSessions.length === 0 ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">No Lens reviews yet</div>
                    ) : (
                      <div className="flex flex-col gap-1">
                        {lensSessions.map((session) => {
                          const active = session.id === activeLensSessionId;
                          return (
                            <button
                              key={session.id}
                              onClick={() => handleOpenLensSession(session.id)}
                              className={`text-left rounded-lg px-3 py-2.5 text-[12px] transition-colors ${
                                active
                                  ? activeSidebarItemClass
                                  : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                              }`}
                              title={session.title}
                              data-testid={`mobile-lens-history-${session.id}`}
                            >
                              <div className="flex items-center gap-2">
                                {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                                <span className={`truncate ${active ? 'font-medium' : ''}`}>{session.title || 'Untitled review'}</span>
                              </div>
                              <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                                {session.status.replace(/_/g, ' ')}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )
                  ) : activeView === 'workshop' ? (
                    workshopSessionsLoading ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
                    ) : workshopSessionsError ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">{workshopSessionsError}</div>
                    ) : workshopSessions.length === 0 ? (
                      <div className="px-3 py-2 text-[12px] text-gray-500">No workshops yet</div>
                    ) : (
                      <div className="flex flex-col gap-1">
                        {workshopSessions.map((ws) => {
                          const active = ws.sessionId === selectedWorkshopSessionId;
                          return (
                            <button
                              key={ws.sessionId}
                              onClick={() => handleLoadWorkshopSession(ws.sessionId)}
                              className={`text-left rounded-lg px-3 py-2.5 text-[12px] transition-colors ${
                                active
                                  ? activeSidebarItemClass
                                  : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                              }`}
                              title={ws.systemName}
                            >
                              <div className="flex items-center gap-2">
                                {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                                <span className={`truncate ${active ? 'font-medium' : ''}`}>{ws.systemName}</span>
                              </div>
                              <div className="text-[10px] text-gray-500 mt-0.5 truncate">
                                {ws.workshopPhase.replace(/_/g, ' ')}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )
                  ) : sessionsLoading ? (
                    <div className="px-3 py-2 text-[12px] text-gray-500">Loading…</div>
                  ) : sessionsError ? (
                    <div className="px-3 py-2 text-[12px] text-gray-500">{sessionsError}</div>
                  ) : sessions.length === 0 ? (
                    <div className="px-3 py-2 text-[12px] text-gray-500">No chats yet</div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      {sessions.map((s) => {
                        const active = s.id === conversationId;
                        const loading = loadingSessionId === s.id;
                        return (
                          <button
                            key={s.id}
                            onClick={() => handleLoadSession(s.id)}
                            disabled={isStreaming || loading}
                            className={`text-left rounded-lg px-3 py-2.5 text-[12px] transition-colors relative ${
                              active
                                ? activeSidebarItemClass
                                : 'text-gray-400 hover:bg-sidebar-hover hover:text-gray-200'
                            } ${isStreaming || loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            title={s.title}
                          >
                            <div className="flex items-center gap-2">
                              {active && <span className={`inline-block w-1.5 h-1.5 rounded-full ${activeSidebarDotClass} shrink-0`} />}
                              <span className={`truncate ${active ? 'font-medium' : ''}`}>{s.title}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </details>

              {!isSpecWeaverRoute && hasActiveStages && (
                <section className="rounded-xl border border-sidebar-border/70 bg-sidebar-hover/30 p-2">
                  <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest px-2 mb-1.5">Pipeline</h3>
                  <StageProgress stages={stages} />
                </section>
              )}
            </div>

            <div className="border-t border-sidebar-border p-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))]">
              <div className="flex items-center gap-2.5 px-3 py-1.5 mb-1">
                <div className="w-6 h-6 shrink-0 rounded-full bg-accent/80 flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">{(username ?? 'U')[0].toUpperCase()}</span>
                </div>
                <span className="text-[12px] text-gray-400 truncate">{username}</span>
              </div>
              <button
                onClick={() => {
                  clearAuth();
                  resetConversation();
                  setMobileDrawerOpen(false);
                  safeRemoveItem(STORAGE_KEYS.lastView);
                  safeRemoveItem(STORAGE_KEYS.lastConversationId);
                }}
                className="flex items-center gap-2.5 w-full rounded-lg px-3 py-2 text-[13px] text-gray-400 hover:bg-sidebar-hover hover:text-gray-200 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Main content ── */}
      <main className="flex-1 flex flex-col min-w-0 bg-white overflow-hidden">
        {/* Mobile top bar */}
        <div className="md:hidden border-b border-gray-100 bg-white">
          <div className="h-12 px-3 flex items-center justify-between gap-2">
            <button
              type="button"
              className="p-2 -ml-1 rounded-lg hover:bg-gray-50 active:bg-gray-100 transition-colors"
              onClick={() => setMobileDrawerOpen(true)}
              aria-label="Open menu"
            >
              <svg className="w-5 h-5 text-gray-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-800 truncate">{activeViewLabel}</p>
              {hasConversation && (
                <p className="text-[11px] text-gray-500 truncate">
                  Session loaded
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                if (isSpecWeaverRoute) {
                  void handleCreateSpecWeaverSession();
                  return;
                }
                if (isLensRoute) {
                  handleCreateLensSession();
                  return;
                }
                handleStartNewChat();
              }}
              disabled={isSpecWeaverRoute ? isCreatingSpecWeaverSession : isLensRoute ? false : isStreaming}
              className="text-xs font-medium rounded-lg px-2.5 py-1.5 border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
            >
              {isSpecWeaverRoute ? 'New session' : isLensRoute ? 'New review' : 'New'}
            </button>
          </div>
        </div>

        {/* Content (leave space for fixed mobile bottom nav) */}
        <div className="flex-1 min-h-0 pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0">
          {isPlatformHomeRoute ? (
            <AxiomHomePage />
          ) : isSpecWeaverRoute ? (
            <Routes>
              <Route path="/specweaver" element={<SpecWeaverHomePage />} />
              <Route path="/specweaver/sessions" element={<SessionListView />} />
              <Route path="/specweaver/sessions/:sessionId" element={<SessionView />} />
              <Route path="/specweaver/sessions/:sessionId/package" element={<PackageDetailView />} />
            </Routes>
          ) : isLensRoute ? (
            <Routes>
              <Route path="/lens" element={<LensHomePage />} />
              <Route path="/lens/new" element={<LensReviewPage />} />
              <Route path="/lens/sessions/:sessionId" element={<LensReviewPage />} />
            </Routes>
          ) : isMemoriaRoute ? (
            <Routes>
              <Route path="/memoria" element={<MemoriaHomePage />} />
              <Route path="/memoria/new" element={<MemoriaNewProjectPage />} />
              <Route path="/memoria/projects/:projectId" element={<MemoriaWorkspacePage />} />
            </Routes>
          ) : isArchonHomeRoute ? (
            <ArchonHomePage />
          ) : (
            <>
              {activeView === 'chat' && <ChatView />}
              {activeView === 'architecture' && (
                <div className="h-full overflow-y-auto">
                  <div className="max-w-5xl mx-auto"><ArchitectureView /></div>
                </div>
              )}
              {activeView === 'governance' && (
                <div className="h-full overflow-y-auto">
                  <div className="max-w-5xl mx-auto"><GovernanceView /></div>
                </div>
              )}
              {activeView === 'archdoc' && (
                <div className="h-full overflow-y-auto">
                  <div className="max-w-5xl mx-auto">
                    <ArchDocView />
                  </div>
                </div>
              )}
              {activeView === 'workshop' && (
                <WorkshopView
                  key={selectedWorkshopSessionId ?? `new-${newWorkshopKey}`}
                  initialSessionId={selectedWorkshopSessionId}
                  onNavigateToChat={(conversationId, initialMessage) => {
                    safeSetItem(STORAGE_KEYS.lastConversationId, conversationId);
                    // Seed the store with the conversation ID and the requirements
                    // text. ChatView will auto-submit the seed via the SSE stream
                    // so the pipeline runs and produces a response.
                    setConversationId(conversationId);
                    setWorkshopSeed(initialMessage);
                    setActiveView('chat');
                    navigate('/archon/chat');
                  }}
                  onSessionCreated={handleWorkshopSessionCreated}
                />
              )}
            </>
          )}
        </div>

        {/* Mobile bottom nav */}
        <nav
          className={`mobile-bottom-nav mobile-bottom-nav--${activeSidebarPillar} md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-gray-100 bg-white/95 backdrop-blur pb-[env(safe-area-inset-bottom)]`}
          data-testid="mobile-bottom-nav"
        >
          <div className={`grid h-16 ${mobileBottomGridClass}`}>
            {mobileBottomNavItems.map(({ id, label, icon, active, disabled, onClick }) => {
              return (
                <button
                  key={id}
                  type="button"
                  onClick={onClick}
                  disabled={disabled}
                  className={`min-w-0 flex flex-col items-center justify-center gap-0.5 px-0.5 text-[10px] transition-colors ${
                    active ? 'mobile-bottom-nav-item--active' : 'text-gray-500'
                  } ${disabled ? 'opacity-40' : 'hover:bg-gray-50 active:bg-gray-100'}`}
                  aria-current={active ? 'page' : undefined}
                  data-testid={`mobile-nav-${id}`}
                >
                  <svg className="h-[18px] w-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <path d={icon} />
                  </svg>
                  <span className="max-w-full truncate leading-none">{label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      </main>
    </div>
    </ToastProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeToggle />
      <AppContent />
    </BrowserRouter>
  );
}
