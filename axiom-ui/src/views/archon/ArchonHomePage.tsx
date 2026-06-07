import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { listSessions } from '../../api/sessions';
import { PillarBadge } from '../../components/PillarBadge';
import { useStore } from '../../store/useStore';
import type { SessionSummary } from '../../types/api';

function formatDate(value?: string): string {
  if (!value) return 'Unknown date';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

/**
 * Archon landing page with entry CTA and recent analyses list.
 */
export function ArchonHomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = useStore((state) => state.token);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const prefillMessage = useMemo(() => {
    const state = location.state as { prefillMessage?: string; source?: string; sessionId?: string } | null;
    return state?.prefillMessage;
  }, [location.state]);

  useEffect(() => {
    if (!token) return;
    setIsLoading(true);
    listSessions(token)
      .then((items) => setSessions(items.slice(0, 3)))
      .catch(() => setSessions([]))
      .finally(() => setIsLoading(false));
  }, [token]);

  const handleStartAnalysis = () => {
    if (prefillMessage) {
      navigate('/archon/chat', { state: location.state });
      return;
    }
    navigate('/archon/chat');
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50" data-testid="archon-home-page">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <header className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <PillarBadge pillar="archon" />
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Archon</h1>
              <p className="text-sm font-medium text-gray-500">Architecture Reasoning</p>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-700 leading-relaxed max-w-3xl">
            Turn your requirements into a complete architecture analysis — decisions, diagrams, trade-offs, and governance rules.
          </p>
        </header>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
            <p className="text-lg font-semibold text-gray-900">Start a new analysis</p>
            <p className="mt-2 text-sm text-gray-700 leading-relaxed">
              Describe your system and Archon runs a 13-stage AI pipeline to produce your architecture.
            </p>
            <button
              type="button"
              onClick={handleStartAnalysis}
              className="mt-4 inline-flex items-center rounded-lg bg-[var(--color-pillar-archon)] px-4 py-2.5 text-sm font-semibold text-white"
              data-testid="archon-start-analysis"
            >
              New Architecture Analysis {'->'}
            </button>
          </div>

          <div className="mt-6">
            <h2 className="text-sm font-semibold text-gray-900">Recent analyses</h2>
            {isLoading ? (
              <p className="mt-3 text-sm text-gray-500">Loading recent analyses...</p>
            ) : sessions.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No analyses yet. Start your first one above.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {sessions.map((session) => (
                  <Link
                    key={session.id}
                    to={`/archon/conversations/${session.id}`}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2.5 hover:bg-gray-50"
                    data-testid={`archon-recent-${session.id}`}
                  >
                    <span className="truncate text-sm font-medium text-gray-800">{session.title || 'Untitled analysis'}</span>
                    <span className="ml-3 shrink-0 text-xs text-gray-500">{formatDate(session.createdAt)}</span>
                  </Link>
                ))}
              </div>
            )}
            <Link to="/archon/chat" className="mt-3 inline-flex text-sm font-medium text-[var(--color-pillar-archon)]">
              View all {'->'}
            </Link>
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="text-sm font-semibold text-gray-900">WHAT ARCHON PRODUCES</h2>
          <p className="mt-2 text-sm text-gray-700">13 pipeline stages. One complete architecture.</p>
          <p className="mt-3 text-sm text-gray-700 leading-relaxed">
            Requirement parsing {'->'} Challenge identification {'->'} Characteristic inference {'->'} Conflict analysis {'->'} Architecture generation {'->'} Diagram generation {'->'} Trade-off analysis {'->'} ADL rules {'->'} Weakness analysis {'->'} FMEA {'->'} Architecture review {'->'} Governance score
          </p>
        </section>
      </div>
    </div>
  );
}
