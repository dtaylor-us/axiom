import type {
  ArchitectureEvidence,
  GapAssessmentResult,
  GapQuestion,
  ReviewReport,
  ReviewSession,
} from '../../api/lens';

function value(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'N/A';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function safeFilenamePart(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'review';
}

function jsonSection(title: string, content: Record<string, unknown>): string[] {
  return [`## ${title}`, '', '```json', JSON.stringify(content, null, 2), '```'];
}

export function lensStatusMarkdownFilename(session: ReviewSession): string {
  return `lens-${safeFilenamePart(session.title)}-status.md`;
}

export function lensReportMarkdownFilename(report: ReviewReport): string {
  return `lens-review-report-${safeFilenamePart(report.sessionId)}.md`;
}

export function buildLensStatusMarkdown({
  session,
  evidence,
  questions,
  assessment,
}: {
  session: ReviewSession;
  evidence: ArchitectureEvidence[];
  questions: GapQuestion[];
  assessment: GapAssessmentResult | null;
}): string {
  const unresolved = questions.filter((question) => question.skipped || !question.answered || !question.answer).length;
  const lines = [
    `# Lens Review Status: ${session.title || 'Untitled review'}`,
    '',
    `- **Session ID:** ${value(session.id)}`,
    `- **Status:** ${session.status}`,
    `- **Gap round:** ${session.gapRound}`,
    `- **Gaps resolved:** ${session.gapsResolved ? 'Yes' : 'No'}`,
    `- **Evidence items:** ${evidence.length}`,
    `- **Gap questions:** ${questions.length}`,
    `- **Unresolved gaps:** ${unresolved}`,
    `- **Last updated:** ${value(session.updatedAt)}`,
    '',
    '## System Description',
    '',
    value(session.systemDescription),
    '',
    '## Evidence',
    '',
  ];

  if (evidence.length === 0) lines.push('_No evidence submitted._');
  evidence.forEach((item, index) => {
    lines.push(
      `### ${index + 1}. ${item.sourceLabel || 'Unlabeled source'}`,
      '',
      `- **Type:** ${item.evidenceType}`,
      `- **Submitted:** ${value(item.submittedAt)}`,
      '',
      item.content,
      '',
    );
  });

  lines.push('## Gap Questions', '');
  if (questions.length === 0) lines.push('_No gap questions generated._');
  questions.forEach((question, index) => {
    lines.push(
      `### ${index + 1}. ${question.category}`,
      '',
      question.question,
      '',
      `- **State:** ${question.skipped ? 'Skipped' : question.answered ? 'Answered' : 'Unanswered'}`,
      `- **Answer:** ${value(question.answer)}`,
      `- **Rationale:** ${value(question.rationale)}`,
      '',
    );
  });

  if (assessment) {
    lines.push(
      '## Latest Gap Assessment',
      '',
      assessment.summary,
      '',
      `- **Resolved:** ${assessment.resolved ? 'Yes' : 'No'}`,
      `- **Can proceed:** ${assessment.canProceed ? 'Yes' : 'No'}`,
      `- **Remaining:** ${assessment.remainingCount}`,
    );
  }

  return `${lines.join('\n').trim()}\n`;
}

export function buildLensReportMarkdown(report: ReviewReport): string {
  const recommendations = Array.isArray(report.recommendationRoadmap)
    ? report.recommendationRoadmap as Record<string, unknown>[]
    : [];
  const lines = [
    '# Lens Architecture Review Report',
    '',
    `- **Session ID:** ${report.sessionId}`,
    `- **Overall rating:** ${report.overallRating}`,
    `- **Generated:** ${value(report.generatedAt)}`,
    '',
    '## Executive Summary',
    '',
    report.executiveSummary,
    '',
    ...jsonSection('Azure Well-Architected Framework', report.azureWafScorecard),
    '',
    ...jsonSection('ATAM Analysis', report.atamAnalysis),
    '',
    ...jsonSection('SEI Analysis', report.seiAnalysis),
    '',
    ...jsonSection('Structural Analysis', report.structuralAnalysis),
    '',
    '## Findings',
    '',
  ];

  if (report.findings.length === 0) lines.push('_No findings._');
  report.findings.forEach((finding) => lines.push(
    `### ${finding.title}`,
    '',
    `- **Severity:** ${finding.severity}`,
    `- **Category:** ${value(finding.category)}`,
    `- **Framework reference:** ${value(finding.frameworkReference)}`,
    `- **Evidence:** ${value(finding.evidence)}`,
    '',
    finding.description,
    '',
  ));

  lines.push('## Risks', '');
  if (report.risks.length === 0) lines.push('_No risks._');
  report.risks.forEach((risk) => lines.push(
    `### ${risk.title}`,
    '',
    `- **Severity:** ${risk.severity}`,
    `- **Likelihood:** ${risk.likelihood}`,
    `- **Affected area:** ${value(risk.affectedArea)}`,
    `- **Framework reference:** ${value(risk.frameworkReference)}`,
    `- **Mitigation:** ${value(risk.mitigationStrategy)}`,
    '',
    risk.description,
    '',
  ));

  lines.push('## Recommendation Roadmap', '');
  if (recommendations.length === 0) lines.push('_No recommendations._');
  recommendations.forEach((recommendation) => lines.push(
    `### ${value(recommendation.title)}`,
    '',
    `- **Priority:** ${value(recommendation.priority as string)}`,
    `- **Effort:** ${value(recommendation.effort as string)}`,
    `- **Addresses risk:** ${value(recommendation.addresses_risk as string)}`,
    '',
    value(recommendation.description as string),
    '',
  ));

  return `${lines.join('\n').trim()}\n`;
}
