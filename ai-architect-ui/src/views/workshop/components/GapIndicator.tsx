import { useState } from 'react';
import type { OpenGap } from '../../../types/workshop';

// Categories match the Python InformationGap.category Literal values exactly
const GAP_CATEGORIES = ['business_context', 'usage_context', 'technical_context', 'risk_priority'] as const;

const CATEGORY_LABELS: Record<string, string> = {
  business_context:  'Business Context',
  usage_context:     'Usage Context',
  technical_context: 'Technical Context',
  risk_priority:     'Risk & Priority',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-400',
  high:     'bg-amber-400',
  medium:   'bg-yellow-300',
  low:      'bg-gray-300',
};

interface Props {
  totalGaps: number;
  filledGaps: number;
  gapCompletionPct: number;
  /** Gaps with partial resolution (confidence ≥ 0.5) still below filled threshold. */
  inProgressCount: number;
  openGaps: OpenGap[];
}

const PROGRESS_DOT = 'bg-amber-400 ring-2 ring-amber-100';

export function GapIndicator({
  totalGaps,
  filledGaps,
  gapCompletionPct,
  inProgressCount,
  openGaps,
}: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggleCategory = (cat: string) =>
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));

  // Group open gaps by category; also collect uncategorised ones under a fallback bucket
  const knownCats = new Set(GAP_CATEGORIES as readonly string[]);
  const gapsByCategory = (GAP_CATEGORIES as readonly string[]).reduce<Record<string, OpenGap[]>>((acc, cat) => {
    acc[cat] = openGaps.filter((g) => g.category === cat);
    return acc;
  }, {});
  const uncategorised = openGaps.filter((g) => !knownCats.has(g.category));

  const pct = Math.round(gapCompletionPct);
  const allFilled = totalGaps > 0 && filledGaps >= totalGaps;

  const statusForGap = (gap: OpenGap): 'open' | 'in_progress' => {
    const rc = gap.resolutionConfidence ?? 0;
    if (rc >= 0.5) return 'in_progress';
    return 'open';
  };

  return (
    <div className="flex flex-col gap-3" data-testid="gap-indicator">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <span className="text-[12px] font-medium text-gray-700">Gap completion</span>
          <span className="text-[12px] text-gray-500">
            {filledGaps}/{totalGaps} filled
            {inProgressCount > 0 && (
              <span className="text-amber-700 ml-1">· {inProgressCount} in progress</span>
            )}
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div
            className="h-full bg-accent rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] text-gray-500 mt-0.5 block">{pct}% complete</span>
      </div>

      {/* Open gaps by category */}
      <div className="flex flex-col gap-2">
        {([...GAP_CATEGORIES] as string[]).concat(uncategorised.length > 0 ? ['_other'] : []).map((cat) => {
          const catGaps = cat === '_other' ? uncategorised : (gapsByCategory[cat] ?? []);
          if (catGaps.length === 0) return null;
          const isCollapsed = collapsed[cat] ?? false;
          const label = cat === '_other' ? 'Other' : (CATEGORY_LABELS[cat] ?? cat);
          return (
            <div key={cat} className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => toggleCategory(cat)}
                className="w-full flex items-center justify-between px-3 py-2 text-[12px] font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 transition-colors"
                aria-expanded={!isCollapsed}
              >
                <span>{label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-gray-500">{catGaps.length} open</span>
                  <svg
                    className={`w-3.5 h-3.5 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
                    viewBox="0 0 12 12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M2 4l4 4 4-4" />
                  </svg>
                </div>
              </button>
              {!isCollapsed && (
                <ul className="flex flex-col divide-y divide-gray-100">
                  {catGaps.map((gap) => (
                    <li key={gap.gapId} className="px-3 py-2 flex items-start gap-2">
                      <span
                        className={`mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full ${
                          statusForGap(gap) === 'in_progress'
                            ? PROGRESS_DOT
                            : PRIORITY_COLORS[gap.priority] ?? 'bg-gray-300'
                        }`}
                        title={statusForGap(gap) === 'in_progress' ? 'in progress' : gap.priority}
                      />
                      <span className="text-[12px] text-gray-600 leading-relaxed">{gap.description}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}

        {allFilled && (
          <div className="flex items-center gap-2 text-[12px] text-emerald-600 bg-emerald-50 rounded-lg px-3 py-2">
            <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M2 8l4 4 8-8" />
            </svg>
            All gaps filled
          </div>
        )}

        {totalGaps === 0 && (
          <p className="text-[12px] text-gray-400 text-center py-4">
            Gaps will appear as the conversation progresses.
          </p>
        )}
      </div>
    </div>
  );
}
