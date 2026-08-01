/**
 * Home / orientation landing view for Axiom.
 *
 * This view is static by design: it explains what Axiom is, outlines the staged
 * pipeline, and provides a clear entry point into a new architecture session.
 */
export function HomeView({
  onStartSession,
  onNavigateToWorkshop,
}: {
  onStartSession: () => void;
  onNavigateToWorkshop?: () => void;
}) {
  const PIPELINE = [
    { id: '01', name: 'Requirement parsing' },
    { id: '02', name: 'Requirement challenge' },
    { id: '03', name: 'Scenario modelling' },
    { id: '04', name: 'Characteristic inference' },
    { id: '04b', name: 'Tactics recommendation' },
    { id: '05', name: 'Conflict analysis' },
    { id: '06', name: 'Architecture generation' },
    { id: '06b', name: 'Buy vs build analysis' },
    { id: '07', name: 'Diagram generation' },
    { id: '08', name: 'Trade-off analysis' },
    { id: '09', name: 'ADL generation' },
    { id: '10', name: 'Weakness and FMEA' },
    { id: '12', name: 'Architecture review' },
  ] as const;

  const artifacts = [
    'Architecture diagrams (C4 container plus type-selected Mermaid)',
    'Trade-off record with documented decisions and scale testing',
    'Mark Richards ADL specification with executable governance rules',
    'FMEA risk analysis with RPN scores',
    'Architecture tactics report',
    'Governance score with confidence level and dimension breakdown',
    'Buy vs build decisions with named alternatives',
  ] as const;

  return (
    <div className="h-full overflow-y-auto" data-testid="home-view">
      <div className="max-w-5xl mx-auto p-6 md:p-10">
        <header
          className="archon-reveal"
          style={{ ['--reveal-delay' as any]: '0ms' }}
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 shrink-0 bg-accent/90 rounded-2xl flex items-center justify-center shadow-sm">
              <svg
                className="w-6 h-6 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl md:text-3xl font-semibold text-gray-900">
                Axiom
              </h1>
              <p className="text-base font-medium text-gray-500 mt-1 tracking-wide">
                An AI assistant for software architects
              </p>
              <p className="text-[15px] text-gray-600 mt-2 leading-relaxed max-w-3xl">
                Axiom is not a chatbot. It is a staged architecture reasoning pipeline that decomposes
                design thinking into a governed, inspectable process.
              </p>
              <div className="mt-5 flex flex-col sm:flex-row sm:items-center gap-2.5">
                <button
                  type="button"
                  onClick={onStartSession}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent text-white px-4 py-2.5 text-sm font-semibold hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 transition-colors"
                  data-testid="home-start-session"
                >
                  Start an architecture session
                  <svg
                    className="w-4 h-4"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M6 3l5 5-5 5" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </header>

        <div className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <main className="min-w-0 space-y-10">
            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '80ms' }}
              aria-labelledby="pipeline-title"
            >
              <div className="flex items-baseline justify-between gap-3">
                <div className="flex items-center gap-2">
                  <svg
                    className="w-4 h-4 text-gray-700"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 4h10M3 8h10M3 12h10" />
                    <path d="M6 4v8" />
                    <path d="M10 8v4" />
                  </svg>
                  <h2 id="pipeline-title" className="text-lg font-bold text-gray-900">
                    Pipeline stages
                  </h2>
                </div>
                <p className="text-xs text-gray-500">
                  Monitored as a structured run, not a single response.
                </p>
              </div>

              <div className="mt-3 rounded-xl border border-gray-200 bg-white overflow-hidden">
                <ol className="divide-y divide-gray-100">
                  {PIPELINE.map((s) => {
                    const isGovernance = s.id === '12';
                    return (
                      <li
                        key={s.id}
                        className={`px-4 py-3 flex items-start justify-between gap-3 ${
                          isGovernance ? 'bg-accent/5' : ''
                        }`}
                        data-stage-id={s.id}
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900">
                            <span className="font-mono text-[12px] text-gray-500 mr-2">
                              {s.id}
                            </span>
                            {s.name}
                          </p>
                          {isGovernance && (
                            <p className="text-xs text-emerald-700 mt-1">
                              Governance stage — independent review and enforceability audit.
                            </p>
                          )}
                        </div>
                        {isGovernance && (
                          <span className="shrink-0 inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-1 text-[11px] font-semibold">
                            Review
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </div>
            </section>

            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '140ms' }}
              aria-labelledby="capabilities-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M8 1.5v2.5M8 12v2.5" />
                  <path d="M1.5 8h2.5M12 8h2.5" />
                  <path d="M3.2 3.2l1.8 1.8M11 11l1.8 1.8" />
                  <path d="M12.8 3.2L11 5M5 11l-1.8 1.8" />
                  <circle cx="8" cy="8" r="2.5" />
                </svg>
                <h2 id="capabilities-title" className="text-lg font-bold text-gray-900">
                  Key capabilities
                </h2>
              </div>

              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M2.5 12.5h11" />
                      <path d="M4 11V5" />
                      <path d="M8 11V3.5" />
                      <path d="M12 11V7" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">Architecture style selection</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    Scores all eight Mark Richards architecture styles against inferred characteristics, applies veto
                    rules, and never defaults to layered architecture without justification.
                  </p>
                </article>
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M3 4.5h10" />
                      <path d="M3 8h10" />
                      <path d="M3 11.5h6" />
                      <path d="M11.2 10.2l1.3 1.3 2-2" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">Architecture tactics</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    Recommends named tactics from the Bass, Clements, Kazman catalog for each quality attribute and
                    identifies which are already addressed and which are not.
                  </p>
                </article>
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M5 3.5h6" />
                      <path d="M4 6.5h8" />
                      <path d="M3.5 6.5v6a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1v-6" />
                      <path d="M6.2 9.2h3.6" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">Buy vs build analysis</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    Evaluates each architecture component for build, buy, or adopt. Names real products and open-source
                    projects and warns when recommendations conflict with stated preferences.
                  </p>
                </article>
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M6.5 2.5h6v11h-9v-8" />
                      <path d="M3.5 5.5l3-3" />
                      <path d="M3.5 5.5h3v-3" />
                      <path d="M6 8h4" />
                      <path d="M6 10.5h4" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">Executable governance</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    Generates Architecture Definition Language (Mark Richards ADL) blocks with executable rules.
                    Rules compile to runnable ArchUnit, PyTestArch, and Semgrep tests.
                  </p>
                </article>
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M2.5 12.5h11" />
                      <path d="M4 12.5V9" />
                      <path d="M8 12.5V6.5" />
                      <path d="M12 12.5V4.5" />
                      <path d="M4 9l4-2.5L12 4.5" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">FMEA and weakness analysis</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    Scores failure modes with Risk Priority Number, identifies cascading failures across service
                    boundaries, and classifies graceful versus catastrophic degradation.
                  </p>
                </article>
                <article className="rounded-xl border border-gray-200 bg-white p-4">
                  <div className="flex items-start gap-2">
                    <svg
                      className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M6.5 3.5h7v9h-7" />
                      <path d="M6.5 5.5H3.5v5h3" />
                      <path d="M8.8 8h2.4" />
                      <path d="M9.8 7l1 1-1 1" />
                    </svg>
                    <h3 className="text-sm font-semibold text-gray-900">Architecture review agent</h3>
                  </div>
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                    A separate review agent challenges assumptions, stress-tests trade-offs, audits ADL enforceability,
                    and produces a governance score (0–100) across five dimensions.
                  </p>
                </article>
              </div>
            </section>

            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '170ms' }}
              aria-labelledby="workshop-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h6a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
                  <path d="M9 5a2 2 0 002 2h0a2 2 0 002-2" />
                  <path d="M9 5a2 2 0 012-2h0a2 2 0 012 2" />
                  <path d="M6.5 10.5h3" />
                  <path d="M6.5 8.5h5" />
                </svg>
                <h2 id="workshop-title" className="text-lg font-bold text-gray-900">
                  Quality Attribute Workshop
                </h2>
              </div>

              <div className="mt-3">
                <p className="text-sm text-gray-600 leading-relaxed">
                  Before running the architecture pipeline, use the built-in Quality Attribute Workshop (QAW) to elicit
                  and structure your quality requirements. Based on the SEI QAW methodology, it guides a structured
                  conversation that asks the right questions before asserting any design decisions.
                </p>

                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg
                        className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M3 5.5h5" />
                        <path d="M3 8.5h8" />
                        <path d="M3 11.5h6" />
                        <circle cx="12" cy="11" r="2.5" />
                        <path d="M14 13l1.5 1.5" />
                      </svg>
                      <h3 className="text-sm font-semibold text-gray-900">Conversational elicitation</h3>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                      A phase-guided conversation draws out concrete quality scenarios — asking about operational events,
                      failure modes, and business goals rather than accepting vague requirements.
                    </p>
                  </article>

                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg
                        className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <circle cx="8" cy="8" r="6" />
                        <path d="M8 5v3.5l2.5 1.5" />
                      </svg>
                      <h3 className="text-sm font-semibold text-gray-900">Information gap tracking</h3>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                      Each turn identifies which information is still missing. A live gap tracker shows completion
                      progress and surfaces open gaps so elicitation stays focused.
                    </p>
                  </article>

                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg
                        className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M8 2.5v3M4.5 5L8 2.5 11.5 5" />
                        <path d="M5 8.5H2.5M8 8.5H5M11 8.5H8M13.5 8.5H11" />
                        <path d="M3.5 8.5v4" />
                        <path d="M8 8.5v4" />
                        <path d="M12.5 8.5v4" />
                      </svg>
                      <h3 className="text-sm font-semibold text-gray-900">SEI utility tree</h3>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                      Once 5 or more scenarios span 3 or more attributes, a priority tree is generated. Architectural
                      drivers — scenarios scored (H,H) or (H,M) — are highlighted automatically.
                    </p>
                  </article>

                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg
                        className="w-4 h-4 text-gray-700 mt-0.5 shrink-0"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M6.5 3.5h7v9h-7" />
                        <path d="M6.5 5.5H3.5v5h3" />
                        <path d="M8.8 8h2.4" />
                        <path d="M9.8 7l1 1-1 1" />
                      </svg>
                      <h3 className="text-sm font-semibold text-gray-900">Pipeline handoff with constraints</h3>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                      Architectural implications — must and should constraints derived from the scenarios — are
                      automatically pre-loaded when the workshop sends its output to the architecture pipeline.
                    </p>
                  </article>
                </div>

                {onNavigateToWorkshop && (
                  <button
                    type="button"
                    onClick={onNavigateToWorkshop}
                    className="mt-4 inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 transition-colors"
                  >
                    Open Quality Attribute Workshop
                    <svg
                      className="w-4 h-4"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M6 3l5 5-5 5" />
                    </svg>
                  </button>
                )}
              </div>
            </section>

            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '200ms' }}
              aria-labelledby="difference-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2.5 4.5h11" />
                  <path d="M2.5 8h7" />
                  <path d="M2.5 11.5h9" />
                  <path d="M12.2 7.2l1.3 1.3 2-2" />
                </svg>
                <h2 id="difference-title" className="text-lg font-bold text-gray-900">
                  Why it’s different
                </h2>
              </div>

              <div className="mt-3 rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-sm text-gray-700 leading-relaxed">
                  Most AI architecture tools produce one answer from one prompt with no intermediate reasoning and no
                  traceability. Axiom runs a structured review process that produces inspectable intermediate artifacts
                  at every stage.
                </p>
                <ul className="mt-3 space-y-2 text-sm text-gray-700">
                  <li className="flex gap-2">
                    <span className="text-accent font-mono shrink-0" aria-hidden="true">—</span>
                    Requirements are challenged before design begins
                  </li>
                  <li className="flex gap-2">
                    <span className="text-accent font-mono shrink-0" aria-hidden="true">—</span>
                    Style is selected from a scored catalog with evidence, not chosen by default
                  </li>
                  <li className="flex gap-2">
                    <span className="text-accent font-mono shrink-0" aria-hidden="true">—</span>
                    Every finding traces back to a requirement, scenario, or characteristic
                  </li>
                  <li className="flex gap-2">
                    <span className="text-accent font-mono shrink-0" aria-hidden="true">—</span>
                    The architecture critiques itself before it is presented as final
                  </li>
                  <li className="flex gap-2">
                    <span className="text-accent font-mono shrink-0" aria-hidden="true">—</span>
                    Governance rules are executable, not just documented
                  </li>
                </ul>
              </div>
            </section>
          </main>

          <aside className="space-y-6 lg:sticky lg:top-6 self-start">
            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '110ms' }}
              aria-labelledby="artifacts-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M5 2.5h7v11h-9v-9" />
                  <path d="M3 4.5l2-2" />
                  <path d="M3 4.5h2v-2" />
                </svg>
                <h2 id="artifacts-title" className="text-lg font-bold text-gray-900">
                  Output artifacts
                </h2>
              </div>
              <div className="mt-3 rounded-xl border border-gray-200 bg-white p-4">
                <ul className="space-y-2 text-sm text-gray-700">
                  {artifacts.map((a) => (
                    <li key={a} className="flex gap-2">
                      <span className="text-gray-400 font-mono shrink-0" aria-hidden="true">
                        ✓
                      </span>
                      <span className="leading-relaxed">{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '170ms' }}
              aria-labelledby="adl-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3.5 2.5h9v11h-9z" />
                  <path d="M5.5 5.5h5" />
                  <path d="M5.5 8h5" />
                  <path d="M5.5 10.5h3.5" />
                </svg>
                <h2 id="adl-title" className="text-lg font-bold text-gray-900">
                  Mark Richards ADL
                </h2>
              </div>
              <div className="mt-3 rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-sm text-gray-700 leading-relaxed">
                  Governance isn’t a PDF appendix. Axiom produces ADL blocks intended to be enforceable via runnable
                  rules (ArchUnit, PyTestArch, Semgrep).
                </p>
                <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <pre className="text-[12px] leading-relaxed text-gray-700 font-mono whitespace-pre-wrap">
                    {[
                      'ADL {',
                      '  rule "services must not call DB directly"',
                      '  enforce via: ArchUnit | PyTestArch | Semgrep',
                      '}',
                    ].join('\n')}
                  </pre>
                </div>
              </div>
            </section>

            <section
              className="archon-reveal"
              style={{ ['--reveal-delay' as any]: '230ms' }}
              aria-labelledby="start-title"
            >
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-gray-700"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 8h10" />
                  <path d="M9.5 5.5L13 8l-3.5 2.5" />
                  <path d="M3.5 3.5h9" />
                  <path d="M3.5 12.5h7" />
                </svg>
                <h2 id="start-title" className="text-lg font-bold text-gray-900">
                  Start a run
                </h2>
              </div>
              <div className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
                <p className="text-sm text-gray-700 leading-relaxed">
                  Provide a requirements description. Axiom executes the full pipeline and streams stage progress as it
                  completes.
                </p>
                <button
                  type="button"
                  onClick={onStartSession}
                  className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 transition-colors"
                >
                  Continue to chat
                  <svg
                    className="w-4 h-4"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M6 3l5 5-5 5" />
                  </svg>
                </button>
                <div className="mt-3 flex items-start gap-2 text-[11px] text-gray-500">
                  <span className="font-mono shrink-0" aria-hidden="true">
                    ::
                  </span>
                  <p>
                    Stage identifiers, intermediate artifacts, and exports are designed to be inspectable — not hidden
                    reasoning.
                  </p>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

