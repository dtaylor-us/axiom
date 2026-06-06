import { Link } from 'react-router-dom';

import { PillarBadge } from '../components/PillarBadge';
import { PillarIcon, type PillarId } from '../components/PillarIcon';

interface PillarCardProps {
  pillarId: 'archon' | 'specweaver' | 'scout' | 'forge';
  name: string;
  tagline: string;
  description: string;
  path: string;
  available: boolean;
}

const PILLAR_ACCENT_CLASS: Record<PillarId, string> = {
  axiom: 'border-l-[#7B2FBE]',
  archon: 'border-l-[var(--color-pillar-archon)]',
  specweaver: 'border-l-[var(--color-pillar-specweaver)]',
  scout: 'border-l-[var(--color-pillar-scout)]',
  forge: 'border-l-[var(--color-pillar-forge)]',
};

const PILLAR_TEXT_CLASS: Record<PillarId, string> = {
  axiom: 'text-[#7B2FBE]',
  archon: 'text-[var(--color-pillar-archon)]',
  specweaver: 'text-[var(--color-pillar-specweaver)]',
  scout: 'text-[var(--color-pillar-scout)]',
  forge: 'text-[var(--color-pillar-forge)]',
};

function PillarCard({ pillarId, name, tagline, description, path, available }: PillarCardProps) {
  const baseClass = `rounded-xl border border-gray-200 border-l-4 ${PILLAR_ACCENT_CLASS[pillarId]} bg-white p-5`;

  if (!available) {
    return (
      <article className={`${baseClass} opacity-85`} data-testid={`axiom-pillar-card-${pillarId}`}>
        <div className="flex items-center gap-2">
          <PillarIcon pillar={pillarId} size={18} className={PILLAR_TEXT_CLASS[pillarId]} />
          <h3 className="text-base font-semibold text-gray-900">{name}</h3>
        </div>
        <p className="mt-1 text-xs font-medium text-gray-500 uppercase tracking-wide">{tagline}</p>
        <p className="mt-3 text-sm text-gray-700 leading-relaxed">{description}</p>
        <div className="mt-4">
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-semibold text-gray-600">
            Planned
          </span>
        </div>
      </article>
    );
  }

  return (
    <Link
      to={path}
      className={`${baseClass} block transition-colors hover:bg-gray-50`}
      data-testid={`axiom-pillar-card-${pillarId}`}
    >
      <div className="flex items-center gap-2">
        <PillarIcon pillar={pillarId} size={18} className={PILLAR_TEXT_CLASS[pillarId]} />
        <h3 className="text-base font-semibold text-gray-900">{name}</h3>
      </div>
      <p className="mt-1 text-xs font-medium text-gray-500 uppercase tracking-wide">{tagline}</p>
      <p className="mt-3 text-sm text-gray-700 leading-relaxed">{description}</p>
      <div className={`mt-4 inline-flex items-center text-sm font-semibold ${PILLAR_TEXT_CLASS[pillarId]}`}>
        Open {'->'}
      </div>
    </Link>
  );
}

/**
 * Platform landing page introducing all pillars and the end-to-end workflow.
 */
export function AxiomHomePage() {
  return (
    <div className="h-full overflow-y-auto bg-gray-50" data-testid="axiom-home-page">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <header className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-start gap-4">
            <div className="axiom-brand-icon shrink-0">
              <PillarIcon pillar="axiom" size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Axiom</h1>
              <p className="mt-1 text-sm uppercase tracking-[0.16em] text-gray-500">Architecture Intelligence Platform</p>
              <p className="mt-3 text-sm text-gray-700 leading-relaxed">
                From requirements to architecture, every step augmented by AI.
              </p>
            </div>
          </div>
        </header>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6" aria-labelledby="pillars-title">
          <h2 id="pillars-title" className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">The Pillars</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <PillarCard
              pillarId="specweaver"
              name="SpecWeaver"
              tagline="Requirements Intelligence"
              description="Transform messy stakeholder documents into clean structured requirements."
              path="/specweaver"
              available
            />
            <PillarCard
              pillarId="archon"
              name="Archon"
              tagline="Architecture Reasoning"
              description="Turn requirements into a full architecture analysis in minutes."
              path="/archon"
              available
            />
            <PillarCard
              pillarId="scout"
              name="Scout"
              tagline="Repository Intelligence"
              description="Analyse your existing codebase and produce a system model."
              path="/scout"
              available={false}
            />
            <PillarCard
              pillarId="forge"
              name="Forge"
              tagline="Prototype Generation"
              description="Generate working code scaffolds grounded in your actual architecture."
              path="/forge"
              available={false}
            />
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6" aria-labelledby="workflow-title">
          <h2 id="workflow-title" className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">The Workflow</h2>
          <div className="mt-3 flex items-center gap-2 text-sm text-gray-700">
            <PillarBadge pillar="specweaver" size="sm" showLabel={false} />
            <span>SpecWeaver</span>
            <span>{'->'}</span>
            <PillarBadge pillar="archon" size="sm" showLabel={false} />
            <span>Archon</span>
            <span>{'->'}</span>
            <PillarBadge pillar="scout" size="sm" showLabel={false} />
            <span>Scout</span>
            <span>{'->'}</span>
            <PillarBadge pillar="forge" size="sm" showLabel={false} />
            <span>Forge</span>
          </div>
          <ol className="mt-4 space-y-4 text-sm text-gray-700">
            <li>
              <p className="font-semibold text-gray-900">1. Upload your requirements documents</p>
              <p className="mt-1">SpecWeaver extracts, classifies, and structures them into an architecture-ready package.</p>
            </li>
            <li>
              <p className="font-semibold text-gray-900">2. Send to Archon</p>
              <p className="mt-1">Archon runs a 13-stage reasoning pipeline and produces architecture decisions, ADL rules, trade-off analysis, and governance scoring.</p>
            </li>
            <li>
              <p className="font-semibold text-gray-900">3. Scout analyses your codebase <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">Coming soon</span></p>
              <p className="mt-1">Detect drift between your architecture decisions and what is actually built.</p>
            </li>
            <li>
              <p className="font-semibold text-gray-900">4. Forge generates your scaffold <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">Coming soon</span></p>
              <p className="mt-1">Produce working code grounded in your architecture, not generic boilerplate.</p>
            </li>
          </ol>
        </section>
      </div>
    </div>
  );
}
