import { useMemo, useState } from 'react';

import type { ReviewReport as LensReviewReport } from '../../api/lens';

interface ReviewReportProps {
  report: LensReviewReport;
}

const TABS = ['Overview', 'Azure WAF', 'ATAM', 'SEI', 'Structural', 'Risks', 'Recommendations'] as const;

function ratingTone(rating: LensReviewReport['overallRating']): string {
  switch (rating) {
    case 'APPROVED': return 'bg-emerald-100 text-emerald-800';
    case 'APPROVED_WITH_CONDITIONS': return 'bg-amber-100 text-amber-800';
    case 'NEEDS_REWORK': return 'bg-orange-100 text-orange-800';
    case 'NOT_APPROVED': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-700';
  }
}

export function ReviewReport({ report }: ReviewReportProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('Overview');
  const findingCount = report.findings.length;
  const riskCount = report.risks.length;

  const scorecardEntries = useMemo(() => Object.entries(report.azureWafScorecard ?? {}), [report.azureWafScorecard]);

  return (
    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4" data-testid="review-report">
      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${activeTab === tab ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700'}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'Overview' && (
        <div className="space-y-3">
          <div className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${ratingTone(report.overallRating)}`}>
            {report.overallRating}
          </div>
          <p className="text-sm leading-6 text-gray-700 whitespace-pre-wrap">{report.executiveSummary}</p>
          {Object.keys(report.insufficientInfoGaps ?? {}).length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Some gaps could not be resolved and were carried forward as findings.
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-3 text-sm text-gray-700">
            <div className="rounded-xl bg-gray-50 p-3">Findings: {findingCount}</div>
            <div className="rounded-xl bg-gray-50 p-3">Risks: {riskCount}</div>
            <div className="rounded-xl bg-gray-50 p-3">Recommendations: {(report.recommendationRoadmap || '').length > 0 ? 1 : 0}</div>
          </div>
        </div>
      )}

      {activeTab === 'Azure WAF' && (
        <div className="space-y-3">
          {scorecardEntries.map(([pillar, value]) => (
            <div key={pillar} className="rounded-xl border border-gray-200 p-3 text-sm">
              <div className="font-semibold capitalize">{pillar}</div>
              <pre className="mt-2 overflow-x-auto text-xs text-gray-600">{JSON.stringify(value, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'ATAM' && <pre className="overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs">{JSON.stringify(report.atamAnalysis, null, 2)}</pre>}
      {activeTab === 'SEI' && <pre className="overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs">{JSON.stringify(report.seiAnalysis, null, 2)}</pre>}
      {activeTab === 'Structural' && <pre className="overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs">{JSON.stringify(report.structuralAnalysis, null, 2)}</pre>}
      {activeTab === 'Risks' && <pre className="overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs">{JSON.stringify(report.risks, null, 2)}</pre>}
      {activeTab === 'Recommendations' && <pre className="overflow-x-auto rounded-xl bg-gray-50 p-3 text-xs">{report.recommendationRoadmap}</pre>}
    </div>
  );
}
