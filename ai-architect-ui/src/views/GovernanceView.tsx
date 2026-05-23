import { useState } from 'react';
import { useGovernance } from '../hooks/useGovernance';
import { useTactics } from '../hooks/useTactics';
import { useBuyVsBuild } from '../hooks/useBuyVsBuild';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { SeverityGrid } from '../components/SeverityGrid';
import { CopyButton } from '../components/CopyButton';
import { StructuredExportBar } from '../components/StructuredData';
import type { Weakness, TacticRecommendation, TradeOffDecision, AdlDocument, FmeaEntry, BuyVsBuildDecision } from '../types/api';

/* ── Badge helpers ────────────────────────────── */

function severityBadgeClass(w: Weakness): string {
  if (w.severity >= 8) return 'bg-red-100 text-red-700';
  if (w.severity >= 6) return 'bg-orange-100 text-orange-700';
  if (w.severity >= 4) return 'bg-yellow-100 text-yellow-700';
  return 'bg-green-100 text-green-700';
}

function priorityBadgeClass(priority: TacticRecommendation['priority']): string {
  switch (priority) {
    case 'critical': return 'bg-red-100 text-red-700';
    case 'recommended': return 'bg-yellow-100 text-yellow-700';
    case 'optional': return 'bg-gray-100 text-gray-600';
  }
}

function effortBadgeClass(effort: TacticRecommendation['effort']): string {
  switch (effort) {
    case 'high': return 'bg-orange-100 text-orange-700';
    case 'medium': return 'bg-blue-100 text-blue-700';
    case 'low': return 'bg-green-100 text-green-700';
  }
}

/* ── Markdown builders ────────────────────────── */

function tradeOffMarkdown(tradeOffs: TradeOffDecision[]): string {
  return tradeOffs.map((t) => [
    `## ${t.decision}`,
    `**Confidence:** ${t.confidence}`,
    `**Optimises:** ${(t.optimises_characteristics ?? []).join(', ')}`,
    `**Sacrifices:** ${(t.sacrifices_characteristics ?? []).join(', ')}`,
    `**Recommendation:** ${t.recommendation}`,
    `**Context:** ${t.context_dependency}`,
  ].join('\n')).join('\n\n');
}

function adlMarkdown(adl: AdlDocument): string {
  const ruleLines = adl.rules.map((r) => [
    `### [${r.rule_id}] ${r.subject} (${r.category})`,
    r.statement,
    r.rationale ? `*${r.rationale}*` : '',
    r.validation_hint?.pseudo_code ? `\`\`\`\n${r.validation_hint.pseudo_code}\n\`\`\`` : '',
  ].filter(Boolean).join('\n'));
  return [adl.document, '', '---', '', '## Rules', '', ...ruleLines].join('\n');
}

function weaknessMarkdown(weaknesses: Weakness[]): string {
  return weaknesses.map((w) => [
    `## ${w.id}: ${w.title} (Severity ${w.severity}/10)`,
    w.category ? `**Category:** ${w.category}` : '',
    w.description,
    `**Affected:** ${w.component_affected}`,
    `**Mitigation:** ${w.mitigation}`,
    w.effort_to_fix ? `**Effort:** ${w.effort_to_fix}` : '',
  ].filter(Boolean).join('\n')).join('\n\n');
}

function fmeaMarkdown(entries: FmeaEntry[]): string {
  const header = '| ID | Failure Mode | Component | S | O | D | RPN | Action |';
  const sep = '|----|-------------|-----------|---|---|---|-----|--------|';
  const rows = entries
    .sort((a, b) => b.rpn - a.rpn)
    .map((e) => `| ${e.id} | ${e.failure_mode} | ${e.component} | ${e.severity} | ${e.occurrence} | ${e.detection} | ${e.rpn} | ${e.recommended_action} |`);
  return [header, sep, ...rows].join('\n');
}

function tacticsMarkdown(tactics: TacticRecommendation[]): string {
  const grouped = tactics.reduce<Record<string, TacticRecommendation[]>>((acc, t) => {
    (acc[t.characteristicName] ??= []).push(t);
    return acc;
  }, {});
  return Object.entries(grouped).map(([char, items]) => [
    `## ${char}`,
    ...items.map((t) => [
      `### ${t.tacticName} [${t.priority}] — ${t.effort} effort`,
      t.description,
      `**Application:** ${t.concreteApplication}`,
      t.alreadyAddressed ? `✓ Already addressed${t.addressEvidence ? `: ${t.addressEvidence}` : ''}` : '',
    ].filter(Boolean).join('\n')),
  ].join('\n\n')).join('\n\n');
}

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/* ── Types ────────────────────────────────────── */

type Tab = 'trade-offs' | 'adl' | 'weaknesses' | 'fmea' | 'tactics';

/* ── Component ────────────────────────────────── */

export function GovernanceView() {
  const [activeTab, setActiveTab] = useState<Tab | 'sourcing'>('trade-offs');
  const [sourcingFilter, setSourcingFilter] = useState<'all' | 'build' | 'buy' | 'adopt'>('all');
  const [sourcingConflictsOnly, setSourcingConflictsOnly] = useState(false);
  const { tradeOffs, adl, weaknesses, fmea, governanceReport, loading, error } = useGovernance();
  const { tactics, summary: tacticsSummary, loading: tacticsLoading } = useTactics();
  const { summary: sourcingSummary } = useBuyVsBuild({
    recommendation: sourcingFilter === 'all' ? undefined : sourcingFilter,
  });

  const tabs: { key: Tab | 'sourcing'; label: string }[] = [
    { key: 'trade-offs', label: 'Trade-offs' },
    { key: 'adl', label: 'ADL' },
    { key: 'weaknesses', label: 'Weaknesses' },
    { key: 'fmea', label: 'FMEA' },
    { key: 'tactics', label: 'Tactics' },
    { key: 'sourcing', label: 'Sourcing' },
  ];

  /* Derive markdown and filename for the active tab */
  function activeTabContent(): { md: string; filename: string } | null {
    switch (activeTab) {
      case 'trade-offs':
        return tradeOffs.length > 0
          ? { md: tradeOffMarkdown(tradeOffs), filename: 'trade-offs.md' }
          : null;
      case 'adl':
        return adl ? { md: adlMarkdown(adl), filename: 'adl.md' } : null;
      case 'weaknesses':
        return weaknesses && weaknesses.weaknesses.length > 0
          ? { md: weaknessMarkdown(weaknesses.weaknesses), filename: 'weaknesses.md' }
          : null;
      case 'fmea':
        return fmea.length > 0
          ? { md: fmeaMarkdown(fmea), filename: 'fmea.md' }
          : null;
      case 'tactics':
        return tactics.length > 0
          ? { md: tacticsMarkdown(tactics), filename: 'tactics.md' }
          : null;
      case 'sourcing':
        return null;
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-500" data-testid="governance-loading">
        <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
          <path d="M8 2a6 6 0 0 1 6 6" />
        </svg>
        Loading governance data…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6" data-testid="governance-error">
        <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          <p className="text-sm font-semibold text-red-800">Unable to load governance</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  const tabContent = activeTabContent();
  const structured = {
    kind: 'governance_report',
    activeTab,
    tradeOffs,
    adl,
    weaknesses,
    fmea,
    tactics,
    tacticsSummary,
    sourcingSummary,
  };

  return (
    <div className="p-6" data-testid="governance-view">
      <StructuredExportBar
        title="Governance"
        json={structured}
        filename="governance-report.json"
        extraRight={
          tabContent ? (
            <>
              <CopyButton text={tabContent.md} label="Copy MD" title="Copy tab content as Markdown" />
              <button
                type="button"
                onClick={() => downloadMarkdown(tabContent.filename, tabContent.md)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                title="Download Markdown file"
              >
                <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" />
                </svg>
                Download .md
              </button>
            </>
          ) : undefined
        }
      />

      {/* ── Governance score + degradation warning ── */}
      {governanceReport && (
        <div className="pt-4 space-y-3" data-testid="governance-score-section">
          {!governanceReport.reviewCompletedFully && (
            <div
              className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3"
              data-testid="review-degradation-banner"
            >
              <svg className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 2L1 14h14L8 2z" /><path d="M8 7v3M8 11.5v.5" />
              </svg>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-amber-900">Review completed with degradation</p>
                <p className="text-sm text-amber-800 mt-1">
                  Some review checks failed: <span className="font-semibold">{(governanceReport.failedReviewNodes ?? []).join(', ') || 'unknown'}</span>.
                  The governance score may be incomplete.
                </p>
              </div>
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-start justify-between gap-3" data-testid="governance-score-card">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-800">Governance score</p>
              <p className="text-xs text-gray-500 mt-1">
                Confidence: <span className="font-semibold">{governanceReport.governanceScoreConfidence}</span>
              </p>
            </div>
            <div className="text-right shrink-0">
              {governanceReport.governanceScoreConfidence === 'unavailable' || governanceReport.governanceScore == null ? (
                <p className="text-sm font-semibold text-gray-700">Score unavailable</p>
              ) : (
                <p className="text-2xl font-bold text-gray-900">
                  {governanceReport.governanceScore}
                  {(governanceReport.governanceScoreConfidence === 'partial' || governanceReport.governanceScoreConfidence === 'low') && (
                    <span className="text-sm font-semibold text-gray-500"> (partial)</span>
                  )}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab bar ── */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 mb-4 pt-3">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === key
                ? 'border-b-2 border-accent text-accent'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            data-testid={`tab-${key}`}
            aria-current={activeTab === key ? 'page' : undefined}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Trade-offs ── */}
      {activeTab === 'trade-offs' && (
        <div data-testid="panel-trade-offs">
          {tradeOffs.length === 0 ? (
            <p className="text-gray-400 italic">No trade-off decisions available</p>
          ) : (
            <div className="space-y-3">
              {tradeOffs.map((t) => (
                <div
                  key={t.decision_id}
                  className="group border border-gray-200 rounded-lg p-4 bg-white hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-sm">{t.decision}</h3>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className={`text-xs rounded px-2 py-0.5 font-medium ${
                        t.confidence === 'high' ? 'bg-green-100 text-green-700' :
                        t.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{t.confidence}</span>
                      <CopyButton
                        text={[
                          t.decision,
                          `Optimises: ${(t.optimises_characteristics ?? []).join(', ')}`,
                          `Sacrifices: ${(t.sacrifices_characteristics ?? []).join(', ')}`,
                          `Recommendation: ${t.recommendation}`,
                          `Context: ${t.context_dependency}`,
                        ].join('\n')}
                        className="opacity-0 group-hover:opacity-100"
                        title="Copy decision"
                      />
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-gray-600 space-y-1">
                    <p>
                      <span className="font-medium text-green-700">Optimises:</span>{' '}
                      {(t.optimises_characteristics ?? []).join(', ')}
                    </p>
                    <p>
                      <span className="font-medium text-red-700">Sacrifices:</span>{' '}
                      {(t.sacrifices_characteristics ?? []).join(', ')}
                    </p>
                    <p>
                      <span className="font-medium">Recommendation:</span>{' '}
                      {t.recommendation}
                    </p>
                    <p>
                      <span className="font-medium">Context dependency:</span>{' '}
                      {t.context_dependency}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Sourcing ── */}
      {activeTab === 'sourcing' && (
        <div data-testid="panel-sourcing" className="space-y-4">
          {!sourcingSummary ? (
            <p className="text-gray-400 italic">No sourcing decisions available</p>
          ) : (
            <>
              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-800">Summary</p>
                {sourcingSummary.summaryText ? (
                  <p className="text-sm text-gray-600 mt-2">{sourcingSummary.summaryText}</p>
                ) : (
                  <p className="text-sm text-gray-400 mt-2 italic">No summary text available</p>
                )}

                <div className="flex flex-wrap gap-2 mt-3">
                  <span className="text-xs font-semibold rounded-full bg-gray-100 text-gray-700 px-3 py-1">Total {sourcingSummary.totalDecisions}</span>
                  <span className="text-xs font-semibold rounded-full bg-blue-50 text-blue-700 px-3 py-1">Build {sourcingSummary.buildCount}</span>
                  <span className="text-xs font-semibold rounded-full bg-purple-50 text-purple-700 px-3 py-1">Buy {sourcingSummary.buyCount}</span>
                  <span className="text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 px-3 py-1">Adopt {sourcingSummary.adoptCount}</span>
                </div>

                {sourcingSummary.conflictCount > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-3 text-amber-900">
                    <p className="text-sm font-semibold">Preference conflicts: {sourcingSummary.conflictCount}</p>
                    <p className="text-sm mt-1">
                      Some recommendations conflict with your stated preferences. Review conflicts below.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <label className="text-sm text-gray-600">
                  Filter:
                  <select
                    className="ml-2 border border-gray-200 rounded-lg px-2 py-1 text-sm"
                    value={sourcingFilter}
                    onChange={(e) => setSourcingFilter(e.target.value as any)}
                  >
                    <option value="all">All</option>
                    <option value="build">Build only</option>
                    <option value="buy">Buy only</option>
                    <option value="adopt">Adopt only</option>
                  </select>
                </label>

                <label className="text-sm text-gray-600 inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={sourcingConflictsOnly}
                    onChange={(e) => setSourcingConflictsOnly(e.target.checked)}
                  />
                  Show conflicts only
                </label>
              </div>

              <div className="space-y-3">
                {sourcingSummary.decisions
                  .filter((d: BuyVsBuildDecision) => !sourcingConflictsOnly || d.conflictsWithUserPreference)
                  .map((d: BuyVsBuildDecision) => (
                    <div key={d.componentName} className="border border-gray-200 rounded-xl p-4 bg-white">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-sm text-gray-900">{d.componentName}</p>
                            {d.isCoreeDifferentiator && (
                              <span className="text-[11px] font-semibold rounded-full bg-blue-50 text-blue-700 px-2 py-0.5">
                                Core differentiator
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Alternatives evaluated: {(d.alternativesConsidered ?? []).join(', ')}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[11px] font-semibold rounded px-2 py-0.5 ${
                            d.recommendation === 'build' ? 'bg-blue-50 text-blue-700' :
                            d.recommendation === 'buy' ? 'bg-purple-50 text-purple-700' :
                            'bg-emerald-50 text-emerald-700'
                          }`}>
                            {d.recommendation.toUpperCase()}
                          </span>
                          <span className="text-[11px] rounded px-2 py-0.5 bg-gray-100 text-gray-700">
                            Integration: {d.integrationEffort}
                          </span>
                        </div>
                      </div>

                      <div className="mt-3 text-sm text-gray-700 space-y-2">
                        <p>
                          <span className="font-semibold">Solution:</span>{' '}
                          {d.recommendedSolution ? d.recommendedSolution : 'Custom build'}
                        </p>
                        <p>{d.rationale}</p>
                        <p><span className="font-semibold">Estimated cost:</span> {d.estimatedBuildCost}</p>
                        <p><span className="font-semibold">Lock-in risk:</span> {d.vendorLockInRisk}</p>
                      </div>

                      {d.conflictsWithUserPreference && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-3 text-amber-900">
                          <p className="text-xs font-semibold flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M8 2L1 14h14L8 2z" /><path d="M8 7v3M8 11.5v.5" />
                            </svg>
                            Preference conflict
                          </p>
                          <p className="text-sm mt-1">{d.conflictExplanation}</p>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ADL ── */}
      {activeTab === 'adl' && (
        <div data-testid="panel-adl">
          {!adl ? (
            <p className="text-gray-400 italic">No ADL document available</p>
          ) : (
            <div className="space-y-4">
              <div className="relative group bg-white border border-gray-200 rounded-lg p-4">
                <CopyButton
                  text={adl.document}
                  label="Copy document"
                  title="Copy ADL document"
                  className="absolute top-3 right-3"
                />
                <MarkdownRenderer content={adl.document} />
              </div>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Rules ({adl.rules.length})</h3>
                <CopyButton
                  text={adl.rules.map((r) => `[${r.rule_id}] ${r.subject}: ${r.statement}`).join('\n')}
                  label="Copy all rules"
                  title="Copy all rules as text"
                />
              </div>
              <div className="space-y-2">
                {adl.rules.map((r, i) => (
                  <div
                    key={i}
                    className="group border border-gray-200 rounded-lg p-3 text-xs bg-gray-50 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-bold text-emerald-700 uppercase shrink-0">{r.category}</span>
                        <span className="font-mono text-gray-400 shrink-0">{r.rule_id}</span>
                        <span className="font-medium text-purple-700 truncate">{r.subject}</span>
                      </div>
                      <CopyButton
                        text={`[${r.rule_id}] ${r.subject}\n${r.statement}${r.rationale ? `\nRationale: ${r.rationale}` : ''}`}
                        className="opacity-0 group-hover:opacity-100 shrink-0"
                        title="Copy rule"
                      />
                    </div>
                    <p className="text-gray-700">{r.statement}</p>
                    {r.rationale && (
                      <p className="text-gray-500 mt-1 italic">{r.rationale}</p>
                    )}
                    {r.validation_hint?.pseudo_code && (
                      <pre className="whitespace-pre-wrap mt-1 text-gray-500 text-xs bg-gray-100 rounded p-1 overflow-x-auto">
                        {r.validation_hint.pseudo_code}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Weaknesses ── */}
      {activeTab === 'weaknesses' && (
        <div data-testid="panel-weaknesses">
          {!weaknesses || weaknesses.weaknesses.length === 0 ? (
            <p className="text-gray-400 italic">No weaknesses identified</p>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
                {weaknesses.summary}
              </p>
              <div className="space-y-3">
                {weaknesses.weaknesses.map((w) => (
                  <div
                    key={w.id}
                    className="group border border-gray-200 rounded-lg p-3 bg-white hover:border-gray-300 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap min-w-0">
                        <span className="font-mono text-xs text-gray-500 shrink-0">{w.id}</span>
                        <h3 className="font-semibold text-sm">{w.title}</h3>
                        <span className={`text-xs rounded px-2 py-0.5 font-medium shrink-0 ${severityBadgeClass(w)}`}>
                          Severity {w.severity}/10
                        </span>
                        {w.category && (
                          <span className="text-xs rounded px-2 py-0.5 font-medium bg-gray-100 text-gray-600 shrink-0">
                            {w.category}
                          </span>
                        )}
                      </div>
                      <CopyButton
                        text={[
                          `${w.id}: ${w.title} (Severity ${w.severity}/10)`,
                          w.description,
                          `Affected: ${w.component_affected}`,
                          `Mitigation: ${w.mitigation}`,
                          w.effort_to_fix ? `Effort: ${w.effort_to_fix}` : '',
                        ].filter(Boolean).join('\n')}
                        className="opacity-0 group-hover:opacity-100 shrink-0"
                        title="Copy weakness"
                      />
                    </div>
                    <p className="text-xs text-gray-600 mt-1">{w.description}</p>
                    <p className="text-xs mt-1">
                      <span className="font-medium">Affected:</span>{' '}
                      {w.component_affected}
                    </p>
                    <p className="text-xs mt-1">
                      <span className="font-medium">Mitigation:</span>{' '}
                      {w.mitigation}
                    </p>
                    {w.effort_to_fix && (
                      <p className="text-xs mt-1">
                        <span className="font-medium">Effort:</span>{' '}
                        {w.effort_to_fix}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── FMEA ── */}
      {activeTab === 'fmea' && (
        <div data-testid="panel-fmea">
          <SeverityGrid entries={fmea} />
        </div>
      )}

      {/* ── Tactics ── */}
      {activeTab === 'tactics' && (
        <div data-testid="panel-tactics">
          {tacticsLoading ? (
            <div className="flex items-center gap-2 text-gray-400 italic">
              <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
                <path d="M8 2a6 6 0 0 1 6 6" />
              </svg>
              Loading tactics…
            </div>
          ) : tactics.length === 0 ? (
            <p className="text-gray-400 italic">No tactic recommendations available</p>
          ) : (
            <div className="space-y-4">
              {/* Summary card */}
              {tacticsSummary && (
                <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div>
                    <p className="text-2xl font-bold text-blue-800">{tacticsSummary.totalTactics}</p>
                    <p className="text-xs text-blue-600">Total tactics</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-700">{tacticsSummary.criticalCount}</p>
                    <p className="text-xs text-red-500">Critical</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-emerald-700">{tacticsSummary.alreadyAddressedCount}</p>
                    <p className="text-xs text-emerald-600">Already addressed</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-orange-700">{tacticsSummary.newTacticsCount}</p>
                    <p className="text-xs text-orange-500">To implement</p>
                  </div>
                </div>
              )}
              {/* Tactic list grouped by characteristic */}
              {Object.entries(
                tactics.reduce<Record<string, typeof tactics>>((acc, t) => {
                  (acc[t.characteristicName] ??= []).push(t);
                  return acc;
                }, {}),
              ).map(([char, charTactics]) => (
                <div key={char}>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2 mt-3">
                    {char}
                  </h3>
                  <div className="space-y-2">
                    {charTactics.map((t) => (
                      <div
                        key={t.id}
                        className={`group border rounded-lg p-3 bg-white hover:shadow-sm transition-all ${
                          t.alreadyAddressed
                            ? 'border-gray-100 opacity-70'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        data-testid={`tactic-${t.tacticId}`}
                      >
                        <div className="flex items-start gap-2 flex-wrap">
                          <h4 className="font-semibold text-sm flex-1">{t.tacticName}</h4>
                          <span className={`text-xs rounded px-2 py-0.5 font-medium shrink-0 ${priorityBadgeClass(t.priority)}`}>
                            {t.priority}
                          </span>
                          <span className={`text-xs rounded px-2 py-0.5 font-medium shrink-0 ${effortBadgeClass(t.effort)}`}>
                            {t.effort} effort
                          </span>
                          {t.alreadyAddressed && (
                            <span className="text-xs rounded px-2 py-0.5 font-medium bg-emerald-50 text-emerald-600 shrink-0">
                              ✓ addressed
                            </span>
                          )}
                          <CopyButton
                            text={[
                              `${t.tacticName} [${t.priority}] — ${t.effort} effort`,
                              t.description,
                              `Application: ${t.concreteApplication}`,
                              t.implementationExamples.length > 0 ? `Examples: ${t.implementationExamples.join(', ')}` : '',
                            ].filter(Boolean).join('\n')}
                            className="opacity-0 group-hover:opacity-100 shrink-0"
                            title="Copy tactic"
                          />
                        </div>
                        <p className="text-xs text-gray-600 mt-1">{t.description}</p>
                        <p className="text-xs mt-1">
                          <span className="font-medium">Application:</span>{' '}
                          {t.concreteApplication}
                        </p>
                        {t.implementationExamples.length > 0 && (
                          <p className="text-xs mt-1 text-gray-500">
                            {t.implementationExamples.join(' · ')}
                          </p>
                        )}
                        {t.alreadyAddressed && t.addressEvidence && (
                          <p className="text-xs mt-1 italic text-emerald-700">
                            Evidence: {t.addressEvidence}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
