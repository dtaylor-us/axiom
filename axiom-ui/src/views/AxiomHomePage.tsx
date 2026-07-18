import { Fragment } from 'react';
import { useNavigate } from 'react-router-dom';

import { PillarBadge } from '../components/PillarBadge';
import { PillarIcon, type PillarId } from '../components/PillarIcon';
import { SectionHeading } from '../components/landing/SectionHeading';
import { useStore } from '../store/useStore';

interface PillarLandingCard {
  id: Exclude<PillarId, 'axiom'>;
  name: string;
  tagline: string;
  description: string;
  path: string;
  available: boolean;
  iconBg: string;
}

const PILLARS: PillarLandingCard[] = [
  {
    id: 'specweaver',
    name: 'SpecWeaver',
    tagline: 'Requirements Intelligence',
    description: 'Transform messy stakeholder documents into clean, structured, architecture-ready requirements.',
    path: '/specweaver',
    available: true,
    iconBg: 'var(--color-pillar-specweaver-bg)',
  },
  {
    id: 'archon',
    name: 'Archon',
    tagline: 'Architecture Reasoning',
    description: 'Turn requirements into a full architecture analysis in minutes.',
    path: '/archon',
    available: true,
    iconBg: 'var(--color-pillar-archon-bg)',
  },
  {
    id: 'lens',
    name: 'Lens',
    tagline: 'Architecture Review Intelligence',
    description: 'Evaluate existing architecture decisions against established review frameworks.',
    path: '/lens',
    available: true,
    iconBg: 'var(--color-pillar-lens-bg)',
  },
];

const WORKFLOW_STEPS = [
  {
    num: '1',
    title: 'SpecWeaver',
    body: 'Upload requirements docs. Get a structured, traceable package.',
    color: 'var(--color-pillar-specweaver)',
  },
  {
    num: '2',
    title: 'Archon',
    body: 'Run the 13-stage pipeline. Get architecture decisions and governance rules.',
    color: 'var(--color-pillar-archon)',
  },
  {
    num: '3',
    title: 'Lens',
    body: 'Review architectures against evidence. Gaps become findings, never blockers.',
    color: 'var(--color-pillar-lens)',
  },
];

/**
 * Platform landing page introducing all pillars and the end-to-end workflow.
 */
export function AxiomHomePage() {
  const navigate = useNavigate();
  const token = useStore((s) => s.token);

  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="axiom-home-page">
      {/* Top navigation — visible when the app shell sidebar is not rendered (unauthenticated) */}
      {!token && (
        <header className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-3">
            <div className="flex items-center gap-2">
              <PillarIcon pillar="axiom" size={20} />
              <span className="text-[15px] font-bold tracking-tight text-gray-900">Axiom</span>
            </div>
            <nav className="hidden items-center gap-1 sm:flex">
              {PILLARS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => navigate(p.path)}
                  className="rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </nav>
            <button
              type="button"
              className="rounded-lg bg-gray-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-gray-700 transition-colors"
              onClick={() => navigate('/login')}
            >
              Sign in
            </button>
          </div>
        </header>
      )}
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="pillar-hero-badge">
            <PillarBadge pillar="axiom" />
          </div>
          <h1>From requirements to review, every step augmented by AI.</h1>
          <p>
            Axiom is a four-pillar platform that transforms messy stakeholder input into governed, traceable architecture
            decisions. Start with requirements. Design your architecture. Review it against evidence. Enforce it as your
            codebase evolves.
          </p>
          <div className="hero-actions">
            <button
              type="button"
              className="btn btn-primary"
              style={{ background: 'var(--color-pillar-axiom)' }}
              onClick={() => navigate('/specweaver')}
            >
              Start with requirements -&gt;
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/archon')}>
              Go to Archon
            </button>
          </div>
        </section>

        <div className="stats-strip">
          <div className="stat-item">
            <span className="stat-value">13</span>
            <span className="stat-label">
              Pipeline stages
              <br />
              per analysis
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-value">7</span>
            <span className="stat-label">
              Output artifact
              <br />
              types
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-value">4</span>
            <span className="stat-label">
              Intelligence
              <br />
              pillars
            </span>
          </div>
        </div>

        <section className="landing-section">
          <SectionHeading
            title="the three pillars"
            subtitle="Each pillar owns a distinct phase of the architecture lifecycle."
            accent="var(--color-pillar-axiom)"
          />
          <div className="feature-cards-grid">
            {PILLARS.map((pillar) => (
              <div
                key={pillar.id}
                className={`feature-card ${pillar.available ? 'feature-card--interactive' : 'feature-card--disabled'}`}
                onClick={() => {
                  if (pillar.available) navigate(pillar.path);
                }}
                data-testid={`axiom-pillar-card-${pillar.id}`}
              >
                <div className="feature-card-icon" style={{ background: pillar.iconBg }}>
                  <PillarIcon pillar={pillar.id} size={22} />
                </div>
                <div className="feature-card-heading-row">
                  <h3 className="feature-card-title">{pillar.name}</h3>
                  {!pillar.available && <span className="planned-notice planned-notice--compact">Planned</span>}
                </div>
                <p className="feature-card-kicker">{pillar.tagline}</p>
                <p className="feature-card-desc">{pillar.description}</p>
                {pillar.available && <p className="feature-card-highlight">Open {pillar.name} -&gt;</p>}
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section">
          <span className="sr-only">The Workflow</span>
          <SectionHeading title="How the pillars connect" accent="var(--color-pillar-axiom)" />
          <div className="workflow-steps">
            {WORKFLOW_STEPS.map((step, index) => (
              <Fragment key={step.num}>
                {index > 0 && (
                  <div className="workflow-connector">
                    -&gt;
                  </div>
                )}
                <div className="workflow-step">
                  <div
                    className="workflow-step-num"
                    style={{ background: `color-mix(in srgb, ${step.color} 12%, transparent)`, color: step.color }}
                  >
                    {step.num}
                  </div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </Fragment>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
