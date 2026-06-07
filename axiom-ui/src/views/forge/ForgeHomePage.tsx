import { Link } from 'react-router-dom';

import { PillarBadge } from '../../components/PillarBadge';

/**
 * Planned Forge pillar landing page.
 */
export function ForgeHomePage() {
  return (
    <div className="h-full overflow-y-auto bg-gray-50" data-testid="forge-home-page">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <header className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <PillarBadge pillar="forge" />
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Forge</h1>
              <p className="text-sm font-medium text-gray-500">Prototype Generation</p>
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
            Forge is a planned pillar of the Axiom platform.
          </p>
          <p className="mt-3">
            It will use the outputs of Archon and Scout to generate working code scaffolds and prototypes grounded in your actual architecture decisions — not generic boilerplate.
          </p>

          <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h2 className="text-sm font-semibold text-gray-900">What Forge will do</h2>
            <ul className="mt-3 space-y-2">
              <li>○ Take the architecture plan from Archon and generate working code structure</li>
              <li>○ Scaffold services, APIs, and data models that match your ADL rules</li>
              <li>○ Validate generated code against your architecture governance rules</li>
              <li>○ Iterate based on Archon feedback until the scaffold passes all governance checks</li>
            </ul>
          </div>

          <Link to="/" className="mt-5 inline-flex text-sm font-medium text-[var(--color-pillar-forge)]">
            {'<-'} Back to Axiom
          </Link>
        </section>
      </div>
    </div>
  );
}
