import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { listReviewSessions, type ReviewSession } from '../../api/lens';
import { PillarBadge } from '../../components/PillarBadge';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';
import { useStore } from '../../store/useStore';

const STEPS = [
  {
    icon: '1',
    iconBg: '#fff7ed',
    title: 'Submit evidence',
    description: 'Capture architecture facts, diagrams, decisions, and requirements evidence.',
  },
  {
    icon: '2',
    iconBg: '#fff7ed',
    title: 'Fill the gaps',
    description: 'Answer targeted Lens questions or proceed with unresolved gaps captured as findings.',
  },
  {
    icon: '3',
    iconBg: '#fff7ed',
    title: 'Receive report',
    description: 'Get a full architecture review with findings, risk register, and prioritized recommendations.',
  },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function statusBadge(status: ReviewSession['status']): string {
  if (status === 'COMPLETE') return 'bg-emerald-100 text-emerald-800';
  if (status === 'IN_REVIEW') return 'bg-amber-100 text-amber-800';
  if (status === 'READY_FOR_REVIEW') return 'bg-sky-100 text-sky-800';
  if (status === 'GAP_ELICITATION') return 'bg-orange-100 text-orange-800';
  return 'bg-gray-100 text-gray-700';
}

export function LensHomePage() {
  const navigate = useNavigate();
  const token = useStore((state) => state.token);
  const [sessions, setSessions] = useState<ReviewSession[]>([]);

  useEffect(() => {
    if (!token) return;
    void listReviewSessions(token).then((items) => setSessions(items.slice(0, 3))).catch(() => setSessions([]));
  }, [token]);

  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="lens-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="pillar-hero-badge">
            <PillarBadge pillar="lens" />
          </div>
          <h1>
            Architecture reviews,
            {' '}
            <span className="gradient-text-amber">framework-grounded.</span>
          </h1>
          <p>
            Submit your architecture and Lens evaluates it against the Azure Well-Architected Framework, SEI ATAM, and
            architecture quality principles. It asks clarifying questions to fill gaps, then generates a comprehensive
            review report with a risk register and prioritised recommendations.
          </p>
          <div className="hero-actions">
            <button type="button" className="btn btn-primary" style={{ background: 'var(--color-pillar-lens)' }} onClick={() => navigate('/lens/new')}>
              New architecture review →
            </button>
          </div>
        </section>

        <section className="landing-section--compact">
          <SectionHeading title="Three-step review flow" accent="var(--color-pillar-lens)" />
          <div className="feature-cards-grid">
            {STEPS.map((card) => <FeatureCard key={card.title} {...card} />)}
          </div>
        </section>

        <section className="landing-section--compact">
          <SectionHeading title="Recent reviews" accent="var(--color-pillar-lens)" />
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <p className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-600">No reviews yet.</p>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm hover:bg-gray-50"
                  onClick={() => navigate(`/lens/sessions/${session.id}`)}
                  data-testid={`lens-home-session-${session.id}`}
                >
                  <span className="min-w-0 truncate font-medium text-gray-800">{session.title}</span>
                  <span className="flex items-center gap-2 shrink-0">
                    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${statusBadge(session.status)}`}>
                      {session.status}
                    </span>
                    <span className="text-xs text-gray-500">{formatDate(session.createdAt)}</span>
                  </span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="landing-section--compact">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gray-500">Azure Well-Architected · SEI ATAM · ISO/IEC 25010</p>
        </section>
      </div>
    </div>
  );
}
