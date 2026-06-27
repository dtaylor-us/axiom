import { useMemo, useState } from 'react';

import type { ReviewReport as LensReviewReport, ReviewRisk } from '../../api/lens';

type TabId = 'overview' | 'waf' | 'atam' | 'sei' | 'structural' | 'risks' | 'recommendations';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'waf', label: 'Azure WAF' },
  { id: 'atam', label: 'ATAM' },
  { id: 'sei', label: 'SEI' },
  { id: 'structural', label: 'Structural' },
  { id: 'risks', label: 'Risks' },
  { id: 'recommendations', label: 'Recommendations' },
];

function ratingTone(rating: LensReviewReport['overallRating']): string {
  switch (rating) {
    case 'APPROVED':
      return 'bg-emerald-100 text-emerald-800';
    case 'APPROVED_WITH_CONDITIONS':
      return 'bg-amber-100 text-amber-800';
    case 'NEEDS_REWORK':
      return 'bg-orange-100 text-orange-800';
    case 'NOT_APPROVED':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-700';
  }
}

function severityWeight(severity: string): number {
  if (severity === 'CRITICAL') return 4;
  if (severity === 'HIGH') return 3;
  if (severity === 'MEDIUM') return 2;
  if (severity === 'LOW') return 1;
  return 0;
}

function scorePercent(score: number): number {
  const safe = Math.max(0, Math.min(5, score));
  return Math.round((safe / 5) * 100);
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asArray<T>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  return [];
}

function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
}

function asDisplayText(value: unknown, fallback = 'N/A'): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    const rendered = value.map((item) => asDisplayText(item, '')).filter(Boolean).join('; ');
    return rendered || fallback;
  }
  if (value && typeof value === 'object') {
    const rendered = Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key.replace(/_/g, ' ')}: ${asDisplayText(item, '')}`)
      .filter((item) => !item.endsWith(': '))
      .join('; ');
    return rendered || fallback;
  }
  return fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? fallback : parsed;
  }
  return fallback;
}

function PillarScore({ title, score }: { title: string; score: number }) {
  const percent = scorePercent(score);
  return (
    <div className="rounded-xl border border-gray-200 p-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-800">{title}</p>
        <p className="text-xs font-semibold text-gray-600">{score.toFixed(1)} / 5</p>
      </div>
      <div className="mt-2 h-2 rounded-full bg-gray-200">
        <div className="h-2 rounded-full bg-[var(--color-pillar-lens)]" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export function ReviewReport({ report }: { report: LensReviewReport }) {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  const riskCount = report.risks.length;
  const recommendationList = asArray<Record<string, unknown>>(report.recommendationRoadmap);
  const recommendationCount = recommendationList.length;
  const findingCount = report.findings.length;

  const risks = useMemo(() => {
    const sorted = [...report.risks].sort((a, b) => severityWeight(b.severity) - severityWeight(a.severity));
    if (severityFilter === 'ALL') return sorted;
    return sorted.filter((risk) => risk.severity === severityFilter);
  }, [report.risks, severityFilter]);

  const waf = asRecord(report.azureWafScorecard);
  const wafPillars = [
    { key: 'reliability', title: 'Reliability' },
    { key: 'security', title: 'Security' },
    { key: 'cost', title: 'Cost' },
    { key: 'operational_excellence', title: 'Operational Excellence' },
    { key: 'performance_efficiency', title: 'Performance Efficiency' },
  ];

  const atam = asRecord(report.atamAnalysis);
  const sei = asRecord(report.seiAnalysis);
  const structural = asRecord(report.structuralAnalysis);

  return (
    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4" data-testid="lens-review-report">
      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${activeTab === tab.id ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-3">
          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${ratingTone(report.overallRating)}`}>
            {report.overallRating}
          </span>
          <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700">{report.executiveSummary}</p>
          {report.findings.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              {report.findings.length} insufficient-information finding(s) were included due to unresolved gap evidence.
            </div>
          )}
          <div className="grid gap-3 text-sm text-gray-700 sm:grid-cols-3">
            <div className="rounded-xl bg-gray-50 p-3">Risks: {riskCount}</div>
            <div className="rounded-xl bg-gray-50 p-3">Recommendations: {recommendationCount}</div>
            <div className="rounded-xl bg-gray-50 p-3">Findings: {findingCount}</div>
          </div>
        </div>
      )}

      {activeTab === 'waf' && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {wafPillars.map((pillar) => {
              const details = asRecord(waf[pillar.key]);
              const score = asNumber(details.score, 0);
              return <PillarScore key={pillar.key} title={pillar.title} score={score} />;
            })}
          </div>
          <div className="space-y-3">
            {wafPillars.map((pillar) => {
              const details = asRecord(waf[pillar.key]);
              const addressed = asArray<string>(details.addressed);
              const gaps = asArray<string>(details.gaps);
              const findings = asArray<string>(details.findings);
              return (
                <div key={pillar.key} className="rounded-xl border border-gray-200 p-3 text-sm">
                  <p className="font-semibold text-gray-800">{pillar.title}</p>
                  <p className="mt-1 text-xs text-gray-500">Addressed: {addressed.length} · Gaps: {gaps.length} · Findings: {findings.length}</p>
                  {gaps.length > 0 && <p className="mt-2 text-gray-700">Gaps: {gaps.join('; ')}</p>}
                  {findings.length > 0 && <p className="mt-1 text-gray-700">Findings: {findings.join('; ')}</p>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'atam' && (
        <div className="space-y-3">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="border-b border-gray-200 py-2">Scenario</th>
                <th className="border-b border-gray-200 py-2">Attribute</th>
                <th className="border-b border-gray-200 py-2">Response</th>
              </tr>
            </thead>
            <tbody>
              {asArray<Record<string, unknown>>(atam.quality_attribute_scenarios).map((scenario, index) => (
                <tr key={`scenario-${index}`} className="text-gray-700">
                  <td className="border-b border-gray-100 py-2">{asDisplayText(scenario.scenario)}</td>
                  <td className="border-b border-gray-100 py-2">{asDisplayText(scenario.attribute)}</td>
                  <td className="border-b border-gray-100 py-2">{asDisplayText(scenario.response)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 p-3 text-sm">
              <p className="font-semibold text-gray-800">Sensitivity points</p>
              <ul className="mt-2 space-y-1 text-gray-700">
                {asArray<unknown>(atam.sensitivity_points).map((item, index) => <li key={`sensitivity-${index}`}>{asDisplayText(item)}</li>)}
              </ul>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 text-sm">
              <p className="font-semibold text-gray-800">Tradeoffs</p>
              <ul className="mt-2 space-y-1 text-gray-700">
                {asArray<unknown>(atam.tradeoffs).map((item, index) => <li key={`tradeoff-${index}`}>{asDisplayText(item)}</li>)}
              </ul>
            </div>
            <div className="rounded-xl border border-gray-200 p-3 text-sm">
              <p className="font-semibold text-gray-800">ATAM risks</p>
              <ul className="mt-2 space-y-1 text-gray-700">
                {asArray<unknown>(atam.risks).map((item, index) => <li key={`atam-risk-${index}`}>{asDisplayText(item)}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sei' && (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {['modifiability', 'performance', 'availability', 'security', 'integrability'].map((attribute) => {
            const details = asRecord(sei[attribute]);
            const rating = asString(details.rating, 'UNKNOWN');
            return (
              <div key={attribute} className="rounded-xl border border-gray-200 p-3 text-sm">
                <p className="font-semibold capitalize text-gray-800">{attribute}</p>
                <p className="mt-1 text-xs text-gray-500">Rating: {rating}</p>
                <p className="mt-2 font-medium text-gray-700">Tactics present</p>
                <ul className="mt-1 space-y-1 text-gray-700">
                  {asArray<string>(details.tactics_present).map((item) => <li key={item}>• {item}</li>)}
                </ul>
                <p className="mt-2 font-medium text-gray-700">Tactics missing</p>
                <ul className="mt-1 space-y-1 text-gray-700">
                  {asArray<string>(details.tactics_missing).map((item) => <li key={item}>• {item}</li>)}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {activeTab === 'structural' && (
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <PillarScore title="Coupling" score={asNumber(structural.coupling_score, 0)} />
            <PillarScore title="Cohesion" score={asNumber(structural.cohesion_score, 0)} />
            <PillarScore title="Dependency direction" score={asNumber(structural.dependency_direction_score, 0)} />
            <PillarScore title="Boundary clarity" score={asNumber(structural.boundary_clarity_score, 0)} />
          </div>
          <div className="rounded-xl border border-gray-200 p-3 text-sm text-gray-700">
            <p className="font-semibold text-gray-800">Observations</p>
            <ul className="mt-2 space-y-1">
              {asArray<string>(structural.observations).map((item) => <li key={item}>• {item}</li>)}
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'risks' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500" htmlFor="risk-filter">Severity</label>
            <select
              id="risk-filter"
              className="rounded-lg border border-gray-300 px-2 py-1 text-xs"
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
            >
              <option value="ALL">All</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="border-b border-gray-200 py-2">Severity</th>
                  <th className="border-b border-gray-200 py-2">Title</th>
                  <th className="border-b border-gray-200 py-2">Likelihood</th>
                  <th className="border-b border-gray-200 py-2">Area</th>
                  <th className="border-b border-gray-200 py-2">Mitigation</th>
                </tr>
              </thead>
              <tbody>
                {risks.map((risk: ReviewRisk) => (
                  <tr key={`${risk.title}-${risk.severity}`} className="text-gray-700">
                    <td className="border-b border-gray-100 py-2">{risk.severity}</td>
                    <td className="border-b border-gray-100 py-2">{risk.title}</td>
                    <td className="border-b border-gray-100 py-2">{risk.likelihood}</td>
                    <td className="border-b border-gray-100 py-2">{risk.affectedArea ?? 'N/A'}</td>
                    <td className="border-b border-gray-100 py-2">{risk.mitigationStrategy ?? 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'recommendations' && (
        <div className="space-y-3">
          {['P1', 'P2', 'P3'].map((priority) => {
            const bucket = recommendationList.filter((item) => asString(item.priority, 'P3') === priority);
            return (
              <div key={priority} className="rounded-xl border border-gray-200 p-3 text-sm">
                <p className="font-semibold text-gray-800">{priority} recommendations ({bucket.length})</p>
                <div className="mt-2 space-y-2">
                  {bucket.map((item, index) => (
                    <div key={`${priority}-${index}`} className="rounded-lg bg-gray-50 p-3">
                      <p className="font-medium text-gray-900">{asString(item.title, 'Untitled recommendation')}</p>
                      <p className="mt-1 text-gray-700">{asString(item.description, 'No description provided.')}</p>
                      <p className="mt-2 text-xs text-gray-500">
                        Effort: {asString(item.effort, 'unknown')} · Addresses risk: {asString(item.addresses_risk, 'N/A')}
                      </p>
                    </div>
                  ))}
                  {bucket.length === 0 && <p className="text-gray-500">No recommendations in this priority group.</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
