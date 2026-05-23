import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useStore } from '../../store/useStore';
import {
  createWorkshopSession,
  submitWorkshopTurn,
  getWorkshopSession,
  getWorkshopAttributes,
  getWorkshopScenarios,
  getWorkshopMessages,
  sendWorkshopToPipeline,
  assessGenerationReadiness,
  generateAttributes,
  getUtilityTree,
  getImplications,
} from '../../api/workshop';
import type {
  WorkshopTurnResponse,
  QualityAttribute,
  GapSummary,
  GenerationReadinessDto,
  WorkshopScenario,
  UtilityTreeDto,
  ArchitectureImplicationDto,
} from '../../types/workshop';
import { ProgressTracker } from './components/ProgressTracker';
import { ConversationThread } from './components/ConversationThread';
import { InputPanel } from './components/InputPanel';
import { GapIndicator } from './components/GapIndicator';
import { AttributePanel } from './components/AttributePanel';
import { GeneratePanel } from './components/GeneratePanel';
import { ReadinessModal } from './components/ReadinessModal';
import { ScenarioCard } from './components/ScenarioCard';
import { MarkdownExportActions } from '../../components/StructuredData';
import { buildScenariosMarkdown } from './workshopMarkdown';

interface Message {
  role: 'user' | 'agent';
  content: string;
}

interface Props {
  onNavigateToChat: (conversationId: string, initialMessage: string) => void;
  initialSessionId?: string | null;
  onSessionCreated?: (sessionId: string) => void;
}

const EMPTY_GAP_SUMMARY: GapSummary = {
  total: 0,
  filled: 0,
  completionPct: 0,
  inProgressCount: 0,
  openGaps: [],
};

type MobileWorkshopPanel = 'chat' | 'gaps' | 'outputs';

function useMinWidthLg() {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia('(min-width: 1024px)').matches : true,
  );

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)');
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  return matches;
}

/**
 * Renders the SEI QAW utility tree grouped by attribute name.
 * Driver scenarios (H,H) and (H,M) are highlighted with a chip.
 */
function UtilityTreePanel({ utilityTree }: { utilityTree: UtilityTreeDto | null }) {
  if (!utilityTree) {
    return (
      <p className="text-[12px] text-gray-400 text-center py-8 px-4">
        The priority tree is generated once 5+ scenarios across 3+ attributes are elicited.
        Keep describing operational events to unlock it.
      </p>
    );
  }

  const byAttribute = utilityTree.nodes.reduce<Record<string, typeof utilityTree.nodes>>((acc, n) => {
    if (!acc[n.attributeName]) acc[n.attributeName] = [];
    acc[n.attributeName].push(n);
    return acc;
  }, {});

  const isDriver = (scenarioId: string) => utilityTree.architecturalDrivers.includes(scenarioId);

  return (
    <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4 space-y-4">
      <p className="text-[11px] text-gray-400">{utilityTree.generationRationale}</p>
      {Object.entries(byAttribute).map(([attrName, nodes]) => (
        <div key={attrName}>
          <h3 className="text-[12px] font-semibold text-gray-700 mb-2">{attrName}</h3>
          <div className="space-y-2">
            {nodes.map((node) => (
              <div
                key={node.nodeId}
                className="rounded border border-gray-100 bg-gray-50 p-2 text-[12px]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    {node.refinement && (
                      <span className="text-gray-400 italic mr-1">{node.refinement} —</span>
                    )}
                    <span className="text-gray-700">{node.scenarioTitle}</span>
                    {isDriver(node.scenarioId) && (
                      <span className="ml-2 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                        DRIVER
                      </span>
                    )}
                  </div>
                  <span className="shrink-0 text-[10px] font-mono text-gray-400">
                    ({node.businessImportance},{node.technicalRisk})
                  </span>
                </div>
                {node.rationale && (
                  <p className="mt-1 text-[11px] text-gray-400">{node.rationale}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Renders architectural implications grouped by constraint type.
 * Includes a "Send to Architecture Pipeline" button when must-strength
 * implications are present.
 */
function ArchitecturePanel({
  implications,
  onSendToPipeline,
  sendingToPipeline,
}: {
  implications: ArchitectureImplicationDto[];
  onSendToPipeline: () => void;
  sendingToPipeline: boolean;
}) {
  if (implications.length === 0) {
    return (
      <p className="text-[12px] text-gray-400 text-center py-8 px-4">
        Architectural implications are derived after the priority tree is generated.
        Continue the workshop to unlock them.
      </p>
    );
  }

  const byType = implications.reduce<Record<string, ArchitectureImplicationDto[]>>((acc, i) => {
    if (!acc[i.constraintType]) acc[i.constraintType] = [];
    acc[i.constraintType].push(i);
    return acc;
  }, {});

  const strengthBadge = (s: string) => {
    if (s === 'must') return 'bg-red-100 text-red-700';
    if (s === 'should') return 'bg-yellow-100 text-yellow-700';
    return 'bg-gray-100 text-gray-500';
  };

  const hasMust = implications.some((i) => i.strength === 'must');

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4 space-y-4">
        {Object.entries(byType).map(([type, items]) => (
          <div key={type}>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-2">
              {type}
            </h3>
            <div className="space-y-2">
              {items.map((imp) => (
                <div
                  key={imp.implicationId}
                  className="rounded border border-gray-100 bg-gray-50 p-3 text-[12px]"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-gray-200 pb-2">
                    <span className="min-w-0 text-[11px] font-semibold text-gray-700">
                      [{(imp.constraintClassification ?? 'functional_constraint').replace(/_/g, ' ')}] {imp.constraintType}
                    </span>
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${strengthBadge(imp.strength)}`}
                    >
                      {imp.strength.toUpperCase()}
                    </span>
                  </div>
                  <p className="mt-2 text-gray-700">{imp.implication}</p>
                  {imp.tradeoff && (
                    <div className="mt-2 rounded border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-900">
                      {imp.tradeoff}
                    </div>
                  )}
                  {imp.measurableCondition && (
                    <div className="mt-2">
                      <span className="inline-flex max-w-full rounded bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-700 ring-1 ring-emerald-200">
                        Measurable condition: {imp.measurableCondition}
                      </span>
                    </div>
                  )}
                  {imp.sourceScenarioTitle && (
                    <p className="mt-2 text-[11px] text-gray-500">
                      Source: {imp.sourceScenarioId} - {imp.sourceScenarioTitle}
                    </p>
                  )}
                  {(imp.affectedQualityAttrs ?? []).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(imp.affectedQualityAttrs ?? []).map((attr) => (
                        <span
                          key={`${imp.implicationId}-${attr}`}
                          className="rounded bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-500 ring-1 ring-gray-200"
                        >
                          {attr}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {hasMust && (
        <div className="shrink-0 border-t border-gray-100 p-3">
          <button
            type="button"
            disabled={sendingToPipeline}
            aria-busy={sendingToPipeline}
            onClick={onSendToPipeline}
            className="w-full rounded bg-accent px-4 py-2 text-[12px] font-medium text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {sendingToPipeline
              ? 'Sending to pipeline...'
              : 'Send to Architecture Pipeline with constraints →'}
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Quality Attribute Workshop view.
 *
 * Layout:
 * - Desktop (lg+): three columns — conversation, information gaps, attributes/scenarios.
 * - Mobile: segmented control switches full-width panels for the same three areas.
 * - Top: phase progress tracker (horizontally scrollable on small screens).
 */
export function WorkshopView({ onNavigateToChat, initialSessionId, onSessionCreated }: Props) {
  const token = useStore((s) => s.token)!;

  // Session state — initialize from prop when restoring a historical session
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId ?? null);
  const [systemName, setSystemName] = useState('');
  const [systemNameInput, setSystemNameInput] = useState('');
  const [phase, setPhase] = useState('CONTEXT_SETTING');
  const [turnNumber, setTurnNumber] = useState(0);
  const [hasSufficientAttributes, setHasSufficientAttributes] = useState(false);
  const [gapSummary, setGapSummary] = useState<GapSummary>(EMPTY_GAP_SUMMARY);

  // UI state
  const [messages, setMessages] = useState<Message[]>([]);
  const [attributes, setAttributes] = useState<QualityAttribute[]>([]);
  const [scenarios, setScenarios] = useState<WorkshopScenario[]>([]);
  const [rightTab, setRightTab] = useState<'attributes' | 'scenarios' | 'priority-tree' | 'architecture'>('attributes');
  const [utilityTree, setUtilityTree] = useState<UtilityTreeDto | null>(null);
  const [implications, setImplications] = useState<ArchitectureImplicationDto[]>([]);
  const [loading, setLoading] = useState(!!initialSessionId);
  const [sendingToPipeline, setSendingToPipeline] = useState(false);

  /** Increments to re-trigger the historical-load effect (retry on failure). */
  const [loadTrigger, setLoadTrigger] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [generationCount, setGenerationCount] = useState(0);
  const [attributesStale, setAttributesStale] = useState(false);
  const [continuationPrompt, setContinuationPrompt] = useState<string | null>(null);
  const [readinessOpen, setReadinessOpen] = useState(false);
  const [readinessData, setReadinessData] = useState<GenerationReadinessDto | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);

  /** Draft text auto-saved to localStorage so it survives page reloads and 5xx errors. */
  const [draftInput, setDraftInput] = useState('');
  /** Whether the current error response indicates the draft was preserved on the server. */
  const [draftPreservedOnServer, setDraftPreservedOnServer] = useState(false);
  /** Non-QA concerns identified during the workshop (regulatory, organisational, etc.) */
  const [nonQaConcerns, setNonQaConcerns] = useState<{ name: string; description: string; category: string }[]>([]);
  const [nonQaPanelOpen, setNonQaPanelOpen] = useState(false);

  /** Which workshop column is visible below the `lg` breakpoint. */
  const [mobileWorkshopPanel, setMobileWorkshopPanel] = useState<MobileWorkshopPanel>('chat');
  const minWidthLg = useMinWidthLg();
  const compactExportToolbar = !minWidthLg;

  const draftKey = sessionId ? `workshop_draft_${sessionId}` : null;
  const draftSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const threadRef = useRef<HTMLDivElement>(null);
  const generatePanelRef = useRef<HTMLDivElement>(null);

  const scenariosMarkdown = useMemo(
    () =>
      scenarios.length > 0 && sessionId
        ? buildScenariosMarkdown(scenarios, {
            systemName: systemName.trim() || undefined,
            sessionId,
          })
        : '',
    [scenarios, sessionId, systemName],
  );

  // Load a historical session when initialSessionId is provided on mount
  useEffect(() => {
    if (!initialSessionId) return;

    let cancelled = false;

    Promise.allSettled([
      getWorkshopSession(token, initialSessionId),
      getWorkshopAttributes(token, initialSessionId),
      getWorkshopScenarios(token, initialSessionId),
      getWorkshopMessages(token, initialSessionId),
    ]).then(([sessionResult, attrsResult, scenariosResult, msgsResult]) => {
        if (cancelled) return;

        if (sessionResult.status === 'rejected') {
          setError((sessionResult.reason as Error).message ?? 'Failed to load session');
          setLoading(false);
          return;
        }

        const session = sessionResult.value;
        setSystemName(session.systemName);
        setPhase(session.workshopPhase);
        setTurnNumber(session.turnCount);
        setGenerationCount(session.generationCount ?? 0);
        setAttributesStale(session.attributesStale ?? false);
        setHasSufficientAttributes(session.readyForPipeline);
        setGapSummary({
          total: session.totalGaps,
          filled: session.filledGaps,
          completionPct: session.gapCompletionPct,
          inProgressCount: session.inProgressGaps ?? 0,
          openGaps: session.openGaps ?? [],
        });

        if (attrsResult.status === 'fulfilled') {
          setAttributes(attrsResult.value);
        }

        if (scenariosResult.status === 'fulfilled') {
          setScenarios(scenariosResult.value);
        }

        if (msgsResult.status === 'fulfilled') {
          // Reconstruct the conversation thread from persisted turn records
          const thread: Message[] = msgsResult.value.flatMap((m) => [
            { role: 'user' as const, content: m.userInput },
            { role: 'agent' as const, content: m.agentResponse },
          ]);
          setMessages(thread);
        }

        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  // loadTrigger intentionally included so retrying re-runs this effect
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadTrigger]);

  // Auto-scroll conversation to bottom (on new messages and when typing indicator appears)
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // Restore draft from localStorage when a session becomes active.
  useEffect(() => {
    if (!draftKey) return;
    const saved = localStorage.getItem(draftKey);
    if (saved) {
      setDraftInput(saved);
    }
  }, [draftKey]);

  /** Debounced auto-save: write draft to localStorage 2s after the user stops typing. */
  const handleDraftChange = useCallback((value: string) => {
    setDraftInput(value);
    if (!draftKey) return;
    if (draftSaveTimer.current) clearTimeout(draftSaveTimer.current);
    draftSaveTimer.current = setTimeout(() => {
      if (value) {
        localStorage.setItem(draftKey, value);
      } else {
        localStorage.removeItem(draftKey);
      }
    }, 2_000);
  }, [draftKey]);

  // Create session when user submits system name
  const handleStartSession = async () => {
    const name = systemNameInput.trim();
    if (!name) return;
    setLoading(true);
    setError(null);
    try {
      const session = await createWorkshopSession(token, name);
      setSessionId(session.sessionId);
      setSystemName(session.systemName);
      setMobileWorkshopPanel('chat');
      onSessionCreated?.(session.sessionId);
      setMessages([
        {
          role: 'agent',
          content: `Welcome! I'll help you elicit quality attributes for **${session.systemName}** using the SEI Quality Attribute Workshop methodology.\n\nLet's start: please describe what the system does and who its primary users are.`,
        },
      ]);
    } catch (e) {
      setError((e as Error).message ?? 'Failed to start session');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitTurn = async (userInput: string) => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    setDraftPreservedOnServer(false);

    // Optimistically add the user message
    setMessages((prev) => [...prev, { role: 'user', content: userInput }]);

    // --- Primary turn call — fatal on failure ---
    let response: WorkshopTurnResponse;
    try {
      response = await submitWorkshopTurn(token, sessionId, userInput);
    } catch (e) {
      const err = e as Error & { status?: number; draftPreserved?: boolean };
      setError(err.message ?? 'Failed to process turn');
      // Server returns draft_preserved: true on 504 (timeout)
      setDraftPreservedOnServer(!!(err.draftPreserved));
      // Remove the optimistic user message — the turn itself failed
      setMessages((prev) => prev.slice(0, -1));
      setLoading(false);
      return;
    }

    // Turn succeeded: clear the saved draft and update conversation state
    if (draftKey) localStorage.removeItem(draftKey);
    setDraftInput('');

    setMessages((prev) => [
      ...prev,
      { role: 'agent', content: response.agentMessage },
    ]);
    setPhase(response.workshopPhase);
    setTurnNumber(response.turnNumber);
    setHasSufficientAttributes(response.readyForPipeline);
    setGapSummary(response.gapSummary);
    if (response.nonQaConcerns && response.nonQaConcerns.length > 0) {
      setNonQaConcerns((prev) => {
        const existing = new Set(prev.map((c) => c.name.toLowerCase()));
        const incoming = response.nonQaConcerns!.filter(
          (c) => !existing.has(c.name.toLowerCase())
        );
        return [...prev, ...incoming];
      });
    }

    // --- Secondary fetches — non-fatal; failures do not hide the turn response ---
    try {
      const sessionSnap = await getWorkshopSession(token, sessionId);
      setGenerationCount(sessionSnap.generationCount ?? 0);
      setAttributesStale(sessionSnap.attributesStale ?? false);
    } catch (_) {
      // Non-fatal: generation count and stale flag will refresh on the next load
    }

    try {
      const [attrs, scen] = await Promise.all([
        getWorkshopAttributes(token, sessionId),
        getWorkshopScenarios(token, sessionId),
      ]);
      setAttributes(attrs);
      setScenarios(scen);
    } catch (_) {
      // Non-fatal: attributes and scenarios will refresh on the next load
    }

    setLoading(false);
  };

  const handlePreviewReadiness = async () => {
    if (!sessionId) return;
    setPreviewLoading(true);
    setError(null);
    try {
      const data = await assessGenerationReadiness(sessionId, token);
      setReadinessData(data);
      setReadinessOpen(true);
    } catch (e) {
      setError((e as Error).message ?? 'Could not load readiness preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerateFromEvidence = async () => {
    if (!sessionId) return;
    setGenerateLoading(true);
    setError(null);
    try {
      const res = await generateAttributes(sessionId, token);
      setGenerationCount(res.generationCount);
      setAttributesStale(res.attributesStale);
      setContinuationPrompt(res.continuationPrompt);
      const attrs = await getWorkshopAttributes(token, sessionId);
      setAttributes(attrs);
    } catch (e) {
      setError((e as Error).message ?? 'Generation failed');
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleSendToPipeline = async () => {
    if (!sessionId) return;
    if (sendingToPipeline) {
      console.warn(
        'send-to-pipeline: duplicate click suppressed while ' +
        'submission in progress',
      );
      return;
    }
    setSendingToPipeline(true);
    setError(null);
    try {
      const { conversationId, initialMessage } = await sendWorkshopToPipeline(token, sessionId);
      onNavigateToChat(conversationId, initialMessage);
    } catch (e) {
      setError((e as Error).message ?? 'Failed to send to pipeline');
      setSendingToPipeline(false);
    }
  };

  // ── Historical load failure ─────────────────────────────────────────────────
  // Shown when an initialSessionId was provided but the session fetch failed.
  if (initialSessionId && !loading && error && !systemName) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50" data-testid="workshop-view">
        <div className="bg-white border border-red-100 rounded-2xl p-8 max-w-md w-full mx-4 shadow-sm archon-reveal text-center">
          <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          </div>
          <h2 className="text-[15px] font-semibold text-gray-900 mb-1">Failed to load session</h2>
          <p className="text-[12px] text-gray-500 mb-5 leading-relaxed">{error}</p>
          <button
            onClick={() => { setLoading(true); setError(null); setLoadTrigger((n) => n + 1); }}
            className="bg-accent hover:bg-accent-hover text-white rounded-xl px-5 py-2.5 text-[13px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/40"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // ── System name entry screen ────────────────────────────────────────────────
  if (!sessionId) {
    return (
      <div
        className="h-full flex items-center justify-center bg-gray-50"
        data-testid="workshop-view"
      >
        <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full mx-4 shadow-sm archon-reveal">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h1 className="text-[16px] font-semibold text-gray-900">Quality Attribute Workshop</h1>
              <p className="text-[12px] text-gray-500">SEI QAW methodology</p>
            </div>
          </div>

          <p className="text-[13px] text-gray-600 mb-5 leading-relaxed">
            I'll guide you through a structured elicitation to define measurable quality requirements for your system — <em>asking before asserting</em>.
          </p>

          <label htmlFor="system-name" className="block text-[12px] font-medium text-gray-700 mb-1.5">
            System name
          </label>
          <input
            id="system-name"
            type="text"
            value={systemNameInput}
            onChange={(e) => setSystemNameInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleStartSession()}
            placeholder="e.g. Payment Processing Service"
            className="w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-[13px] text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent/40 mb-4"
            data-testid="system-name-input"
          />

          {error && (
            <div className="mb-3 bg-red-50 border border-red-100 rounded-xl px-3 py-2 text-[12px] text-red-700">
              {error}
            </div>
          )}

          <button
            onClick={handleStartSession}
            disabled={loading || !systemNameInput.trim()}
            className="w-full bg-accent hover:bg-accent-hover disabled:opacity-50 text-white rounded-xl py-2.5 text-[13px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/40"
            data-testid="start-workshop-btn"
          >
            {loading ? 'Starting…' : 'Start Workshop'}
          </button>
        </div>
      </div>
    );
  }

  // ── Main 3-panel layout ─────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full" data-testid="workshop-view">
      {/* Phase progress bar */}
      <ProgressTracker
        currentPhase={phase}
        turnNumber={turnNumber}
        hasSufficientAttributes={hasSufficientAttributes}
      />

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-100 px-4 py-2 text-[12px] text-red-700" role="alert">
          <span>{error}</span>
          {draftPreservedOnServer && (
            <span className="ml-2 text-red-600 font-medium">
              Your input was preserved — you can try again.
              <button
                className="ml-2 underline"
                onClick={() => {
                  if (draftInput) navigator.clipboard.writeText(draftInput).catch(() => {});
                }}
                aria-label="Copy draft to clipboard"
              >
                Copy to clipboard
              </button>
            </span>
          )}
          <button
            onClick={() => { setError(null); setDraftPreservedOnServer(false); }}
            className="ml-2 text-red-500 hover:text-red-700"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      <div className="flex flex-1 min-h-0 flex-col lg:flex-row">
        {/* Mobile: one full-width column at a time */}
        <div
          className="lg:hidden flex p-1 gap-1 shrink-0 bg-gray-100 border-b border-gray-200"
          role="tablist"
          aria-label="Workshop section"
        >
          {(
            [
              { id: 'chat' as const, label: 'Chat' },
              { id: 'gaps' as const, label: 'Gaps' },
              { id: 'outputs' as const, label: 'Results' },
            ] as const
          ).map(({ id, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mobileWorkshopPanel === id}
              onClick={() => setMobileWorkshopPanel(id)}
              className={`flex-1 rounded-lg py-2.5 text-[12px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 ${
                mobileWorkshopPanel === id
                  ? 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200/80'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-white/60'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Left: conversation ── */}
        <div
          className={`${
            mobileWorkshopPanel === 'chat' ? 'flex flex-1 flex-col' : 'hidden lg:flex lg:flex-col'
          } min-h-0 min-w-0 border-gray-200 bg-gray-50 lg:w-[45%] lg:shrink-0 lg:border-r`}
        >
          <div className="px-3 sm:px-4 py-2 border-b border-gray-200 bg-white shrink-0">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide truncate">
              {systemName}
            </p>
          </div>
          <div className="flex flex-col flex-1 min-h-0">
            <div ref={threadRef} className="flex-1 overflow-y-auto min-h-0">
              <ConversationThread messages={messages} isLoading={loading} />
            </div>
            <GeneratePanel
              turnComplete={turnNumber >= 1}
              generationCount={generationCount}
              attributesStale={attributesStale}
              continuationPrompt={continuationPrompt}
              previewLoading={previewLoading}
              generateLoading={generateLoading}
              onPreview={handlePreviewReadiness}
              onGenerate={handleGenerateFromEvidence}
              panelRef={generatePanelRef}
            />
            <InputPanel
              onSubmit={handleSubmitTurn}
              disabled={loading}
              initialValue={draftInput}
              onValueChange={handleDraftChange}
            />
          </div>
        </div>

        {/* ── Centre: gap tracker ── */}
        <div
          className={`${
            mobileWorkshopPanel === 'gaps' ? 'flex flex-1 flex-col' : 'hidden lg:flex lg:flex-col'
          } min-h-0 min-w-0 border-gray-200 bg-white lg:w-[25%] lg:shrink-0 lg:border-r`}
        >
          <div className="px-3 sm:px-4 py-2 border-b border-gray-200 shrink-0">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
              Information Gaps
            </p>
          </div>
          <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4">
            <GapIndicator
              totalGaps={gapSummary.total}
              filledGaps={gapSummary.filled}
              gapCompletionPct={gapSummary.completionPct}
              inProgressCount={gapSummary.inProgressCount ?? 0}
              openGaps={gapSummary.openGaps}
            />
          </div>
        </div>

        {/* ── Right: attributes / scenarios + non-QA concerns ── */}
        <div
          className={`${
            mobileWorkshopPanel === 'outputs' ? 'flex flex-1 flex-col' : 'hidden lg:flex lg:flex-col'
          } min-h-0 min-w-0 bg-white lg:flex-1`}
        >
          <div className="flex border-b border-gray-200 px-2 pt-2 gap-1 overflow-x-auto shrink-0 [scrollbar-width:thin]">
            <button
              type="button"
              onClick={() => setRightTab('attributes')}
              className={`shrink-0 px-3 py-1.5 text-[12px] font-medium rounded-t-lg transition-colors ${
                rightTab === 'attributes'
                  ? 'bg-white text-accent border border-b-0 border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Attributes
            </button>
            <button
              type="button"
              onClick={() => setRightTab('scenarios')}
              className={`shrink-0 px-3 py-1.5 text-[12px] font-medium rounded-t-lg transition-colors ${
                rightTab === 'scenarios'
                  ? 'bg-white text-accent border border-b-0 border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Scenarios ({scenarios.length})
            </button>
            <button
              type="button"
              onClick={() => {
                setRightTab('priority-tree');
                if (!utilityTree && sessionId) {
                  getUtilityTree(token, sessionId)
                    .then(setUtilityTree)
                    .catch(() => { /* not yet generated — silently ignore */ });
                }
              }}
              className={`shrink-0 px-3 py-1.5 text-[12px] font-medium rounded-t-lg transition-colors ${
                rightTab === 'priority-tree'
                  ? 'bg-white text-accent border border-b-0 border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Priority Tree
            </button>
            <button
              type="button"
              onClick={() => {
                setRightTab('architecture');
                if (implications.length === 0 && sessionId) {
                  getImplications(token, sessionId)
                    .then(setImplications)
                    .catch(() => { /* silently ignore */ });
                }
              }}
              className={`shrink-0 px-3 py-1.5 text-[12px] font-medium rounded-t-lg transition-colors ${
                rightTab === 'architecture'
                  ? 'bg-white text-accent border border-b-0 border-gray-200'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Architecture
            </button>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            {rightTab === 'attributes' ? (
              <AttributePanel
                attributes={attributes}
                sessionId={sessionId}
                systemName={systemName}
                compactToolbar={compactExportToolbar}
                hasSufficientAttributes={hasSufficientAttributes}
                onSendToPipeline={handleSendToPipeline}
                sendingToPipeline={sendingToPipeline}
                generationCount={generationCount}
                sessionAttributesStale={attributesStale}
              />
            ) : rightTab === 'scenarios' ? (
              <div className="flex flex-col flex-1 min-h-0">
                {scenarios.length > 0 && sessionId && (
                  <div
                    className="flex flex-wrap items-center justify-end gap-2 px-3 sm:px-4 py-2 border-b border-gray-100 shrink-0"
                    data-testid="scenario-markdown-export"
                  >
                    <MarkdownExportActions
                      markdown={scenariosMarkdown}
                      markdownFilename={`workshop-scenarios-${sessionId}.md`}
                      compact={compactExportToolbar}
                    />
                  </div>
                )}
                <div className="flex-1 overflow-y-auto min-h-0 p-3 sm:p-4 space-y-3">
                {scenarios.length === 0 ? (
                  <p className="text-[12px] text-gray-400 text-center py-8">
                    Scenarios appear as you describe operational events and failures.
                  </p>
                ) : (
                  scenarios.map((s) => (
                    <ScenarioCard
                      key={s.scenarioId}
                      scenario={s}
                      onSubmitMeasure={(scenarioId, measure) => {
                        void handleSubmitTurn(
                          `For scenario ${scenarioId}, the measurable response threshold is: ${measure}`,
                        );
                      }}
                    />
                  ))
                )}
                </div>
              </div>
            ) : rightTab === 'priority-tree' ? (
              <UtilityTreePanel utilityTree={utilityTree} />
            ) : (
              <ArchitecturePanel
                implications={implications}
                onSendToPipeline={handleSendToPipeline}
                sendingToPipeline={sendingToPipeline}
              />
            )}
          </div>

          {/* Non-QA concerns — tracked but not counted as quality attributes */}
          {nonQaConcerns.length > 0 && (
            <div className="border-t border-gray-100 mt-auto shrink-0">
              <button
                className="w-full flex items-center justify-between px-3 sm:px-4 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wide hover:bg-gray-50 transition-colors"
                onClick={() => setNonQaPanelOpen((v) => !v)}
                aria-expanded={nonQaPanelOpen}
              >
                <span>Other Concerns ({nonQaConcerns.length})</span>
                <span aria-hidden>{nonQaPanelOpen ? '▲' : '▼'}</span>
              </button>
              {nonQaPanelOpen && (
                <ul className="px-3 sm:px-4 pb-3 space-y-1.5">
                  {nonQaConcerns.map((c) => (
                    <li key={c.name} className="text-[12px] text-gray-400">
                      <span className="font-medium text-gray-500">{c.name}</span>
                      {c.description ? ` — ${c.description}` : ''}
                      {c.category && c.category !== 'other' && (
                        <span className="ml-1.5 text-[10px] text-gray-300 uppercase">[{c.category}]</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <p className="px-3 sm:px-4 pb-2 text-[10px] text-gray-300">
                These concerns are noted but are not quality attributes. They will not appear in the generated architecture document.
              </p>
            </div>
          )}
        </div>
      </div>

      <ReadinessModal
        open={readinessOpen}
        data={readinessData}
        onClose={() => setReadinessOpen(false)}
        onKeepGoing={() => setReadinessOpen(false)}
        onGenerateAnyway={() => {
          void handleGenerateFromEvidence();
        }}
      />
    </div>
  );
}
