import { useState } from 'react';
import { useArchDoc } from '../hooks/useArchDoc';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { MarkdownExportActions, downloadMarkdown } from '../components/StructuredData';

type Tab = 'overview' | 'module' | 'cc' | 'allocation' | 'risk';

const TABS: { key: Tab; label: string; description: string }[] = [
  { key: 'overview', label: 'Overview', description: 'Stakeholders, glossary, SLO targets' },
  { key: 'module', label: 'Module View', description: 'Components, implementation guidance' },
  { key: 'cc', label: 'C&C View', description: 'Runtime interactions, QA scenarios' },
  { key: 'allocation', label: 'Allocation', description: 'Deployment, build sequence, teams' },
  { key: 'risk', label: 'Risk & Decisions', description: 'ADRs, risk register, fitness functions' },
];

export function ArchDocView() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const {
    systemTitle,
    overviewMarkdown,
    moduleViewMarkdown,
    ccViewMarkdown,
    allocationViewMarkdown,
    riskMarkdown,
    fullPackageMarkdown,
    exportFilename,
    components,
    tactics,
    buildSequence,
    allAdlRules,
    fmeaAll,
    loading,
    error,
    hasData,
  } = useArchDoc();

  function getTabContent(): string {
    switch (activeTab) {
      case 'overview': return overviewMarkdown;
      case 'module': return moduleViewMarkdown;
      case 'cc': return ccViewMarkdown;
      case 'allocation': return allocationViewMarkdown;
      case 'risk': return riskMarkdown;
    }
  }

  function getTabFilename(): string {
    const base = exportFilename.replace('.md', '');
    switch (activeTab) {
      case 'overview': return `${base}-overview.md`;
      case 'module': return `${base}-module-view.md`;
      case 'cc': return `${base}-cc-view.md`;
      case 'allocation': return `${base}-allocation-view.md`;
      case 'risk': return `${base}-risk.md`;
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-500" data-testid="arch-doc-loading">
        <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
          <path d="M8 2a6 6 0 0 1 6 6" />
        </svg>
        Loading documentation package…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6" data-testid="arch-doc-error">
        <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          <p className="text-sm font-semibold text-red-800">Unable to load architecture documentation</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6 py-12">
        <svg className="w-12 h-12 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h2 className="text-lg font-semibold text-gray-700">No architecture data yet</h2>
        <p className="text-sm text-gray-500 max-w-sm">
          Complete an architecture analysis in Chat to generate the full documentation package.
        </p>
      </div>
    );
  }

  const tabContent = getTabContent();

  // Summary stats for header bar
  const criticalTacticCount = tactics.filter((t) => t.priority === 'critical' && !t.alreadyAddressed).length;
  const hardAdlCount = (allAdlRules as (typeof allAdlRules[number] & Record<string, unknown>)[])
    .filter((r) => r['enforcement_level'] === 'hard' || r.validation_hint?.enforcement_level === 'hard').length;

  return (
    <div className="flex flex-col h-full" data-testid="arch-doc-view">
      {/* Top bar */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 sticky top-0 z-10 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-gray-900 truncate">
            Arch Docs — {systemTitle}
          </h1>
          <div className="flex items-center gap-3 mt-0.5">
            {components.length > 0 && (
              <span className="text-xs text-gray-500">{components.length} components</span>
            )}
            {buildSequence.length > 0 && (
              <span className="text-xs text-gray-500">
                {buildSequence.filter((s) => s.phase === 1).length}P1 ·{' '}
                {buildSequence.filter((s) => s.phase === 2).length}P2 ·{' '}
                {buildSequence.filter((s) => s.phase === 3).length}P3
              </span>
            )}
            {criticalTacticCount > 0 && (
              <span className="text-xs bg-red-50 text-red-700 rounded-full px-1.5 py-0.5 font-medium">
                {criticalTacticCount} critical tactics open
              </span>
            )}
            {hardAdlCount > 0 && (
              <span className="text-xs bg-orange-50 text-orange-700 rounded-full px-1.5 py-0.5 font-medium">
                {hardAdlCount} hard ADL rules
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => downloadMarkdown(exportFilename, fullPackageMarkdown)}
          disabled={!hasData}
          className="flex items-center gap-1.5 shrink-0 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" />
          </svg>
          Export full package
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 px-6 pt-3 bg-white">
        {TABS.map(({ key, label, description }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            title={description}
            className={`px-3 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === key
                ? 'border-b-2 border-accent text-accent'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            data-testid={`tab-${key}`}
            aria-current={activeTab === key ? 'page' : undefined}
          >
            {label}
            {key === 'risk' && criticalTacticCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold bg-red-100 text-red-700 rounded-full">
                {criticalTacticCount > 9 ? '9+' : criticalTacticCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* FMEA top risks callout — shown when C&C tab active */}
      {activeTab === 'cc' && fmeaAll.length > 0 && (
        <div className="mx-6 mt-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <p className="text-xs font-semibold text-amber-800 mb-1">Top failure modes by RPN</p>
          <div className="flex flex-wrap gap-2">
            {fmeaAll
              .sort((a, b) => b.rpn - a.rpn)
              .slice(0, 4)
              .map((e) => (
                <span key={e.id} className="text-xs bg-amber-100 text-amber-900 rounded px-1.5 py-0.5">
                  {e.failure_mode} <strong>RPN {e.rpn}</strong>
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-4 flex justify-end">
            <MarkdownExportActions
              markdown={tabContent}
              markdownFilename={getTabFilename()}
              compact={true}
              copyButtonTitle="Copy section as Markdown"
            />
          </div>

          {tabContent.trim() ? (
            <MarkdownRenderer content={tabContent} />
          ) : (
            <p className="text-gray-400 italic">No content available for this section.</p>
          )}
        </div>
      </div>
    </div>
  );
}
