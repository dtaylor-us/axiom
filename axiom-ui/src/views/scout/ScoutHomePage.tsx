import { Link } from 'react-router-dom';

import { PillarBadge } from '../../components/PillarBadge';

/**
 * Planned Scout pillar landing page.
 */
export function ScoutHomePage() {
  return (
    <div className="h-full overflow-y-auto bg-gray-50" data-testid="scout-home-page">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <header className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <PillarBadge pillar="scout" />
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Scout</h1>
              <p className="text-sm font-medium text-gray-500">Repository Intelligence</p>
            </div>
          </div>
          <div className="mt-4">
            <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-semibold text-gray-600">
              Planned Pillar
            </span>
          </div>
        </header>

        <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-700 leading-relaxed">
          <p>
            Scout is a planned pillar of the Axiom platform.
          </p>
          <p className="mt-3">
            It will analyse your existing codebase and produce a structured model of your system as it actually is — identifying domain boundaries, detecting drift from architecture decisions, and surfacing technical debt.
          </p>

          <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h2 className="text-sm font-semibold text-gray-900">What Scout will do</h2>
            <ul className="mt-3 space-y-2">
              <li>○ Parse your repository using static analysis (JavaParser, Tree-sitter, Semgrep)</li>
              <li>○ Produce a SystemModel — components, dependencies, domain boundaries</li>
              <li>○ Detect drift between your architecture decisions (from Archon) and your actual codebase</li>
              <li>○ Surface technical debt and violated architecture rules</li>
            </ul>
          </div>

          <Link to="/" className="mt-5 inline-flex text-sm font-medium text-[var(--color-pillar-scout)]">
            {'<-'} Back to Axiom
          </Link>
        </section>
      </div>
    </div>
  );
}
