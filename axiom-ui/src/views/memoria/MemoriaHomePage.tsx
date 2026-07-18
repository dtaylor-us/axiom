import { useEffect, useMemo, useState } from 'react';

import {
  createAdr,
  createMemoryEntry,
  createProject,
  createSessionLink,
  getProjectSummary,
  listAdrs,
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
  type MemoryConfidence,
  type MemoryEntry,
  type MemoryStatus,
  type MemoryTier,
  type MemoryType,
  type MemoriaProject,
  type Pillar,
  type ProjectMemorySummary,
  type SessionLink,
} from '../../api/memoria';
import { PillarBadge } from '../../components/PillarBadge';
import { emitToast } from '../../components/Toast';
import { useStore } from '../../store/useStore';

const MEMORY_TYPES: MemoryType[] = ['DECISION', 'REQUIREMENT', 'RISK', 'QUALITY_SCORE', 'ASSUMPTION', 'CONSTRAINT', 'SESSION_SUMMARY'];
const MEMORY_STATUSES: MemoryStatus[] = ['ACTIVE', 'STALE', 'SUPERSEDED', 'ARCHIVED'];
const ADR_STATUSES: AdrStatus[] = ['PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'DEPRECATED'];
const PILLARS: Pillar[] = ['SPECWEAVER', 'ARCHON', 'LENS'];

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
  const [projects, setProjects] = useState<MemoriaProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [summary, setSummary] = useState<ProjectMemorySummary>(EMPTY_SUMMARY);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [adrs, setAdrs] = useState<ArchitectureDecision[]>([]);
  const [links, setLinks] = useState<SessionLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [memoryType, setMemoryType] = useState<MemoryType>('DECISION');
  const [memoryTier, setMemoryTier] = useState<MemoryTier>('EPISODIC');
  const [memoryConfidence, setMemoryConfidence] = useState<MemoryConfidence>('MEDIUM');
  const [memoryContent, setMemoryContent] = useState('');
  const [memoryRationale, setMemoryRationale] = useState('');
  const [memoryTags, setMemoryTags] = useState('');
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | ''>('ACTIVE');
  const [memorySearch, setMemorySearch] = useState('');
  const [memoryTagFilter, setMemoryTagFilter] = useState('');
  const [supersedeTargets, setSupersedeTargets] = useState<Record<string, string>>({});
  const [promoteEntryId, setPromoteEntryId] = useState('');
  const [adrTitle, setAdrTitle] = useState('');
  const [adrContext, setAdrContext] = useState('');
  const [adrDecision, setAdrDecision] = useState('');
  const [adrStatus, setAdrStatus] = useState<AdrStatus | ''>('');
  const [adrSearch, setAdrSearch] = useState('');
  const [adrSupersedeTargets, setAdrSupersedeTargets] = useState<Record<string, string>>({});
  const [linkPillar, setLinkPillar] = useState<Pillar>('ARCHON');
  const [linkSessionId, setLinkSessionId] = useState('');

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    listProjects(token)
      .then((items) => {
        if (cancelled) return;
        setProjects(items);
        setSelectedProjectId((current) => current || items[0]?.id || '');
      })
      .catch((error) => emitToast((error as Error).message, 'error'))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, refreshKey]);

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
        const [nextSummary, nextEntries, nextAdrs, nextLinks] = await Promise.all([
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
        ]);
        if (cancelled) return;
        setSummary(nextSummary);
        setEntries(nextEntries);
        setAdrs(nextAdrs);
        setLinks(nextLinks);
      } catch (error) {
        if (!cancelled) emitToast((error as Error).message, 'error');
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
    setSelectedProjectId(project.id);
    reload();
  }

  async function handleCreateMemory() {
    if (!token || !selectedProjectId || !memoryContent.trim()) return;
    await createMemoryEntry(token, selectedProjectId, {
      memoryType,
      tier: memoryTier,
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
    if (!token || !selectedProjectId || !adrContext.trim() || !adrDecision.trim()) return;
    await promoteMemoryEntry(token, selectedProjectId, entryId, {
      title: adrTitle.trim() || undefined,
      context: adrContext.trim(),
      decision: adrDecision.trim(),
    });
    setPromoteEntryId('');
    setAdrTitle('');
    setAdrContext('');
    setAdrDecision('');
    reload();
  }

  async function handleSupersedeAdr(adrId: string) {
    const adrSupersedeTarget = adrSupersedeTargets[adrId];
    if (!token || !selectedProjectId || !adrSupersedeTarget) return;
    await supersedeAdr(token, selectedProjectId, adrId, adrSupersedeTarget);
    setAdrSupersedeTargets((current) => ({ ...current, [adrId]: '' }));
    reload();
  }

  async function handleLinkSession() {
    if (!token || !selectedProjectId || !linkSessionId.trim()) return;
    await createSessionLink(token, selectedProjectId, linkPillar, linkSessionId.trim());
    setLinkSessionId('');
    reload();
  }

  async function handleRemoveLink(linkId: string) {
    if (!token || !selectedProjectId) return;
    await removeSessionLink(token, selectedProjectId, linkId);
    reload();
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
                onChange={(event) => setSelectedProjectId(event.target.value)}
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
                <input className="rounded-md border border-slate-300 px-2 py-2 text-sm" placeholder="Session UUID" value={linkSessionId} onChange={(event) => setLinkSessionId(event.target.value)} />
              </div>
              <button type="button" className="mt-2 w-full rounded-md border border-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-[var(--color-pillar-memoria-bg)]" onClick={() => void handleLinkSession()} disabled={!selectedProjectId}>
                Link session
              </button>
              <div className="mt-3 space-y-2">
                {links.length === 0 ? <p className="text-xs text-slate-500">No linked sessions.</p> : links.map((link) => (
                  <div key={link.id} className="rounded-md border border-slate-200 p-2 text-xs">
                    <div className="font-semibold text-slate-700">{label(link.pillar)}</div>
                    <div className="mt-1 truncate text-slate-500">{link.sessionId}</div>
                    <button type="button" className="mt-2 text-rose-700 hover:underline" onClick={() => void handleRemoveLink(link.id)}>Remove</button>
                  </div>
                ))}
              </div>
            </section>
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
                      {entry.tags && entry.tags.length > 0 && <div className="mt-2 text-xs text-slate-500">Tags: {entry.tags.join(', ')}</div>}
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'mark-stale')}>Mark stale</button>
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'archive')}>Archive</button>
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleTransition(entry.id, 'restore')}>Restore</button>
                        <select
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                          value={supersedeTargets[entry.id] ?? ''}
                          onChange={(event) => setSupersedeTargets((current) => ({ ...current, [entry.id]: event.target.value }))}
                        >
                          <option value="">Superseded by...</option>
                          {entries.filter((candidate) => candidate.id !== entry.id).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.content.slice(0, 42)}</option>)}
                        </select>
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleSupersede(entry.id)}>Supersede</button>
                        <button type="button" className="rounded-md border border-[var(--color-pillar-memoria-text)] px-2 py-1 text-xs font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-[var(--color-pillar-memoria-bg)]" onClick={() => setPromoteEntryId(entry.id)}>Promote to ADR</button>
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
                    <div className="grid grid-cols-2 gap-2">
                      <select className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={memoryTier} onChange={(event) => setMemoryTier(event.target.value as MemoryTier)}>
                        <option value="EPISODIC">Episodic</option>
                        <option value="SEMANTIC">Semantic</option>
                      </select>
                      <select className="rounded-md border border-slate-300 px-3 py-2 text-sm" value={memoryConfidence} onChange={(event) => setMemoryConfidence(event.target.value as MemoryConfidence)}>
                        <option value="HIGH">High</option>
                        <option value="MEDIUM">Medium</option>
                        <option value="LOW">Low</option>
                        <option value="INFERRED">Inferred</option>
                      </select>
                    </div>
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
                          {adrs.filter((candidate) => candidate.id !== adr.id).map((candidate) => <option key={candidate.id} value={candidate.id}>ADR {candidate.adrNumber}</option>)}
                        </select>
                        <button type="button" className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void handleSupersedeAdr(adr.id)}>Supersede ADR</button>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">{promoteEntryId ? 'Promote memory to ADR' : 'Create ADR'}</h3>
                  <div className="mt-3 space-y-2">
                    <input className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Title" value={adrTitle} onChange={(event) => setAdrTitle(event.target.value)} />
                    <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Context" value={adrContext} onChange={(event) => setAdrContext(event.target.value)} />
                    <textarea className="min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Decision" value={adrDecision} onChange={(event) => setAdrDecision(event.target.value)} />
                    {promoteEntryId ? (
                      <div className="grid grid-cols-2 gap-2">
                        <button type="button" className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-white" onClick={() => setPromoteEntryId('')}>Cancel</button>
                        <button type="button" className="rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handlePromote(promoteEntryId)}>Promote</button>
                      </div>
                    ) : (
                      <button type="button" className="w-full rounded-md bg-[var(--color-pillar-memoria-text)] px-3 py-2 text-sm font-semibold text-white hover:bg-rose-800" onClick={() => void handleCreateAdr()} disabled={!selectedProjectId}>
                        Create ADR
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}
