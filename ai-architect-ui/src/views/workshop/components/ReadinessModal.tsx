import type {
  GenerationReadinessDto,
  AttributePreviewDto,
  HighValueGapDto,
} from '../../../types/workshop';

type ReadinessLevel = GenerationReadinessDto['overallReadiness'];

function readinessBadge(level: ReadinessLevel): { label: string; className: string } {
  switch (level) {
    case 'insufficient':
      return { label: 'Limited evidence', className: 'bg-red-50 text-red-800 ring-red-200' };
    case 'partial':
      return { label: 'Partial evidence', className: 'bg-amber-50 text-amber-900 ring-amber-200' };
    case 'adequate':
      return { label: 'Adequate evidence', className: 'bg-sky-50 text-sky-900 ring-sky-200' };
    case 'strong':
      return { label: 'Strong evidence', className: 'bg-emerald-50 text-emerald-900 ring-emerald-200' };
    default:
      return { label: level || 'Evidence', className: 'bg-gray-50 text-gray-800 ring-gray-200' };
  }
}

function ConfidenceChip({ level }: { level: AttributePreviewDto['confidence'] }) {
  const styles: Record<string, string> = {
    confirmed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    inferred: 'bg-amber-50 text-amber-900 ring-amber-200',
    tentative: 'bg-gray-50 text-gray-700 ring-gray-200',
  };
  const c = styles[level] ?? styles.tentative;
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${c}`}>{level}</span>
  );
}

interface Props {
  open: boolean;
  data: GenerationReadinessDto | null;
  onClose: () => void;
  onKeepGoing: () => void;
  onGenerateAnyway: () => void;
}

export function ReadinessModal({
  open,
  data,
  onClose,
  onKeepGoing,
  onGenerateAnyway,
}: Props) {
  if (!open || !data) return null;

  const badge = readinessBadge(data.overallReadiness);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" role="dialog" aria-modal="true">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto border border-gray-200">
        <div className="p-5 border-b border-gray-100">
          <div className="flex justify-between items-start gap-2">
            <h2 className="text-[15px] font-semibold text-gray-900">
              What you would get if you generate now
            </h2>
            <button
              type="button"
              className="shrink-0 text-gray-400 hover:text-gray-600 text-[20px] leading-none"
              onClick={onClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ${badge.className}`}>
              {badge.label}
            </span>
          </div>
        </div>

        <div className="p-5 space-y-5 text-[13px] text-gray-700">
          <p className="leading-relaxed whitespace-pre-wrap">{data.confidenceNote}</p>

          {data.attributePreview.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Attribute preview
              </p>
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-[12px]">
                  <thead className="bg-gray-50 text-gray-600 text-left">
                    <tr>
                      <th className="px-3 py-2 font-medium">Attribute</th>
                      <th className="px-3 py-2 font-medium">Confidence</th>
                      <th className="px-3 py-2 font-medium">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.attributePreview.map((row, i) => (
                      <tr key={i} className="border-t border-gray-100">
                        <td className="px-3 py-2 align-top font-medium text-gray-900">{row.name}</td>
                        <td className="px-3 py-2 align-top">
                          <ConfidenceChip level={row.confidence} />
                        </td>
                        <td className="px-3 py-2 align-top text-gray-600">{row.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.highValueGaps.length > 0 && (
            <div>
              <p className="text-[12px] font-medium text-gray-800 mb-2">
                If you have a few more minutes, these would most improve the output:
              </p>
              <ol className="list-decimal list-inside space-y-2 text-[12px] text-gray-700">
                {data.highValueGaps.map((g: HighValueGapDto, i: number) => (
                  <li key={g.gapId || i}>
                    <span className="font-medium">{g.description}</span>
                    {g.impact ? (
                      <span className="text-gray-600">
                        {' '}
                        → {g.impact}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {data.missingDomains.length > 0 && (
            <div>
              <p className="text-[12px] text-gray-700 mb-1">
                These quality attributes have no evidence yet and will not appear in the output:
              </p>
              <p className="text-[12px] text-gray-500">
                {data.missingDomains.join('  ·  ')}
              </p>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-gray-100 flex flex-col sm:flex-row gap-2">
          <button
            type="button"
            onClick={() => {
              onKeepGoing();
              onClose();
            }}
            className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-[13px] font-medium text-gray-800 hover:bg-gray-50"
          >
            Keep going — fill the gaps above
          </button>
          <button
            type="button"
            onClick={() => {
              onGenerateAnyway();
              onClose();
            }}
            className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-[13px] font-medium text-gray-800 hover:bg-gray-50"
          >
            Generate now anyway
          </button>
        </div>
      </div>
    </div>
  );
}
