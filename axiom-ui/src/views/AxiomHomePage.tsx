import { Fragment } from 'react';
import { useNavigate } from 'react-router-dom';

import { PillarBadge } from '../components/PillarBadge';
import { PillarIcon, type PillarId } from '../components/PillarIcon';
import { SectionHeading } from '../components/landing/SectionHeading';

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
    id: 'scout',
    name: 'Scout',
    tagline: 'Repository Intelligence',
    description: 'Analyse your existing codebase and produce a system model.',
    path: '/scout',
    available: false,
    iconBg: 'var(--color-pillar-scout-bg)',
  },
  {
    id: 'forge',
    name: 'Forge',
    tagline: 'Prototype Generation',
    description: 'Generate working code scaffolds grounded in your actual architecture.',
    path: '/forge',
    available: false,
    iconBg: 'var(--color-pillar-forge-bg)',
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
    title: 'Scout + Forge',
    body: 'Analyse your codebase. Enforce your architecture as it evolves.',
    color: 'var(--color-pillar-scout)',
  },
];

/**
 * Platform landing page introducing all pillars and the end-to-end workflow.
 */
export function AxiomHomePage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="axiom-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="pillar-hero-badge">
            <PillarBadge pillar="axiom" />
          </div>
          <h1>From requirements to architecture, every step augmented by AI.</h1>
          <p>
            Axiom is a four-pillar platform that transforms messy stakeholder input into governed, traceable architecture
            decisions. Start with requirements. Design your architecture. Enforce it as your codebase evolves.
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
            title="The four pillars"
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
