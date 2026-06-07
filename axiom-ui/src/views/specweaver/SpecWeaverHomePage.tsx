import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PillarBadge } from '../../components/PillarBadge';
import { useStore } from '../../store/useStore';
import { useSpecWeaverStore } from '../../store/useSpecWeaverStore';
import type { Session, SessionStatus } from '../../api/specweaver';

const STATUS_LABELS: Record<SessionStatus, string> = {
  ACTIVE: 'Active',
  PROCESSING: 'Processing',
  PACKAGE_READY: 'Package Ready',
  SENT_TO_ARCHON: 'Sent to Archon',
};

function statusClass(status: SessionStatus): string {
  if (status === 'PACKAGE_READY') return 'bg-[var(--color-pillar-specweaver-bg)] text-[var(--color-pillar-specweaver-text)]';
  if (status === 'SENT_TO_ARCHON') return 'bg-gray-100 text-gray-700';
  if (status === 'PROCESSING') return 'bg-amber-50 text-amber-700';
  return 'bg-gray-50 text-gray-600';
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

/**
 * SpecWeaver landing page with quick start CTA and recent sessions.
 */
export function SpecWeaverHomePage() {
  const navigate = useNavigate();
  const token = useStore((state) => state.token)!;
  const sessions = useSpecWeaverStore((state) => state.sessions);
  const loadSessions = useSpecWeaverStore((state) => state.loadSessions);
  const createSession = useSpecWeaverStore((state) => state.createSession);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    document.title = 'SpecWeaver — Requirements Intelligence | Axiom';
  }, []);

  useEffect(() => {
    void loadSessions(token);
  }, [loadSessions, token]);

  const handleCreateSession = async () => {
    setIsCreating(true);
    try {
      const session = await createSession(token, undefined);
      navigate(`/specweaver/sessions/${session.id}`);
    } finally {
      setIsCreating(false);
    }
  };

  const recentSessions: Session[] = sessions.slice(0, 3);

  return (
    <div className="specweaver-scope h-full overflow-y-auto bg-gray-50" data-testid="specweaver-home-page">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <header className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <PillarBadge pillar="specweaver" />
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">SpecWeaver</h1>
              <p className="text-sm font-medium text-gray-500">Requirements Intelligence</p>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-700 leading-relaxed max-w-3xl">
            Transform messy stakeholder documents into clean, structured, architecture-ready requirements.
          </p>
        </header>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
            <p className="text-lg font-semibold text-gray-900">Start a new session</p>
            <p className="mt-2 text-sm text-gray-700 leading-relaxed">
              Upload meeting notes, emails, or documents. SpecWeaver extracts and classifies your requirements automatically.
            </p>
            <button
              type="button"
              onClick={handleCreateSession}
              disabled={isCreating}
              className="btn btn-primary mt-4 inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              data-testid="specweaver-start-session"
            >
              {isCreating ? 'Creating...' : 'New Requirements Session ->'}
            </button>
          </div>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-gray-900">Recent sessions</h2>
            {recentSessions.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No sessions yet. Start your first one above.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {recentSessions.map((session) => {
                  const requirementCount = session.status === 'PACKAGE_READY' ? 'Package ready' : 'In progress';
                  return (
                    <Link
                      key={session.id}
                      to={`/specweaver/sessions/${session.id}`}
                      className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 hover:bg-gray-50"
                      data-testid={`specweaver-home-recent-${session.id}`}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-gray-800">{session.title?.trim() || 'Untitled session'}</p>
                        <p className="text-xs text-gray-500">{requirementCount} · {formatDate(session.createdAt)}</p>
                      </div>
                      <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${statusClass(session.status)}`}>
                        {STATUS_LABELS[session.status]}
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
            <Link to="/specweaver/sessions" className="mt-3 inline-flex text-sm font-medium text-[var(--color-pillar-specweaver)]">
              View all sessions {'->'}
            </Link>
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="text-sm font-semibold text-gray-900">HOW IT WORKS</h2>
          <ol className="mt-3 space-y-4 text-sm text-gray-700">
            <li>
              <p className="font-semibold text-gray-900">1. Upload your documents</p>
              <p className="mt-1">Paste text, upload PDFs or Word documents. SpecWeaver accepts meeting notes, emails, workshop outputs, and informal bullet lists.</p>
            </li>
            <li>
              <p className="font-semibold text-gray-900">2. Extract and classify</p>
              <p className="mt-1">The AI pipeline extracts every requirement, deduplicates across documents, identifies what is missing, and flags contradictions.</p>
            </li>
            <li>
              <p className="font-semibold text-gray-900">3. Review and send to Archon</p>
              <p className="mt-1">Review the requirements package, check gaps and conflicts, then open it directly in Archon for architecture analysis.</p>
            </li>
          </ol>
        </section>
      </div>
    </div>
  );
}
