import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { listReviewSessions, type ReviewSession } from '../../api/lens';
import { PillarBadge } from '../../components/PillarBadge';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';
import { useStore } from '../../store/useStore';

const FEATURES = [
  {
    icon: '🧭',
    iconBg: '#fff7ed',
    title: 'Evidence-grounded reviews',
    description: 'Lens evaluates submitted architecture evidence against structured review frameworks and records what is actually supported.',
  },
  {
    icon: '❓',
    iconBg: '#fff7ed',
    title: 'Gap elicitation',
    description: 'Targeted questions close the most important unknowns. Skipped answers are preserved and unresolved gaps become findings.',
  },
  {
    icon: '🛡',
    iconBg: '#fff7ed',
    title: 'Risk register',
    description: 'Produces a prioritized register of architecture risks with severity, likelihood, area, and mitigation strategy.',
  },
  {
    icon: '📊',
    iconBg: '#fff7ed',
    title: 'Framework scorecards',
    description: 'Covers Azure WAF, SEI ATAM, ISO/IEC 25010, and TOGAF principles with a structured review report.',
  },
  {
    icon: '🧱',
    iconBg: '#fff7ed',
    title: 'Structural analysis',
    description: 'Scores coupling, cohesion, dependency direction, and boundary clarity from the evidence you provide.',
  },
  {
    icon: '🧾',
    iconBg: '#fff7ed',
    title: 'Actionable roadmap',
    description: 'Recommendation output stays specific and bounded so the user always has a next step, never a dead end.',
  },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
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
          <SectionHeading title="How it works" accent="var(--color-pillar-lens)" />
          <div className="feature-cards-grid">
            {FEATURES.map((card) => <FeatureCard key={card.title} {...card} />)}
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
                  <span className="shrink-0 text-xs text-gray-500">{formatDate(session.createdAt)}</span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="landing-section--compact">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gray-500">Azure Well-Architected · SEI ATAM · ISO/IEC 25010 · TOGAF</p>
        </section>
      </div>
    </div>
  );
}
