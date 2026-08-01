import type { RefObject } from 'react';

interface Props {
  /** At least one completed conversation turn with the agent */
  turnComplete: boolean;
  generationCount: number;
  attributesStale: boolean;
  continuationPrompt?: string | null;
  previewLoading: boolean;
  generateLoading: boolean;
  onPreview: () => void;
  onGenerate: () => void;
  panelRef?: RefObject<HTMLDivElement | null>;
}

export function GeneratePanel({
  turnComplete,
  generationCount,
  attributesStale,
  continuationPrompt,
  previewLoading,
  generateLoading,
  onPreview,
  onGenerate,
  panelRef,
}: Props) {
  if (!turnComplete) return null;

  const stateB = generationCount > 0 && attributesStale;
  const stateC = generationCount > 0 && !attributesStale;
  const stateA = generationCount === 0;

  let borderClass = 'border-gray-200 bg-white';
  let title = '';
  let body = '';
  let previewLabel = 'Preview what you\'d get →';
  let actionLabel = 'Generate ↓';

  if (stateB) {
    borderClass = 'border-l-4 border-l-amber-400 border-y border-r border-amber-100/80 bg-amber-50/40';
    title = '↻ New context available';
    body =
      'You have provided additional information since your last generation. Regenerate to update your quality attributes.';
    previewLabel = 'Preview changes →';
    actionLabel = 'Regenerate ↓';
  } else if (stateC) {
    borderClass = 'border-l-4 border-l-emerald-500 border-y border-r border-emerald-100 bg-emerald-50/30';
    title = `✓ Attributes generated (pass ${generationCount})`;
    body = 'Continue providing context to refine them.';
    previewLabel = 'Regenerate with new context ↓';
    actionLabel = 'Regenerate with new context ↓';
  } else if (stateA) {
    title = 'Ready to generate?';
    body = 'Generate quality attributes from your current evidence at any time.';
  }

  return (
    <div
      ref={panelRef}
      data-testid="workshop-generate-panel"
      className={`mx-2 sm:mx-3 mb-2 rounded-xl border px-3 sm:px-4 py-3 ${borderClass}`}
    >
      <p className="text-[13px] font-semibold text-gray-900">{title}</p>
      <p className="text-[12px] text-gray-600 mt-1 leading-relaxed">{body}</p>
      {stateC && continuationPrompt ? (
        <p className="text-[11px] text-gray-500 mt-2 leading-relaxed border-t border-emerald-100/80 pt-2">
          {continuationPrompt}
        </p>
      ) : null}
      <div className="mt-3 flex flex-col sm:flex-row flex-wrap gap-2">
        {stateC ? null : (
          <button
            type="button"
            onClick={onPreview}
            disabled={previewLoading || generateLoading}
            className="w-full sm:w-auto rounded-xl border border-gray-300 bg-white px-3 py-2 text-[12px] font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-50 text-left sm:text-center"
          >
            {previewLoading ? 'Loading…' : previewLabel}
          </button>
        )}
        <button
          type="button"
          onClick={onGenerate}
          disabled={generateLoading || previewLoading}
          className="w-full sm:w-auto rounded-xl border border-gray-300 bg-white px-3 py-2 text-[12px] font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-50 text-left sm:text-center"
        >
          {generateLoading ? 'Working…' : actionLabel}
        </button>
      </div>
    </div>
  );
}
