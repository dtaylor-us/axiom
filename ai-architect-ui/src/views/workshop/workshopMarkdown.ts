import type { QualityAttribute, WorkshopScenario } from '../../types/workshop';

function block(text: string): string {
  const t = text.trim();
  if (!t) return '_—_';
  return t.split('\n').join('\n\n');
}

/** Human-readable Markdown for elicited quality attributes (workshop export). */
export function buildQualityAttributesMarkdown(
  attributes: QualityAttribute[],
  opts?: { systemName?: string; sessionId?: string },
): string {
  const lines: string[] = ['# Quality attributes', ''];

  if (opts?.systemName) {
    lines.push(`**System:** ${opts.systemName}`, '');
  }
  if (opts?.sessionId) {
    lines.push(`**Session:** \`${opts.sessionId}\``, '');
  }

  for (const a of attributes) {
    lines.push(`## ${a.name}`, '', `- **Id:** \`${a.attributeId}\``);
    lines.push(`- **Category:** ${a.category}`);
    lines.push(`- **Importance:** ${a.importance}`);
    lines.push(`- **Confidence:** ${a.confidence}`);
    lines.push(`- **Scenario completeness:** ${a.scenarioCompleteness}`);
    if (a.firstGenerationPass != null || a.lastGenerationPass != null) {
      lines.push(
        `- **Generation passes:** ${a.firstGenerationPass ?? '—'} → ${a.lastGenerationPass ?? '—'}`,
      );
    }
    if (a.lastUpdateSummary) {
      lines.push(`- **Last update:** ${a.lastUpdateSummary}`);
    }
    if (a.lastUpdatedTurn != null) {
      lines.push(`- **Last updated turn:** ${a.lastUpdatedTurn}`);
    }
    lines.push('', '### Description', '', block(a.description), '');

    const open = a.openQuestions?.filter((q) => q.trim()) ?? [];
    if (open.length > 0) {
      lines.push('### Open questions', '');
      for (const q of open) {
        lines.push(`- ${q}`);
      }
      lines.push('');
    }

    const quotes = a.evidenceQuotes?.filter((q) => q.trim()) ?? [];
    if (quotes.length > 0) {
      lines.push('### Evidence quotes', '');
      for (const q of quotes) {
        lines.push(`> ${q.split('\n').join('\n> ')}`, '');
      }
    }

    const resolved = a.resolvedAnswers?.filter((r) => r.question?.trim()) ?? [];
    if (resolved.length > 0) {
      lines.push('### Resolved answers', '');
      for (const r of resolved) {
        lines.push(`#### Q (turn ${r.resolvedInTurn})`, '', r.question, '', '**Answer:**', '', block(r.answer), '');
        if (r.evidenceQuote?.trim()) {
          lines.push(`_Evidence:_ ${r.evidenceQuote}`, '');
        }
      }
    }

    lines.push('---', '');
  }

  return lines.join('\n').trimEnd() + '\n';
}

/** Human-readable Markdown for workshop scenarios (export). */
export function buildScenariosMarkdown(
  scenarios: WorkshopScenario[],
  opts?: { systemName?: string; sessionId?: string },
): string {
  const lines: string[] = ['# Workshop scenarios', ''];

  if (opts?.systemName) {
    lines.push(`**System:** ${opts.systemName}`, '');
  }
  if (opts?.sessionId) {
    lines.push(`**Session:** \`${opts.sessionId}\``, '');
  }

  for (const s of scenarios) {
    const title = s.title?.trim() || 'Untitled scenario';
    lines.push(`## ${title}`, '', `- **Id:** \`${s.scenarioId}\``);
    lines.push(`- **Completeness:** ${s.completeness.replace(/_/g, ' ')}`);
    lines.push(`- **Derived in turn:** ${s.derivedInTurn}`);
    if (s.stimulus?.trim()) lines.push(`- **Stimulus:** ${s.stimulus}`);
    if (s.source?.trim()) lines.push(`- **Source:** ${s.source}`);
    if (s.environment?.trim()) lines.push(`- **Environment:** ${s.environment}`);
    if (s.artifact?.trim()) lines.push(`- **Artifact:** ${s.artifact}`);
    if (s.response?.trim()) lines.push(`- **Response:** ${s.response}`);
    if (s.responseMeasure?.trim()) {
      lines.push(`- **Response measure:** ${s.responseMeasure}`);
    }
    if (s.exercisesAttributes?.length) {
      lines.push(`- **Exercises attributes:** ${s.exercisesAttributes.join(', ')}`);
    }
    if (s.evidenceQuote?.trim()) {
      lines.push('', '### Evidence', '', `> ${s.evidenceQuote.split('\n').join('\n> ')}`, '');
    }
    lines.push('---', '');
  }

  return lines.join('\n').trimEnd() + '\n';
}
