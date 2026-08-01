import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { listSessions } from '../../api/sessions';
import { PillarBadge } from '../../components/PillarBadge';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';
import { useStore } from '../../store/useStore';
import type { SessionSummary } from '../../types/api';

const PIPELINE_STAGES = [
  '1 Req parsing',
  '2 Challenge',
  '3 Scenarios',
  '4 Characteristics',
  '4b Tactics',
  '5 Conflicts',
  '6 Architecture',
  '6b Buy/build',
  '7 Diagrams',
  '8 Trade-offs',
  '9 ADL',
  '10 Weakness',
  '11 FMEA',
];

const ARCHON_FEATURES = [
  {
    icon: '🏗',
    iconBg: '#f0fdf4',
    title: 'Architecture style selection',
    description:
      'Scores all 8 Mark Richards styles against inferred characteristics. Applies veto rules. Never defaults to layered without justification.',
  },
  {
    icon: '📋',
    iconBg: '#f0fdf4',
    title: 'Executable ADL governance',
    description: 'Generates Architecture Definition Language rules that compile to ArchUnit, PyTestArch, and Semgrep tests.',
  },
  {
    icon: '⚠️',
    iconBg: '#fefce8',
    title: 'FMEA risk analysis',
    description:
      'Risk Priority Numbers for each failure mode. Cascading failure chains across service boundaries identified.',
  },
  {
    icon: '🛒',
    iconBg: '#f0fdf4',
    title: 'Buy vs build decisions',
    description: 'Names real products for each component. Warns when recommendations conflict with your stated preferences.',
  },
  {
    icon: '⚡',
    iconBg: '#fefce8',
    title: 'Architecture tactics',
    description:
      'Bass, Clements, Kazman catalog recommendations per quality attribute. Identifies which are already addressed.',
  },
  {
    icon: '📊',
    iconBg: '#f0fdf4',
    title: 'Governance score 0-100',
    description: 'An independent review agent challenges assumptions and scores across 5 dimensions with confidence level.',
  },
];

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
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="archon-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="pillar-hero-badge">
            <PillarBadge pillar="archon" />
          </div>
          <h1>Architecture reasoning, 13 stages deep.</h1>
          <p>
            Not a diagram generator. A governed reasoning pipeline that challenges your requirements, selects an
            architecture style with evidence, generates executable governance rules, and scores the result.
          </p>
        </section>

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

        <section className="landing-section--compact">
          <SectionHeading
            title="Pipeline stages"
            subtitle="Every run executes all 13 stages in sequence."
            accent="var(--color-pillar-archon)"
          />
          <div className="pipeline-stages-row">
            {PIPELINE_STAGES.map((stage) => (
              <Fragment key={stage}>
                <span className="pipeline-stage-chip">{stage}</span>
                <span className="pipeline-arrow">›</span>
              </Fragment>
            ))}
            <span className="pipeline-stage-chip governance">★ 12 Review + Score</span>
          </div>
        </section>

        <section className="landing-section--compact">
          <SectionHeading title="What Archon produces" accent="var(--color-pillar-archon)" />
          <div className="feature-cards-grid">
            {ARCHON_FEATURES.map((card) => (
              <FeatureCard key={card.title} {...card} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
