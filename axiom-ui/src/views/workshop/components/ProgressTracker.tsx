const PHASES = [
  { key: 'CONTEXT_SETTING', label: 'Context' },
  { key: 'STAKEHOLDER_ELICITATION', label: 'Stakeholders' },
  { key: 'QUALITY_ATTRIBUTE_ELICITATION', label: 'Attributes' },
  { key: 'SCENARIO_REFINEMENT', label: 'Scenarios' },
  { key: 'CONSOLIDATION', label: 'Consolidate' },
] as const;

/** Map Python agent snake_case phase names to the UI phase keys above. */
const PYTHON_PHASE_MAP: Record<string, string> = {
  input_analysis:          'CONTEXT_SETTING',
  business_context:        'CONTEXT_SETTING',
  usage_context:           'STAKEHOLDER_ELICITATION',
  technical_context:       'STAKEHOLDER_ELICITATION',
  risk_priority:           'QUALITY_ATTRIBUTE_ELICITATION',
  scenario_brainstorm:     'QUALITY_ATTRIBUTE_ELICITATION',
  scenario_refinement:     'SCENARIO_REFINEMENT',
  attribute_consolidation: 'CONSOLIDATION',
  validation:              'CONSOLIDATION',
  complete:                'CONSOLIDATION',
};

function normalizePhase(phase: string): string {
  return PYTHON_PHASE_MAP[phase] ?? phase;
}

interface Props {
  currentPhase: string;
  turnNumber: number;
  hasSufficientAttributes: boolean;
}

export function ProgressTracker({ currentPhase, turnNumber, hasSufficientAttributes }: Props) {
  const normalized = normalizePhase(currentPhase);
  const currentIndex = PHASES.findIndex((p) => p.key === normalized);

  return (
    <div
      className="flex flex-col gap-2 min-w-0 sm:flex-row sm:items-center sm:gap-2 px-3 sm:px-4 py-2 bg-white border-b border-gray-200"
      data-testid="progress-tracker"
      aria-label="Workshop phase progress"
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="text-[10px] sm:text-[11px] text-gray-500 font-medium shrink-0">Phase</span>
        <div className="flex items-center gap-1 flex-1 min-w-0 overflow-x-auto overflow-y-hidden pb-0.5 [-webkit-overflow-scrolling:touch] [scrollbar-width:thin]">
          {PHASES.map((phase, idx) => {
            const done = idx < currentIndex;
            const active = idx === currentIndex;
            return (
              <div key={phase.key} className="flex items-center gap-1 shrink-0">
                <div
                  className={`flex items-center gap-0.5 sm:gap-1 rounded-full px-2 sm:px-2.5 py-0.5 text-[10px] sm:text-[11px] font-medium transition-colors whitespace-nowrap ${
                    active
                      ? 'bg-accent/10 text-accent ring-1 ring-accent/40'
                      : done
                      ? 'bg-emerald-50 text-emerald-600'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {done && (
                    <svg className="w-2.5 h-2.5 sm:w-3 sm:h-3 shrink-0" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M2 6l3 3 5-5" />
                    </svg>
                  )}
                  {phase.label}
                </div>
                {idx < PHASES.length - 1 && (
                  <div className={`w-2 sm:w-3 h-px shrink-0 ${done ? 'bg-emerald-300' : 'bg-gray-200'}`} aria-hidden="true" />
                )}
              </div>
            );
          })}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 pt-1 border-t border-gray-100 sm:pt-0 sm:border-t-0 sm:pl-2 sm:ml-0">
        <span className="text-[10px] sm:text-[11px] text-gray-500 whitespace-nowrap">Turn {turnNumber}</span>
        {hasSufficientAttributes && (
          <span className="rounded-full px-2 sm:px-2.5 py-0.5 text-[10px] sm:text-[11px] font-semibold bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 whitespace-nowrap">
            Ready
          </span>
        )}
      </div>
    </div>
  );
}
