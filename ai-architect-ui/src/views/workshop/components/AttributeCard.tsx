import type { QualityAttribute } from '../../../types/workshop';

const CONFIDENCE_BADGE: Record<string, string> = {
  confirmed: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  inferred: 'bg-amber-50 text-amber-900 ring-amber-200',
  tentative: 'bg-gray-100 text-gray-700 ring-gray-200',
};

const IMPORTANCE_SCORE: Record<string, number> = {
  critical: 10,
  high: 8,
  medium: 5,
  low: 2,
};

const COMPLETENESS_PCT: Record<string, number> = {
  complete: 100,
  partial: 60,
  needs_measure: 30,
  aspirational: 10,
};

interface Props {
  attribute: QualityAttribute;
  sessionAttributesStale?: boolean;
  onScrollToGenerate?: () => void;
}

export function AttributeCard({
  attribute,
  sessionAttributesStale = false,
  onScrollToGenerate,
}: Props) {
  const badgeClass = CONFIDENCE_BADGE[attribute.confidence] ?? 'bg-gray-100 text-gray-600 ring-gray-200';
  const importanceScore = IMPORTANCE_SCORE[attribute.importance] ?? 5;
  const completeness = COMPLETENESS_PCT[attribute.scenarioCompleteness] ?? 0;

  const fp = attribute.firstGenerationPass ?? null;
  const lp = attribute.lastGenerationPass ?? null;
  let passLabel = '';
  if (fp != null && lp != null && lp !== fp) {
    passLabel = `Generated in pass ${fp} · Updated in pass ${lp}`;
  } else if (fp != null) {
    passLabel = `Generated in pass ${fp}`;
  }

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-3.5 flex flex-col gap-2 archon-reveal"
      data-testid="attribute-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-gray-900 truncate">
            <span className="text-gray-500 font-normal">{attribute.attributeId}</span>
            {' — '}
            {attribute.name}
          </p>
          <p className="text-[11px] text-gray-500">{attribute.category}</p>
          {(passLabel || (sessionAttributesStale && fp != null)) ? (
            <p className="text-[10px] text-gray-400 mt-0.5">
              {passLabel}
              {sessionAttributesStale && fp != null ? (
                <>
                  {passLabel ? ' · ' : null}
                  <button
                    type="button"
                    onClick={onScrollToGenerate}
                    className="text-amber-700 hover:text-amber-900 font-medium"
                  >
                    may be outdated ↻
                  </button>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ${badgeClass}`}>
          {attribute.confidence}
        </span>
      </div>

      {/* Importance */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-gray-500">Importance</span>
        <div className="flex gap-0.5">
          {Array.from({ length: 10 }, (_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-sm ${i < importanceScore ? 'bg-accent' : 'bg-gray-100'}`}
              aria-hidden="true"
            />
          ))}
        </div>
        <span className="text-[11px] text-gray-500">{attribute.importance}</span>
      </div>

      {/* Scenario completeness */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <span className="text-[11px] text-gray-500">Scenario</span>
          <span className="text-[11px] text-gray-400">{attribute.scenarioCompleteness}</span>
        </div>
        <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full"
            style={{ width: `${completeness}%` }}
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Scenario detail removed — not returned by QualityAttributeDto */}

      {/* Open questions */}
      {attribute.openQuestions.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-amber-700 mb-1">Open questions</p>
          <ul className="flex flex-col gap-0.5">
            {attribute.openQuestions.map((q, i) => (
              <li key={i} className="text-[11px] text-gray-600">• {q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
