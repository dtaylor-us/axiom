import type { WorkshopScenario } from '../../../types/workshop';
import { useState } from 'react';

const BORDER: Record<string, string> = {
  complete: 'border-l-emerald-500',
  needs_measure: 'border-l-amber-400',
  needs_operational_metric: 'border-l-amber-400',
  partial: 'border-l-blue-500',
  aspirational: 'border-l-gray-300',
};

const COMPLETENESS_LABEL: Record<string, string> = {
  complete: 'Complete',
  needs_measure: 'Missing response measure',
  needs_operational_metric: 'Response measure needs a specific operational threshold',
  partial: 'Partial',
  aspirational: 'Aspirational',
};

interface Props {
  scenario: WorkshopScenario;
  /** When set, shows an inline field to submit a response measure as a workshop turn. */
  onSubmitMeasure?: (scenarioId: string, measure: string) => void;
}

/**
 * Card showing one operational workshop scenario and its completeness state.
 */
export function ScenarioCard({ scenario, onSubmitMeasure }: Props) {
  const [measureDraft, setMeasureDraft] = useState('');
  const border = BORDER[scenario.completeness] ?? BORDER.aspirational;
  const needsMeasure = scenario.completeness === 'needs_measure';
  const needsOperationalMetric = scenario.completeness === 'needs_operational_metric';

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white shadow-sm border-l-4 ${border} p-3`}
      data-testid={`scenario-card-${scenario.scenarioId}`}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <span className="text-[11px] font-mono text-gray-400">{scenario.scenarioId}</span>
        <span className="text-[10px] uppercase tracking-wide text-gray-500">
          {COMPLETENESS_LABEL[scenario.completeness] ?? scenario.completeness.replace(/_/g, ' ')}
        </span>
      </div>
      <h3 className="text-[13px] font-semibold text-gray-900 mb-2">{scenario.title || 'Untitled scenario'}</h3>
      <dl className="space-y-1.5 text-[12px] text-gray-600">
        <div className="grid grid-cols-[88px_1fr] gap-1">
          <dt className="text-gray-400">Stimulus</dt>
          <dd>{scenario.stimulus || '—'}</dd>
        </div>
        <div className="grid grid-cols-[88px_1fr] gap-1">
          <dt className="text-gray-400">Environment</dt>
          <dd>{scenario.environment || '—'}</dd>
        </div>
        <div className="grid grid-cols-[88px_1fr] gap-1">
          <dt className="text-gray-400">Response</dt>
          <dd>{scenario.response || '—'}</dd>
        </div>
        <div className="grid grid-cols-[88px_1fr] gap-1 items-start">
          <dt className="text-gray-400">Measure</dt>
          <dd>
            {scenario.responseMeasure ? (
              <span className={needsOperationalMetric ? 'text-amber-700' : undefined}>
                {scenario.responseMeasure}
              </span>
            ) : needsMeasure ? (
              <span className="text-amber-700">Missing response measure</span>
            ) : (
              '—'
            )}
          </dd>
        </div>
      </dl>
      {scenario.exercisesAttributes?.length > 0 && (
        <p className="mt-2 text-[11px] text-gray-500">
          <span className="font-medium text-gray-600">Exercises:</span>{' '}
          {scenario.exercisesAttributes.join(' · ')}
        </p>
      )}
      {needsMeasure && onSubmitMeasure && (
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={measureDraft}
            onChange={(e) => setMeasureDraft(e.target.value)}
            placeholder="Add a measurable threshold…"
            className="flex-1 text-[12px] border border-gray-200 rounded-lg px-2 py-1.5"
          />
          <button
            type="button"
            disabled={!measureDraft.trim()}
            onClick={() => {
              onSubmitMeasure(scenario.scenarioId, measureDraft.trim());
              setMeasureDraft('');
            }}
            className="shrink-0 text-[11px] bg-accent text-white rounded-lg px-3 py-1.5 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}
