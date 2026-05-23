import { useArchitecture } from '../hooks/useArchitecture';
import { useDiagrams } from '../hooks/useDiagrams';
import { useTactics } from '../hooks/useTactics';
import { useBuyVsBuild } from '../hooks/useBuyVsBuild';
import { useStore } from '../store/useStore';
import { MermaidDiagram } from '../components/MermaidDiagram';
import { CopyButton } from '../components/CopyButton';
import { StructuredDataCard, StructuredExportBar } from '../components/StructuredData';
import type { ArchitectureOutput, DiagramCollectionDto, BuyVsBuildDecision } from '../types/api';

/* ── Export helpers ─────────────────────────────── */

function buildArchitectureMarkdown(
  arch: ArchitectureOutput,
  diagrams: DiagramCollectionDto | null,
): string {
  const lines: string[] = [];

  lines.push('# Architecture Report', '');
  lines.push('## Architecture Style', '', arch.style, '');

  lines.push('## Components', '');
  for (const c of arch.components) {
    lines.push(`### ${c.name}`, c.responsibility, `*Technology: ${c.technology}*`, '');
  }

  lines.push('## Interactions', '');
  lines.push('| From | To | Protocol | Purpose |');
  lines.push('|------|-----|---------|---------|');
  for (const i of arch.interactions) {
    lines.push(`| ${i.from} | ${i.to} | \`${i.protocol}\` | ${i.purpose} |`);
  }
  lines.push('');

  const diags = diagrams?.diagrams ?? [];
  if (diags.length > 0) {
    for (const d of diags) {
      lines.push(`## ${d.title}`);
      if (d.description) lines.push(d.description, '');
      lines.push('```mermaid', d.mermaidSource, '```', '');
      if (d.characteristicAddressed) lines.push(`*Addresses: ${d.characteristicAddressed}*`, '');
    }
  } else {
    lines.push('## Component Diagram', '', '```mermaid', arch.componentDiagram, '```', '');
    lines.push('## Sequence Diagram', '', '```mermaid', arch.sequenceDiagram, '```', '');
  }

  return lines.join('\n');
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

/* ── Component ───────────────────────────────────── */

export function ArchitectureView() {
  const { architecture, loading, error } = useArchitecture();
  const { collection: diagramCollection } = useDiagrams();
  const {
    tactics: criticalTactics,
    loading: tacticsLoading,
    error: tacticsError,
  } = useTactics({ priority: 'critical', newOnly: true });
  const overrideWarning = useStore((s) => s.overrideWarning);
  const {
    summary: buyVsBuild,
    loading: buyVsBuildLoading,
    error: buyVsBuildError,
  } = useBuyVsBuild();

  if (loading) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-500" data-testid="architecture-loading">
        <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
          <path d="M8 2a6 6 0 0 1 6 6" />
        </svg>
        Loading architecture…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6" data-testid="architecture-error">
        <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          <p className="text-sm font-semibold text-red-800">Unable to load architecture</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!architecture) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-400" data-testid="architecture-empty">
        <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
        </svg>
        No architecture data yet. Run the pipeline first.
      </div>
    );
  }

  const markdown = buildArchitectureMarkdown(architecture, diagramCollection ?? null);
  const structured = {
    kind: 'architecture_report',
    conversationId: architecture.conversationId,
    style: architecture.style,
    components: architecture.components,
    interactions: architecture.interactions,
    diagrams: diagramCollection?.diagrams ?? null,
  };

  return (
    <div className="p-6 space-y-8" data-testid="architecture-view">

      {overrideWarning && overrideWarning.trim().length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3" data-testid="override-warning-banner">
          <svg className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 2L1 14h14L8 2z" /><path d="M8 7v3M8 11.5v.5" />
          </svg>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-amber-900">Architecture override warning</p>
            <p className="text-sm text-amber-800 mt-1">{overrideWarning}</p>
            <p className="text-xs text-amber-700 mt-1">
              This warning was generated because the requested architecture style conflicts with the inferred system
              characteristics. Review the Governance tab for details.
            </p>
          </div>
        </div>
      )}

      <StructuredExportBar
        title="Architecture Report"
        json={structured}
        filename="architecture-report.json"
        extraRight={
          <>
            <CopyButton text={markdown} label="Copy MD" title="Copy full report as Markdown" />
            <button
              type="button"
              onClick={() => downloadMarkdown('architecture-report.md', markdown)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
              title="Download Markdown file"
            >
              <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 2v8M5 7l3 3 3-3M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" />
              </svg>
              Download .md
            </button>
          </>
        }
      />

      {/* Critical tactics sidebar — top 5 unaddressed critical tactics */}
      {(tacticsLoading || tacticsError || criticalTactics.length > 0) && (
        <section data-testid="critical-tactics-sidebar">
          <h2 className="text-sm font-semibold text-red-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 2L1 14h14L8 2z" /><path d="M8 7v3M8 11.5v.5" />
            </svg>
            Critical unaddressed tactics
          </h2>
          <div className="bg-red-50 border border-red-100 rounded-xl p-3 space-y-2">
            {tacticsLoading && (
              <div className="text-sm text-gray-600 flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
                  <path d="M8 2a6 6 0 0 1 6 6" />
                </svg>
                Loading tactics…
              </div>
            )}

            {tacticsError && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                <p className="text-xs font-semibold text-amber-900">Unable to load tactics</p>
                <p className="text-sm text-amber-800 mt-1">{tacticsError}</p>
              </div>
            )}

            {!tacticsLoading && !tacticsError && criticalTactics.length === 0 && (
              <p className="text-sm text-gray-600 italic">No critical tactics available yet.</p>
            )}

            {criticalTactics.slice(0, 5).map((t) => (
              <div key={t.id} className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5 text-xs shrink-0">▸</span>
                <div>
                  <p className="text-sm font-medium text-gray-800">{t.tacticName}</p>
                  <p className="text-xs text-gray-500">{t.characteristicName} — {t.effort} effort</p>
                </div>
              </div>
            ))}

            <p className="text-xs text-red-500 italic pt-1">
              See Governance → Tactics for full details.
            </p>
          </div>
        </section>
      )}

      {/* Summary */}
      <StructuredDataCard
        title="Architecture Style"
        subtitle="Primary chosen architecture style"
        fields={[
          { label: 'Conversation ID', value: architecture.conversationId, fieldKey: 'conversationId' },
          { label: 'Style', value: architecture.style, fieldKey: 'style' },
        ]}
        copyValue={JSON.stringify({ conversationId: architecture.conversationId, style: architecture.style }, null, 2)}
        data-testid="architecture-style-card"
      />

      {/* Components */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-gray-800">Components</h2>
          <CopyButton
            text={architecture.components.map((c) => `${c.name}: ${c.responsibility} (${c.technology})`).join('\n')}
            label="Copy all"
            title="Copy all components as text"
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-structured-section="components">
          {architecture.components.map((c) => (
            <div
              key={c.name}
              className="group relative border border-gray-200 rounded-lg p-3 bg-white hover:border-gray-300 hover:shadow-sm transition-all"
              data-component-name={c.name}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-sm">{c.name}</h3>
                <CopyButton
                  text={`${c.name}: ${c.responsibility} (${c.technology})`}
                  className="opacity-0 group-hover:opacity-100"
                  title={`Copy ${c.name}`}
                />
              </div>
              <p className="text-xs text-gray-600 mt-1">{c.responsibility}</p>
              <span className="inline-block mt-1.5 text-xs bg-emerald-50 text-emerald-700 rounded px-2 py-0.5">
                {c.technology}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Buy vs Build */}
      <section data-testid="buy-vs-build-section">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Component sourcing decisions</h2>
            <p className="text-sm text-gray-500">Build vs buy vs adopt recommendations per component.</p>
          </div>
        </div>

        {buyVsBuildLoading && (
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <svg className="w-4 h-4 animate-spin text-accent shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
              <path d="M8 2a6 6 0 0 1 6 6" />
            </svg>
            Loading sourcing decisions…
          </div>
        )}

        {buyVsBuildError && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <p className="text-sm font-semibold text-amber-900">Unable to load sourcing decisions</p>
            <p className="text-sm text-amber-800 mt-1">{buyVsBuildError}</p>
            <p className="text-xs text-amber-700 mt-1">
              This usually means the endpoint `GET /api/v1/sessions/{'{id}'}/build-analysis` returned an error.
            </p>
          </div>
        )}

        {!buyVsBuildLoading && !buyVsBuildError && (!buyVsBuild || buyVsBuild.totalDecisions === 0) && (
          <p className="text-sm text-gray-400 italic">
            No sourcing decisions available yet.
          </p>
        )}

        {buyVsBuild && buyVsBuild.totalDecisions > 0 && (
          <>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="text-xs font-semibold rounded-full bg-blue-50 text-blue-700 px-3 py-1">Build {buyVsBuild.buildCount}</span>
              <span className="text-xs font-semibold rounded-full bg-purple-50 text-purple-700 px-3 py-1">Buy {buyVsBuild.buyCount}</span>
              <span className="text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 px-3 py-1">Adopt {buyVsBuild.adoptCount}</span>
              {buyVsBuild.conflictCount > 0 && (
                <span className="text-xs font-semibold rounded-full bg-amber-50 text-amber-800 px-3 py-1">
                  {buyVsBuild.conflictCount} preference conflicts
                </span>
              )}
            </div>

            <div className="space-y-3">
              {buyVsBuild.decisions.map((d: BuyVsBuildDecision) => (
                <details key={d.componentName} className="border border-gray-200 rounded-lg p-3 bg-white">
                  <summary className="cursor-pointer list-none flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-gray-900 truncate">{d.componentName}</p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">
                        {d.recommendedSolution ? d.recommendedSolution : 'Custom build'}
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
                        Lock-in: {d.vendorLockInRisk}
                      </span>
                      {d.conflictsWithUserPreference && (
                        <span className="text-[11px] font-semibold rounded px-2 py-0.5 bg-amber-50 text-amber-800">
                          Preference conflict
                        </span>
                      )}
                    </div>
                  </summary>

                  <div className="mt-3 text-sm text-gray-700 space-y-2">
                    <p><span className="font-semibold">Estimated cost:</span> {d.estimatedBuildCost}</p>
                    <p className="text-sm text-gray-700">{d.rationale}</p>
                    {d.conflictsWithUserPreference && d.conflictExplanation && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-amber-900">
                        <p className="text-xs font-semibold">Preference conflict</p>
                        <p className="text-sm mt-1">{d.conflictExplanation}</p>
                      </div>
                    )}
                  </div>
                </details>
              ))}
            </div>

            {buyVsBuild.summaryText && (
              <p className="text-sm text-gray-600 mt-4">{buyVsBuild.summaryText}</p>
            )}
          </>
        )}
      </section>

      {/* Interactions */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-gray-800">Interactions</h2>
          <CopyButton
            text={['| From | To | Protocol | Purpose |', '|------|-----|---------|---------|',
              ...architecture.interactions.map((i) => `| ${i.from} | ${i.to} | ${i.protocol} | ${i.purpose} |`)
            ].join('\n')}
            label="Copy table"
            title="Copy as Markdown table"
          />
        </div>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="text-sm w-full border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">From</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">To</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">Protocol</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">Purpose</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100" data-structured-section="interactions">
              {architecture.interactions.map((i, idx) => (
                <tr
                  key={idx}
                  className="hover:bg-gray-50 transition-colors"
                  data-interaction-index={idx}
                  data-from={i.from}
                  data-to={i.to}
                  data-protocol={i.protocol}
                >
                  <td className="px-3 py-2 font-medium text-gray-800">{i.from}</td>
                  <td className="px-3 py-2 text-gray-700">{i.to}</td>
                  <td className="px-3 py-2"><code className="text-xs bg-gray-100 rounded px-1.5 py-0.5 font-mono">{i.protocol}</code></td>
                  <td className="px-3 py-2 text-gray-600">{i.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Diagrams */}
      {diagramCollection && diagramCollection.diagrams.length > 0 ? (
        diagramCollection.diagrams.map((diagram) => (
          <section key={diagram.diagramId}>
            <div className="flex items-start justify-between gap-2 mb-1">
              <h2 className="text-lg font-bold text-gray-800">{diagram.title}</h2>
              <CopyButton
                text={diagram.mermaidSource}
                label="Copy source"
                title="Copy Mermaid source"
                className="shrink-0 mt-0.5"
              />
            </div>
            {diagram.description && (
              <p className="text-xs text-gray-500 mb-2">{diagram.description}</p>
            )}
            <MermaidDiagram
              chart={diagram.mermaidSource}
              id={`diagram-${diagram.diagramId}`}
            />
            {diagram.characteristicAddressed && (
              <p className="text-xs text-gray-400 mt-1 italic">
                Addresses: {diagram.characteristicAddressed}
              </p>
            )}
          </section>
        ))
      ) : (
        <>
          <section>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-bold text-gray-800">Component Diagram</h2>
              <CopyButton text={architecture.componentDiagram} label="Copy source" title="Copy Mermaid source" />
            </div>
            <MermaidDiagram
              chart={architecture.componentDiagram}
              id="component-diagram"
            />
          </section>

          <section>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-bold text-gray-800">Sequence Diagram</h2>
              <CopyButton text={architecture.sequenceDiagram} label="Copy source" title="Copy Mermaid source" />
            </div>
            <MermaidDiagram
              chart={architecture.sequenceDiagram}
              id="sequence-diagram"
            />
          </section>
        </>
      )}
    </div>
  );
}
