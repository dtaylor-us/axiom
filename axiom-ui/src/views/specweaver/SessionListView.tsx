import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useStore } from '../../store/useStore';
import { useSpecWeaverStore } from '../../store/useSpecWeaverStore';
import type { Session, SessionStatus } from '../../api/specweaver';
import { PillarBadge } from '../../components/PillarBadge';

const STATUS_LABELS: Record<SessionStatus, string> = {
  ACTIVE: 'Active',
  PROCESSING: 'Processing',
  PACKAGE_READY: 'Package Ready',
  SENT_TO_ARCHON: 'Sent to Archon',
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value));
}

function statusClass(status: SessionStatus): string {
  if (status === 'PACKAGE_READY') return 'bg-accent/10 text-accent ring-accent/20';
  if (status === 'SENT_TO_ARCHON') return 'bg-gray-100 text-gray-700 ring-gray-200';
  if (status === 'PROCESSING') return 'bg-amber-50 text-amber-700 ring-amber-200';
  return 'bg-gray-50 text-gray-600 ring-gray-200';
}

/**
 * Displays the SpecWeaver session index and starts new extraction sessions.
 */
export function SessionListView() {
  const navigate = useNavigate();
  const token = useStore((state) => state.token)!;
  const sessions = useSpecWeaverStore((state) => state.sessions);
  const error = useSpecWeaverStore((state) => state.error);
  const loadSessions = useSpecWeaverStore((state) => state.loadSessions);
  const createSession = useSpecWeaverStore((state) => state.createSession);
  const clearError = useSpecWeaverStore((state) => state.clearError);
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

  const renderSession = (session: Session) => {
    const documentCount = Array.isArray(session.documents) ? session.documents.length : 0;
    return (
    <button
      key={session.id}
      type="button"
      onClick={() => navigate(`/specweaver/sessions/${session.id}`)}
      className="w-full rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors hover:bg-gray-50"
      data-testid={`specweaver-session-${session.id}`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-[15px] font-semibold text-gray-900">
            {session.title?.trim() || 'Untitled session'}
          </h2>
          <p className="mt-1 text-[12px] text-gray-500">
            {documentCount} document{documentCount === 1 ? '' : 's'} · Created {formatDate(session.createdAt)}
          </p>
        </div>
        <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ${statusClass(session.status)}`}>
          {STATUS_LABELS[session.status]}
        </span>
      </div>
    </button>
    );
  };

  return (
    <div className="specweaver-scope h-full overflow-y-auto bg-gray-50" data-testid="specweaver-session-list">
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-2">
              <PillarBadge pillar="specweaver" />
            </div>
            <h1 className="text-[20px] font-semibold text-gray-900">Requirements Sessions</h1>
            <p className="mt-1 text-[13px] text-gray-500">
              Convert requirement evidence into typed architecture input.
            </p>
          </div>
          <button
            type="button"
            onClick={handleCreateSession}
            disabled={isCreating}
            className="btn btn-primary inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-[13px] font-semibold disabled:opacity-50"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M8 3v10M3 8h10" />
            </svg>
            {isCreating ? 'Creating…' : 'New Session'}
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-700" role="alert">
            {error}
            <button type="button" className="ml-2 underline" onClick={clearError}>
              Dismiss
            </button>
          </div>
        )}

        {sessions.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 bg-white p-8 text-center">
            <p className="text-[13px] text-gray-500">
              No sessions yet. Create your first session to start extracting requirements.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map(renderSession)}
          </div>
        )}
      </div>
    </div>
  );
}
