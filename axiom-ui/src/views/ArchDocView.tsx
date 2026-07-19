import { useState } from 'react';
import { useArchDoc } from '../hooks/useArchDoc';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { StructuredExportBar, MarkdownExportActions, downloadMarkdown } from '../components/StructuredData';

type Tab = 'overview' | 'module' | 'cc' | 'allocation' | 'risk';

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'module', label: 'Module View' },
  { key: 'cc', label: 'Component & Connector' },
  { key: 'allocation', label: 'Allocation View' },
  { key: 'risk', label: 'Risk & Decisions' },
];

export function ArchDocView() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const {
    overviewMarkdown,
    moduleViewMarkdown,
    ccViewMarkdown,
    allocationViewMarkdown,
    riskMarkdown,
    fullPackageMarkdown,
    exportFilename,
    loading,
    error,
    hasData,
  } = useArchDoc();

  function getTabContent(): string {
    switch (activeTab) {
      case 'overview':
        return overviewMarkdown;
      case 'module':
        return moduleViewMarkdown;
      case 'cc':
        return ccViewMarkdown;
      case 'allocation':
        return allocationViewMarkdown;
      case 'risk':
        return riskMarkdown;
    }
  }

  function getTabFilename(): string {
    const baseName = exportFilename.replace('.md', '');
    switch (activeTab) {
      case 'overview':
        return `${baseName}-overview.md`;
      case 'module':
        return `${baseName}-module-view.md`;
      case 'cc':
        return `${baseName}-cc-view.md`;
      case 'allocation':
        return `${baseName}-allocation-view.md`;
      case 'risk':
        return `${baseName}-risk.md`;
    }
  }

  function handleExportFullPackage() {
    downloadMarkdown(exportFilename, fullPackageMarkdown);
  }

  // Loading state
  if (loading) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-500" data-testid="arch-doc-loading">
        <svg
          className="w-4 h-4 animate-spin text-accent shrink-0"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
          <path d="M8 2a6 6 0 0 1 6 6" />
        </svg>
        Loading documentation…
      </div>
    );
  }

  // Error state
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

  // Empty state
  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6 py-12">
        <svg
          className="w-12 h-12 text-gray-300"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h2 className="text-lg font-semibold text-gray-700">No architecture data yet</h2>
        <p className="text-sm text-gray-500 max-w-sm">
          Complete an architecture analysis in Chat to generate the documentation package.
        </p>
      </div>
    );
  }

  const tabContent = getTabContent();
  const tabFilename = getTabFilename();

  return (
    <div className="flex flex-col h-full" data-testid="arch-doc-view">
      {/* Top bar */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 sticky top-0 flex items-center justify-between gap-4">
        <h1 className="text-lg font-semibold text-gray-900">Arch Docs</h1>
        <button
          onClick={handleExportFullPackage}
          disabled={!hasData}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" />
          </svg>
          Export Arch Docs
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 mb-4 px-6 pt-3 bg-white">
        {TABS.map(({ key, label }) => (
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

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-4xl mx-auto">
          {/* Per-tab export button */}
          <div className="mb-4 flex justify-end">
            <MarkdownExportActions
              markdown={tabContent}
              markdownFilename={tabFilename}
              compact={true}
              copyButtonTitle="Copy tab as Markdown"
            />
          </div>

          {/* Content */}
          {tabContent.trim() ? (
            <MarkdownRenderer content={tabContent} />
          ) : (
            <p className="text-gray-400 italic">No content available for this section</p>
          )}
        </div>
      </div>
    </div>
  );
}
