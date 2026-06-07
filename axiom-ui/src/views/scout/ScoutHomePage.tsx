import { Link } from 'react-router-dom';

import { PillarBadge } from '../../components/PillarBadge';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';

const SCOUT_FEATURES = [
  {
    icon: '🔍',
    iconBg: '#f0fdfa',
    title: 'Repository scanning',
    description: 'JavaParser, Tree-sitter, and Semgrep analyse your codebase across Java, Python, and TypeScript.',
  },
  {
    icon: '🗺',
    iconBg: '#f0fdfa',
    title: 'System modelling',
    description: 'Components, dependencies, and domain boundaries extracted into a typed SystemModel.',
  },
  {
    icon: '📐',
    iconBg: '#fefce8',
    title: 'Drift detection',
    description: "Compare your SystemModel against Archon's architecture decisions. Drift surfaces before it compounds.",
  },
  {
    icon: '🛡',
    iconBg: '#f0fdfa',
    title: 'ADL enforcement',
    description: 'Run your Archon ADL rules against the actual codebase. Violations surface as CI failures.',
  },
];

/**
 * Planned Scout pillar landing page.
 */
export function ScoutHomePage() {
  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="scout-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="planned-notice">
            Coming soon
            <span className="sr-only">Planned Pillar</span>
          </div>
          <div className="pillar-hero-badge">
            <PillarBadge pillar="scout" />
          </div>
          <h1>Your codebase, understood.</h1>
          <p>
            Scout analyses your repository using static analysis and produces a structured system model: components,
            dependencies, domain boundaries. Then it compares what you built against what Archon designed, and tells you
            where they diverge.
          </p>
          <Link to="/" className="btn btn-secondary">
            &lt;- Back to Axiom
          </Link>
        </section>

        <section className="landing-section">
          <SectionHeading title="Planned capabilities" accent="var(--color-pillar-scout)" />
          <div className="feature-cards-grid">
            {SCOUT_FEATURES.map((card) => (
              <FeatureCard key={card.title} {...card} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
