import { Link } from 'react-router-dom';

import { PillarBadge } from '../../components/PillarBadge';
import { FeatureCard } from '../../components/landing/FeatureCard';
import { SectionHeading } from '../../components/landing/SectionHeading';

const FORGE_FEATURES = [
  {
    icon: '🏗',
    iconBg: '#fff1f2',
    title: 'Architecture-constrained scaffolding',
    description: 'Generate service structures with ADL constraints embedded as annotations, not empty boilerplate.',
  },
  {
    icon: '📋',
    iconBg: '#fff1f2',
    title: 'Rule generation',
    description: 'Produce ArchUnit, PyTestArch, and Semgrep tests from your ADL rules automatically.',
  },
  {
    icon: '🚦',
    iconBg: '#fefce8',
    title: 'CI enforcement',
    description: 'Architecture gates in your pipeline. Pull requests fail when ADL rules are violated.',
  },
  {
    icon: '🔄',
    iconBg: '#fff1f2',
    title: 'Continuous audit',
    description: "Continuously compare Scout's SystemModel against Archon decisions. Drift never hides.",
  },
];

/**
 * Planned Forge pillar landing page.
 */
export function ForgeHomePage() {
  return (
    <div className="landing-page h-full overflow-y-auto bg-gray-50" data-testid="forge-home-page">
      <div className="landing-inner">
        <section className="pillar-hero">
          <div className="planned-notice">
            Coming soon
            <span className="sr-only">Planned Pillar</span>
          </div>
          <div className="pillar-hero-badge">
            <PillarBadge pillar="forge" />
          </div>
          <h1>Architecture that stays honest.</h1>
          <p>
            Forge generates code scaffolds grounded in your actual architecture decisions, not generic boilerplate. Then
            it enforces those decisions as executable CI gates so your architecture stays honest as the codebase grows.
          </p>
          <Link to="/" className="btn btn-secondary">
            &lt;- Back to Axiom
          </Link>
        </section>

        <section className="landing-section">
          <SectionHeading title="Planned capabilities" accent="var(--color-pillar-forge)" />
          <div className="feature-cards-grid">
            {FORGE_FEATURES.map((card) => (
              <FeatureCard key={card.title} {...card} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
