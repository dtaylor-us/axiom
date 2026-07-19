import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  createAdr,
  createMemoryEntry,
  createProject,
  createSessionLink,
  distillAllSessions,
  distillSingleSession,
  getProjectSummary,
  listAdrs,
  listDistillationJobs,
  listMemoryEntries,
  listProjects,
  listSessionLinks,
  promoteMemoryEntry,
  removeSessionLink,
  supersedeAdr,
  supersedeMemoryEntry,
  transitionMemoryEntry,
  type AdrStatus,
  type ArchitectureDecision,
  type DistillationJob,
  type MemoryConfidence,
  type MemoryEntry,
  type MemoryStatus,
  type MemoryType,
  type MemoriaProject,
  type Pillar,
  type ProjectMemorySummary,
  type SessionLink,
} from '../../api/memoria';
import { ApiError } from '../../api/http';
import { listSessions as listArchonSessions } from '../../api/sessions';
import { getSessions as listSpecWeaverSessions } from '../../api/specweaver';
import { listReviewSessions } from '../../api/lens';
import { CopyButton } from '../../components/CopyButton';
import { PillarBadge } from '../../components/PillarBadge';
import { emitToast } from '../../components/Toast';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';
import { useStore } from '../../store/useStore';
import type { SessionSummary } from '../../types/api';
import type { Session as SpecWeaverSession } from '../../api/specweaver';
import type { ReviewSession } from '../../api/lens';

const MEMORY_TYPES: MemoryType[] = ['DECISION', 'REQUIREMENT', 'RISK', 'QUALITY_SCORE', 'ASSUMPTION', 'CONSTRAINT', 'SESSION_SUMMARY'];
const MEMORY_STATUSES: MemoryStatus[] = ['ACTIVE', 'STALE', 'SUPERSEDED', 'ARCHIVED'];
const ADR_STATUSES: AdrStatus[] = ['PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'DEPRECATED'];
const PILLARS: Pillar[] = ['SPECWEAVER', 'ARCHON', 'LENS'];

const MEMORIA_FEATURES = [
  {
    icon: '1',
    iconBg: '#fff1f2',
    title: 'Episodic memory',
    description: 'Captures facts from specific sessions: requirements, risks, assumptions, constraints, and summaries.',
  },
  {
    icon: '2',
    iconBg: '#fdf2f8',
    title: 'Semantic memory',
    description: 'Promotes durable architecture knowledge so future sessions inherit the reasoning that still matters.',
  },
  {
    icon: '3',
    iconBg: '#f0fdf4',
    title: 'ADR register',
    description: 'Turns decisions into traceable records with status, context, supersession, and source links.',
  },
];

interface LinkableSession {
  id: string;
  title: string;
  updatedAt: string;
}

const EMPTY_SUMMARY: ProjectMemorySummary = {
  totalFacts: 0,
  activeFacts: 0,
  staleFacts: 0,
  archivedFacts: 0,
  supersededFacts: 0,
  decisions: 0,
  requirements: 0,
  openRisks: 0,
  adrCount: 0,
  expiringSoon: 0,
};

function label(value: string): string {
  return value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value: string | null): string {
  if (!value) return 'No expiry';
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function formatActivityDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function truncate(value: string, length: number): string {
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function sourceHref(pillar: Pillar, sessionId: string): string {
  if (pillar === 'ARCHON') return `/archon/conversations/${sessionId}`;
  if (pillar === 'SPECWEAVER') return `/specweaver/sessions/${sessionId}`;
  return `/lens/sessions/${sessionId}`;
}

function normalizeArchonSession(session: SessionSummary): LinkableSession {
  return {
    id: session.id,
    title: session.title || 'Untitled analysis',
    updatedAt: session.updatedAt ?? session.createdAt ?? new Date(0).toISOString(),
  };
}

function normalizeSpecWeaverSession(session: SpecWeaverSession): LinkableSession {
  return {
    id: session.id,
    title: session.title || 'Untitled session',
    updatedAt: session.updatedAt,
  };
}

function normalizeLensSession(session: ReviewSession): LinkableSession {
  return {
    id: session.id,
    title: session.title || 'Untitled review',
    updatedAt: session.updatedAt,
  };
}

function splitTags(value: string): string[] {
  return value.split(',').map((tag) => tag.trim()).filter(Boolean);
}

function statusClass(status: MemoryStatus | AdrStatus): string {
  if (status === 'ACTIVE' || status === 'ACCEPTED') return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
  if (status === 'STALE' || status === 'PROPOSED') return 'bg-amber-50 text-amber-700 ring-amber-200';
  if (status === 'SUPERSEDED') return 'bg-slate-100 text-slate-600 ring-slate-200';
  return 'bg-rose-50 text-rose-700 ring-rose-200';
}

function Badge({ value }: { value: string }) {
  return <span className="rounded-full px-2 py-1 text-[11px] font-semibold ring-1 ring-inset">{value}</span>;
}

export function MemoriaHomePage() {
  const token = useStore((state) => state.token);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const linkPillar = searchParams.get('linkPillar') as Pillar | null;
  const linkSessionId = searchParams.get('linkSessionId');
  const [projects, setProjects] = useState<MemoriaProject[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const hasLinkIntent = !!linkPillar && !!linkSessionId && PILLARS.includes(linkPillar);

  useEffect(() => {
    if (!token) return;
    listProjects(token)
      .then((items) => setProjects(items))
      .catch((error) => emitToast((error as Error).message, 'error'));
  }, [token]);

  const recentProjects = useMemo(
    () => [...projects]
      .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      .slice(0, 3),
    [projects],
  );

  async function handleCreateProject() {
    if (!token) return;
    setIsCreating(true);
    try {
      const project = await createProject(token, 'Untitled memory project', '');
      const query = hasLinkIntent ? `?${searchParams.toString()}` : '';
      navigate(`/memoria/projects/${project.id}${query}`);
    } catch (error) {
      emitToast((error as Error).message, 'error');
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="memoria-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="pillar-hero-badge">
            <PillarBadge pillar="memoria" />
          </div>
          <h1>Architecture memory, curated and searchable.</h1>
          <p>
            Link your SpecWeaver sessions, Archon conversations, and Lens reviews to a project. Memoria distils
            decisions, requirements, risks, and constraints into a persistent knowledge store, injecting relevant
            context back into your next session so no architectural reasoning is lost.
          </p>
          <div className="hero-actions">
            <button
              type="button"
              onClick={() => void handleCreateProject()}
              disabled={isCreating}
              className="btn btn-primary"
              style={{ background: 'var(--color-pillar-memoria-text)' }}
              data-testid="memoria-new-project"
            >
              {isCreating ? 'Creating...' : 'New project ->'}
            </button>
          </div>
        </section>

        {hasLinkIntent && (
          <section className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-5">
            <p className="text-sm font-semibold text-rose-950">Link {label(linkPillar)} session to Memoria</p>
            <p className="mt-1 break-all text-xs text-rose-800">{linkSessionId}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/memoria/projects/${project.id}?${searchParams.toString()}`}
                  className="rounded-lg bg-white px-3 py-2 text-sm font-semibold text-rose-800 ring-1 ring-rose-200 hover:bg-rose-100"
                >
                  Link to {project.name}
                </Link>
              ))}
              {projects.length === 0 && (
                <button
                  type="button"
                  onClick={() => void handleCreateProject()}
                  className="rounded-lg bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white"
                >
                  Create your first project
                </button>
              )}
            </div>
          </section>
        )}

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-gray-900">Recent projects</h2>
            <Link to="/memoria/new" className="text-sm font-medium text-[var(--color-pillar-memoria-text)]">New project {'->'}</Link>
          </div>
          {projects.length === 0 ? (
            <div className="mt-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
              <p className="text-base font-semibold text-gray-900">Your project memory is empty</p>
              <p className="mx-auto mt-2 max-w-2xl text-sm text-gray-600">
                Memoria captures decisions, requirements, risks, and constraints from your SpecWeaver, Archon, and Lens
                sessions automatically after Phase 3, or manually right now.
              </p>
              <button
                type="button"
                onClick={() => void handleCreateProject()}
                className="mt-4 rounded-lg bg-[var(--color-pillar-memoria-text)] px-4 py-2.5 text-sm font-semibold text-white"
              >
                Create your first project
              </button>
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/memoria/projects/${project.id}`}
                  className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 hover:bg-gray-50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-gray-800">{project.name}</p>
                    <p className="truncate text-xs text-gray-500">{project.description || 'No description yet'}</p>
                  </div>
                  <span className="shrink-0 text-xs text-gray-500">Last activity {formatActivityDate(project.updatedAt)}</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="landing-section--compact">
          <SectionHeading title="What Memoria remembers" accent="var(--color-pillar-memoria)" />
          <div className="feature-cards-grid">
            {MEMORIA_FEATURES.map((card) => <FeatureCard key={card.title} {...card} />)}
          </div>
        </section>
      </div>
    </div>
  );
}

export function MemoriaNewProjectPage() {
  const token = useStore((state) => state.token);
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) return;
    createProject(token, 'Untitled memory project', '')
      .then((project) => navigate(`/memoria/projects/${project.id}`, { replace: true }))
      .catch((error) => {
        emitToast((error as Error).message, 'error');
        navigate('/memoria', { replace: true });
      });
  }, [navigate, token]);

  return <div className="p-6 text-sm text-slate-500">Creating project...</div>;
}

export function MemoriaWorkspacePage() {
  const token = useStore((state) => state.token);
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const [projects, setProjects] = useState<MemoriaProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projectId ?? '');
  const [summary, setSummary] = useState<ProjectMemorySummary>(EMPTY_SUMMARY);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [adrs, setAdrs] = useState<ArchitectureDecision[]>([]);
  const [links, setLinks] = useState<SessionLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [memoryType, setMemoryType] = useState<MemoryType>('DECISION');
  const [memoryConfidence, setMemoryConfidence] = useState<MemoryConfidence>('MEDIUM');
  const [memoryContent, setMemoryContent] = useState('');
  const [memoryRationale, setMemoryRationale] = useState('');
  const [memoryTags, setMemoryTags] = useState('');
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | ''>('ACTIVE');
  const [memorySearch, setMemorySearch] = useState('');
  const [memoryTagFilter, setMemoryTagFilter] = useState('');
  const [supersedeTargets, setSupersedeTargets] = useState<Record<string, string>>({});
  const [promoteEntryId, setPromoteEntryId] = useState('');
  const [promoteDraft, setPromoteDraft] = useState({ title: '', context: '', decision: '' });
  const [adrTitle, setAdrTitle] = useState('');
  const [adrContext, setAdrContext] = useState('');
  const [adrDecision, setAdrDecision] = useState('');
  const [adrStatus, setAdrStatus] = useState<AdrStatus | ''>('');
  const [adrSearch, setAdrSearch] = useState('');
  const [adrSupersedeTargets, setAdrSupersedeTargets] = useState<Record<string, string>>({});
  const [linkPillar, setLinkPillar] = useState<Pillar>('ARCHON');
  const [linkSessionId, setLinkSessionId] = useState('');
  const [recentLinkSessions, setRecentLinkSessions] = useState<LinkableSession[]>([]);
  const [linkSessionsAvailable, setLinkSessionsAvailable] = useState(true);
  const [linkingSession, setLinkingSession] = useState(false);
  const [isDistillingAll, setIsDistillingAll] = useState(false);
  const [distillingSessionId, setDistillingSessionId] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<DistillationJob | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  useEffect(() => {
    setSelectedProjectId(projectId ?? '');
  }, [projectId]);

  useEffect(() => {
    const nextPillar = searchParams.get('linkPillar') as Pillar | null;
    const nextSessionId = searchParams.get('linkSessionId');
    if (nextPillar && PILLARS.includes(nextPillar)) setLinkPillar(nextPillar);
    if (nextSessionId) setLinkSessionId(nextSessionId);
  }, [searchParams]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLinkSessionsAvailable(true);
    const loadSessions = async () => {
      try {
        const sessions = linkPillar === 'ARCHON'
          ? (await listArchonSessions(token)).map(normalizeArchonSession)
          : linkPillar === 'SPECWEAVER'
            ? (await listSpecWeaverSessions(token)).map(normalizeSpecWeaverSession)
            : (await listReviewSessions(token)).map(normalizeLensSession);
        if (!cancelled) {
          setRecentLinkSessions(
            sessions
              .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
              .slice(0, 8),
          );
        }
      } catch {
        if (!cancelled) {
          setRecentLinkSessions([]);
          setLinkSessionsAvailable(false);
        }
      }
    };
    void loadSessions();
    return () => {
      cancelled = true;
    };
  }, [linkPillar, token]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    listProjects(token)
      .then((items) => {
        if (cancelled) return;
        setProjects(items);
        if (!projectId && items[0]?.id) {
          navigate(`/memoria/projects/${items[0].id}`, { replace: true });
        }
      })
      .catch((error) => emitToast((error as Error).message, 'error'))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate, projectId, token, refreshKey]);

  useEffect(() => {
    if (!token || !selectedProjectId) {
      setSummary(EMPTY_SUMMARY);
      setEntries([]);
      setAdrs([]);
      setLinks([]);
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const [nextSummary, nextEntries, nextAdrs, nextLinks, nextJobs] = await Promise.allSettled([
          getProjectSummary(token, selectedProjectId),
          listMemoryEntries(token, selectedProjectId, {
            status: memoryStatus || undefined,
            tag: memoryTagFilter || undefined,
            q: memorySearch || undefined,
          }),
          listAdrs(token, selectedProjectId, {
            status: adrStatus || undefined,
            q: adrSearch || undefined,
          }),
          listSessionLinks(token, selectedProjectId),
          listDistillationJobs(token, selectedProjectId),
        ]);
        if (cancelled) return;
        if (nextSummary.status === 'fulfilled') setSummary(nextSummary.value);
        if (nextEntries.status === 'fulfilled') setEntries(nextEntries.value);
        if (nextAdrs.status === 'fulfilled') setAdrs(nextAdrs.value);
        if (nextLinks.status === 'fulfilled') setLinks(nextLinks.value);
        if (nextJobs.status === 'fulfilled') {
          const jobs = nextJobs.value;
          setLastJob(jobs[0] ?? null);
        }

        const failure = [nextSummary, nextEntries, nextAdrs, nextLinks]
          .find((result): result is PromiseRejectedResult => result.status === 'rejected');
        if (failure) emitToast((failure.reason as Error).message, 'error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [token, selectedProjectId, refreshKey, memoryStatus, memoryTagFilter, memorySearch, adrStatus, adrSearch]);

  const reload = () => setRefreshKey((key) => key + 1);

  async function handleCreateProject() {
    if (!token || !projectName.trim()) return;
    const project = await createProject(token, projectName.trim(), projectDescription.trim());
    setProjectName('');
    setProjectDescription('');
    navigate(`/memoria/projects/${project.id}`);
    reload();
  }

  async function handleCreateMemory() {
    if (!token || !selectedProjectId || !memoryContent.trim()) return;
    await createMemoryEntry(token, selectedProjectId, {
      memoryType,
      tier: 'EPISODIC',
      confidence: memoryConfidence,
      content: memoryContent.trim(),
      rationale: memoryRationale.trim() || undefined,
      tags: splitTags(memoryTags),
    });
    setMemoryContent('');
    setMemoryRationale('');
    setMemoryTags('');
    reload();
  }

  async function handleTransition(entryId: string, action: 'mark-stale' | 'archive' | 'restore') {
    if (!token || !selectedProjectId) return;
    await transitionMemoryEntry(token, selectedProjectId, entryId, action);
    reload();
  }

  async function handleSupersede(entryId: string) {
    const supersedeTarget = supersedeTargets[entryId];
    if (!token || !selectedProjectId || !supersedeTarget) return;
    await supersedeMemoryEntry(token, selectedProjectId, entryId, supersedeTarget);
    setSupersedeTargets((current) => ({ ...current, [entryId]: '' }));
    reload();
  }

  async function handleCreateAdr() {
    if (!token || !selectedProjectId || !adrTitle.trim() || !adrContext.trim() || !adrDecision.trim()) return;
    await createAdr(token, selectedProjectId, {
      title: adrTitle.trim(),
      context: adrContext.trim(),
      decision: adrDecision.trim(),
    });
    setAdrTitle('');
    setAdrContext('');
    setAdrDecision('');
    reload();
  }

  async function handlePromote(entryId: string) {
    if (!token || !selectedProjectId || !promoteDraft.context.trim() || !promoteDraft.decision.trim()) return;
    await promoteMemoryEntry(token, selectedProjectId, entryId, {
      title: promoteDraft.title.trim() || undefined,
      context: promoteDraft.context.trim(),
      decision: promoteDraft.decision.trim(),
    });
    setPromoteEntryId('');
    setPromoteDraft({ title: '', context: '', decision: '' });
    reload();
  }

  function startPromote(entry: MemoryEntry) {
    setPromoteEntryId(entry.id);
    setPromoteDraft({
      title: truncate(entry.content, 80),
      context: entry.rationale ?? '',
      decision: entry.content,
    });
  }

  async function handleSupersedeAdr(adrId: string) {
    const adrSupersedeTarget = adrSupersedeTargets[adrId];
    if (!token || !selectedProjectId || !adrSupersedeTarget) return;
    await supersedeAdr(token, selectedProjectId, adrId, adrSupersedeTarget);
    setAdrSupersedeTargets((current) => ({ ...current, [adrId]: '' }));
    reload();
  }

  async function handleLinkSession() {
    const sessionId = linkSessionId.trim();
    if (!token || !selectedProjectId || !sessionId || linkingSession) return;
    setLinkingSession(true);
    try {
      await createSessionLink(token, selectedProjectId, linkPillar, sessionId);
      setLinks(await listSessionLinks(token, selectedProjectId));
      setLinkSessionId('');
      navigate(`/memoria/projects/${selectedProjectId}`, { replace: true });
      emitToast('Session linked to project.', 'info');
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        const problem = error.problem as (typeof error.problem & { projectId?: unknown; projectName?: unknown });
        if (typeof problem?.projectId === 'string' && projects.some((project) => project.id === problem.projectId)) {
          const projectName = typeof problem.projectName === 'string' ? problem.projectName : 'the linked project';
          emitToast(`Opening ${projectName}, where this session is already linked.`, 'info');
          navigate(`/memoria/projects/${problem.projectId}`);
          return;
        }
      }
      emitToast((error as Error).message, 'error');
    } finally {
      setLinkingSession(false);
    }
  }

  async function handleRemoveLink(linkId: string) {
    if (!token || !selectedProjectId) return;
    await removeSessionLink(token, selectedProjectId, linkId);
    reload();
  }

  async function handleDistillAll() {
    if (!token || !selectedProjectId || isDistillingAll) return;
    setIsDistillingAll(true);
    try {
      const job = await distillAllSessions(token, selectedProjectId);
      setLastJob(job);
      emitToast(
        `Distillation complete: ${job.totalPersisted} entries added, ${job.totalSuperseded} superseded`,
        job.status === 'COMPLETE' ? 'success' : 'warning',
      );
      reload();
    } catch (error) {
      emitToast((error as Error).message, 'error');
    } finally {
      setIsDistillingAll(false);
    }
  }

  async function handleDistillSession(pillar: Pillar, sessionId: string) {
    if (!token || !selectedProjectId || distillingSessionId) return;
    setDistillingSessionId(sessionId);
    try {
      const result = await distillSingleSession(token, selectedProjectId, pillar, sessionId);
      emitToast(
        `Distilled: ${result.entriesCreated} entries added, ${result.entriesSuperseded} superseded`,
        'success',
      );
      reload();
    } catch (error) {
      emitToast((error as Error).message, 'error');
    } finally {
      setDistillingSessionId(null);
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-50" data-testid="memoria-home-page">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 lg:px-6">
        <header className="flex flex-col gap-3 border-b border-slate-200 pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <PillarBadge pillar="memoria" />
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">Project memory</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Curate requirements, decisions, risks, constraints, and ADRs before automated distillation arrives.
            </p>
          </div>
          <div className="text-xs font-medium text-slate-500">{loading ? 'Syncing...' : 'Manual memory mode'}</div>
        </header>

        <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Projects</h2>
              <select
                className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={selectedProjectId}
                onChange={(event) => {
                  const nextProjectId = event.target.value;
                  setSelectedProjectId(nextProjectId);
                  if (nextProjectId) navigate(`/memoria/projects/${nextProjectId}`);
                }}
              >
                <option value="">Select a project</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
              </select>
              <div className="mt-3 space-y-2">
                <input className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="New project name" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
                <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Description" value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} />
                <button type="button" className="w-full rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handleCreateProject()}>
                  Create project
                </button>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Linked sessions</h2>
              <div className="mt-3 grid grid-cols-[1fr_1.4fr] gap-2">
                <select className="rounded-md border border-slate-300 px-2 py-2 text-sm" value={linkPillar} onChange={(event) => setLinkPillar(event.target.value as Pillar)}>
                  {PILLARS.map((pillar) => <option key={pillar} value={pillar}>{label(pillar)}</option>)}
                </select>
                <select
                  className="rounded-md border border-slate-300 px-2 py-2 text-sm"
                  value={recentLinkSessions.some((session) => session.id === linkSessionId) ? linkSessionId : ''}
                  onChange={(event) => setLinkSessionId(event.target.value)}
                  disabled={!linkSessionsAvailable || recentLinkSessions.length === 0}
                >
                  <option value="">Select recent session</option>
                  {recentLinkSessions.map((session) => (
                    <option key={session.id} value={session.id}>
                      {truncate(session.title, 34)} ({formatActivityDate(session.updatedAt)})
                    </option>
                  ))}
                </select>
              </div>
              {(!linkSessionsAvailable || recentLinkSessions.length === 0 || !recentLinkSessions.some((session) => session.id === linkSessionId)) && (
                <input
                  className="mt-2 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                  placeholder="Session UUID"
                  value={linkSessionId}
                  onChange={(event) => setLinkSessionId(event.target.value)}
                />
              )}
              <button type="button" className="mt-2 w-full rounded-md border border-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-[var(--color-pillar-memoria-bg)] disabled:cursor-not-allowed disabled:opacity-50" onClick={() => void handleLinkSession()} disabled={!selectedProjectId || !linkSessionId.trim() || linkingSession}>
                {linkingSession ? 'Linking...' : 'Link session'}
              </button>
              <div className="mt-3 space-y-2">
                {links.length === 0 ? <p className="text-xs text-slate-500">No linked sessions.</p> : (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-slate-700">
                        Sessions ({links.length})
                      </h3>
                      <button
                        type="button"
                        className="rounded-md bg-[var(--color-pillar-memoria-text)] px-2 py-1 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-40"
                        onClick={() => void handleDistillAll()}
                        disabled={isDistillingAll || !selectedProjectId}
                      >
                        {isDistillingAll ? 'Distilling...' : 'Distill all'}
                      </button>
                    </div>
                    {links.map((link) => (
                      <div key={link.id} className="rounded-md border border-slate-200 p-2 text-xs">
                        <div className="font-semibold text-slate-700">{label(link.pillar)}</div>
                        <div className="mt-1 flex items-center gap-1 text-slate-500">
                          <Link to={sourceHref(link.pillar, link.sessionId)} className="min-w-0 truncate hover:underline">{link.sessionId}</Link>
                          <CopyButton text={link.sessionId} title={`Copy ${label(link.pillar)} session ID`} />
                        </div>
                        <div className="mt-2 flex gap-2">
                          <button
                            type="button"
                            className="rounded-md border border-[var(--color-pillar-memoria-text)] px-2 py-1 text-xs font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-[var(--color-pillar-memoria-bg)] disabled:opacity-40"
                            onClick={() => void handleDistillSession(link.pillar, link.sessionId)}
                            disabled={distillingSessionId === link.sessionId || !selectedProjectId}
                          >
                            {distillingSessionId === link.sessionId ? 'Distilling...' : 'Distill'}
                          </button>
                          <button type="button" className="text-rose-700 hover:underline text-xs" onClick={() => void handleRemoveLink(link.id)}>Remove</button>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </section>

            {lastJob && (
              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-900">Last distillation</h2>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${
                    lastJob.status === 'COMPLETE' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' :
                    lastJob.status === 'PARTIAL' ? 'bg-amber-50 text-amber-700 ring-amber-200' :
                    'bg-rose-50 text-rose-700 ring-rose-200'
                  }`}>
                    {label(lastJob.status)}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md bg-slate-50 px-2 py-1.5">
                    <div className="text-slate-500">Extracted</div>
                    <div className="text-base font-semibold text-slate-900">{lastJob.totalCandidates}</div>
                  </div>
                  <div className="rounded-md bg-slate-50 px-2 py-1.5">
                    <div className="text-slate-500">Added</div>
                    <div className="text-base font-semibold text-emerald-700">{lastJob.totalPersisted}</div>
                  </div>
                  <div className="rounded-md bg-slate-50 px-2 py-1.5">
                    <div className="text-slate-500">Superseded</div>
                    <div className="text-base font-semibold text-amber-700">{lastJob.totalSuperseded}</div>
                  </div>
                  <div className="rounded-md bg-slate-50 px-2 py-1.5">
                    <div className="text-slate-500">Conflicts</div>
                    <div className="text-base font-semibold text-slate-700">{lastJob.totalConflicts}</div>
                  </div>
                </div>
                {lastJob.sessionResults.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {lastJob.sessionResults.map((result) => (
                      <div
                        key={result.sessionId}
                        className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1.5 text-xs"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                            result.status === 'SUCCESS' ? 'bg-emerald-500' :
                            result.status === 'FAILED' ? 'bg-rose-500' :
                            'bg-slate-400'
                          }`} />
                          <span className="text-slate-600 truncate">{label(result.pillar)}</span>
                        </div>
                        <div className="text-slate-500 shrink-0">
                          {result.persisted} added
                          {result.superseded > 0 && `, ${result.superseded} superseded`}
                          {result.error && (
                            <span className="text-rose-600 ml-1" title={result.error}>⚠</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
          </aside>

          <main className="space-y-5">
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">{selectedProject?.name ?? 'No project selected'}</h2>
                  <p className="text-sm text-slate-500">{selectedProject?.description || 'Create or select a project to curate memory.'}</p>
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ['Active', summary.activeFacts],
                  ['Stale', summary.staleFacts],
                  ['Decisions', summary.decisions],
                  ['Open risks', summary.openRisks],
                  ['ADRs', summary.adrCount],
                ].map(([name, value]) => (
                  <div key={name} className="rounded-md border border-slate-200 px-3 py-2">
                    <div className="text-xs font-medium text-slate-500">{name}</div>
                    <div className="mt-1 text-xl font-semibold text-slate-950">{value}</div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <h2 className="text-base font-semibold text-slate-950">Knowledge browser</h2>
                <div className="grid gap-2 sm:grid-cols-3">
                  <input className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Search memory" value={memorySearch} onChange={(event) => setMemorySearch(event.target.value)} />
                  <input className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Tag" value={memoryTagFilter} onChange={(event) => setMemoryTagFilter(event.target.value)} />
                  <select className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={memoryStatus} onChange={(event) => setMemoryStatus(event.target.value as MemoryStatus | '')}>
                    <option value="">All statuses</option>
                    {MEMORY_STATUSES.map((status) => <option key={status} value={status}>{label(status)}</option>)}
                  </select>
                </div>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-3">
                  {entries.length === 0 ? <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">No memory entries match the current filters.</p> : entries.map((entry) => (
                    <article key={entry.id} className="rounded-lg border border-slate-200 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${statusClass(entry.status)}`}>{label(entry.status)}</span>
                        <Badge value={label(entry.memoryType)} />
                        <Badge value={label(entry.confidence)} />
                        <span className="text-xs text-slate-500">Expires {formatDate(entry.expiresAt)}</span>
                      </div>
                      <p className="mt-3 text-sm text-slate-900">{entry.content}</p>
                      {entry.rationale && <p className="mt-2 text-xs text-slate-500">{entry.rationale}</p>}
                      {entry.sourcePillar && (
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                          {entry.sourceSessionId ? (
                            <Link
                              to={sourceHref(entry.sourcePillar, entry.sourceSessionId)}
                              className="rounded-full bg-slate-100 px-2 py-1 font-semibold text-slate-700 hover:bg-slate-200"
                            >
                              From {label(entry.sourcePillar)}
                            </Link>
                          ) : (
                            <span className="rounded-full bg-slate-100 px-2 py-1 font-semibold text-slate-700">From {label(entry.sourcePillar)}</span>
                          )}
                          {entry.sourceSessionId && <span className="font-mono text-slate-500">{entry.sourceSessionId.slice(0, 8)}</span>}
                        </div>
                      )}
                      {entry.tags && entry.tags.length > 0 && <div className="mt-2 text-xs text-slate-500">Tags: {entry.tags.join(', ')}</div>}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {entry.status === 'ACTIVE' && (
                          <>
                            <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'mark-stale')}>Mark stale</button>
                            <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'archive')}>Archive</button>
                            <button type="button" className="rounded-md border border-[var(--color-pillar-memoria-text)] px-2 py-1 text-xs font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-[var(--color-pillar-memoria-bg)]" onClick={() => startPromote(entry)}>Promote to ADR</button>
                          </>
                        )}
                        {entry.status === 'STALE' && (
                          <>
                            <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'restore')}>Restore</button>
                            <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'archive')}>Archive</button>
                          </>
                        )}
                        {entry.status === 'ARCHIVED' && (
                          <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'restore')}>Restore</button>
                        )}
                        {entry.status !== 'SUPERSEDED' && (
                          <details className="w-full pt-1">
                            <summary className="cursor-pointer text-xs font-semibold text-slate-500">More actions</summary>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <select
                                className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                                value={supersedeTargets[entry.id] ?? ''}
                                onChange={(event) => setSupersedeTargets((current) => ({ ...current, [entry.id]: event.target.value }))}
                              >
                                <option value="">Superseded by...</option>
                                {entries.filter((candidate) => candidate.id !== entry.id).map((candidate) => (
                                  <option key={candidate.id} value={candidate.id}>
                                    [{label(candidate.memoryType)}] {truncate(candidate.content, 35)} ({formatActivityDate(candidate.createdAt)})
                                  </option>
                                ))}
                              </select>
                              <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleSupersede(entry.id)}>Supersede</button>
                            </div>
                          </details>
                        )}
                      </div>
                    </article>
                  ))}
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">Create memory</h3>
                  <div className="mt-3 space-y-2">
                    <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={memoryType} onChange={(event) => setMemoryType(event.target.value as MemoryType)}>
                      {MEMORY_TYPES.map((type) => <option key={type} value={type}>{label(type)}</option>)}
                    </select>
                    <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={memoryConfidence} onChange={(event) => setMemoryConfidence(event.target.value as MemoryConfidence)}>
                      <option value="HIGH">High</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="LOW">Low</option>
                      <option value="INFERRED">Inferred</option>
                    </select>
                    <textarea className="min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Memory content" value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} />
                    <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Rationale" value={memoryRationale} onChange={(event) => setMemoryRationale(event.target.value)} />
                    <input className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Tags, comma separated" value={memoryTags} onChange={(event) => setMemoryTags(event.target.value)} />
                    <button type="button" className="w-full rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handleCreateMemory()} disabled={!selectedProjectId}>
                      Add memory
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <h2 className="text-base font-semibold text-slate-950">ADR register</h2>
                <div className="grid gap-2 sm:grid-cols-2">
                  <input className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Search ADRs" value={adrSearch} onChange={(event) => setAdrSearch(event.target.value)} />
                  <select className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={adrStatus} onChange={(event) => setAdrStatus(event.target.value as AdrStatus | '')}>
                    <option value="">All statuses</option>
                    {ADR_STATUSES.map((status) => <option key={status} value={status}>{label(status)}</option>)}
                  </select>
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-3">
                  {adrs.length === 0 ? <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">No ADRs match the current filters.</p> : adrs.map((adr) => (
                    <article key={adr.id} className="rounded-lg border border-slate-200 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-slate-950">ADR {adr.adrNumber}: {adr.title}</span>
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${statusClass(adr.status)}`}>{label(adr.status)}</span>
                      </div>
                      <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Decision</p>
                      <p className="mt-1 text-sm text-slate-800">{adr.decision}</p>
                      <p className="mt-2 text-xs text-slate-500">{adr.context}</p>
                      {adr.sourceMemoryEntryId && <p className="mt-2 text-xs text-[var(--color-pillar-memoria-text)]">Promoted from memory entry {adr.sourceMemoryEntryId.slice(0, 8)}</p>}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <select
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                          value={adrSupersedeTargets[adr.id] ?? ''}
                          onChange={(event) => setAdrSupersedeTargets((current) => ({ ...current, [adr.id]: event.target.value }))}
                        >
                          <option value="">Superseded by...</option>
                          {adrs.filter((candidate) => candidate.id !== adr.id).map((candidate) => (
                            <option key={candidate.id} value={candidate.id}>
                              ADR {candidate.adrNumber}: {truncate(candidate.title, 40)}
                            </option>
                          ))}
                        </select>
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleSupersedeAdr(adr.id)}>Supersede ADR</button>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">Create ADR</h3>
                  <div className="mt-3 space-y-2">
                    <input className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Title" value={adrTitle} onChange={(event) => setAdrTitle(event.target.value)} />
                    <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Context" value={adrContext} onChange={(event) => setAdrContext(event.target.value)} />
                    <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Decision" value={adrDecision} onChange={(event) => setAdrDecision(event.target.value)} />
                    <button type="button" className="w-full rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handleCreateAdr()} disabled={!selectedProjectId}>
                      Create ADR
                    </button>
                  </div>
                </div>

                {promoteEntryId && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                    <h3 className="text-sm font-semibold text-rose-950">Promote memory to ADR</h3>
                    <div className="mt-3 space-y-2">
                      <input className="w-full rounded-md border border-rose-200 px-3 py-2 text-sm" placeholder="Title" value={promoteDraft.title} onChange={(event) => setPromoteDraft((current) => ({ ...current, title: event.target.value }))} />
                      <textarea className="min-h-20 w-full rounded-md border border-rose-200 px-3 py-2 text-sm" placeholder="Context" value={promoteDraft.context} onChange={(event) => setPromoteDraft((current) => ({ ...current, context: event.target.value }))} />
                      <textarea className="min-h-20 w-full rounded-md border border-rose-200 px-3 py-2 text-sm" placeholder="Decision" value={promoteDraft.decision} onChange={(event) => setPromoteDraft((current) => ({ ...current, decision: event.target.value }))} />
                      <div className="grid grid-cols-2 gap-2">
                        <button type="button" className="rounded-md border border-rose-200 bg-white px-3 py-2 text-sm font-semibold text-rose-800 hover:bg-rose-100" onClick={() => { setPromoteEntryId(''); setPromoteDraft({ title: '', context: '', decision: '' }); }}>Cancel</button>
                        <button type="button" className="rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handlePromote(promoteEntryId)}>Promote</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}
