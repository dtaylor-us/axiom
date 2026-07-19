import { expect, it } from 'vitest';

import type { ReviewReport, ReviewSession } from '../api/lens';
import {
  buildLensReportMarkdown,
  buildLensStatusMarkdown,
  lensReportMarkdownFilename,
  lensStatusMarkdownFilename,
} from '../views/lens/lensMarkdown';

const session: ReviewSession = {
  id: 'session-1',
  title: 'Payments / Review',
  systemDescription: 'A multi-region payment platform.',
  status: 'READY_FOR_REVIEW',
  gapRound: 2,
  gapsResolved: false,
  createdAt: '2026-07-01T00:00:00Z',
  updatedAt: '2026-07-02T00:00:00Z',
};

it('builds a complete Lens status Markdown document and safe filename', () => {
  const markdown = buildLensStatusMarkdown({ session, evidence: [], questions: [], assessment: null });
  expect(markdown).toContain('# Lens Review Status: Payments / Review');
  expect(markdown).toContain('**Status:** READY_FOR_REVIEW');
  expect(markdown).toContain('A multi-region payment platform.');
  expect(markdown).toContain('_No evidence submitted._');
  expect(lensStatusMarkdownFilename(session)).toBe('lens-payments-review-status.md');
});

it('builds report Markdown with findings, risks, recommendations, and analysis', () => {
  const report = {
    id: 'report-1', sessionId: session.id, executiveSummary: 'Architecture summary.',
    overallRating: 'NEEDS_REWORK', generatedAt: '2026-07-03T00:00:00Z',
    azureWafScorecard: { reliability: { score: 3 } }, atamAnalysis: {}, seiAnalysis: {}, structuralAnalysis: {},
    insufficientInfoGaps: {},
    findings: [{ findingType: 'GAP', category: 'SECURITY', title: 'Missing controls', description: 'Controls are absent.', evidence: null, frameworkReference: null, severity: 'HIGH' }],
    risks: [{ title: 'Data exposure', description: 'Sensitive data may leak.', severity: 'HIGH', likelihood: 'MEDIUM', affectedArea: 'Security', mitigationStrategy: 'Encrypt data.', frameworkReference: null }],
    recommendationRoadmap: [{ title: 'Add encryption', description: 'Encrypt stored data.', priority: 'P1', effort: 'DAYS', addresses_risk: 'Data exposure' }],
  } satisfies ReviewReport;
  const markdown = buildLensReportMarkdown(report);
  expect(markdown).toContain('# Lens Architecture Review Report');
  expect(markdown).toContain('### Missing controls');
  expect(markdown).toContain('### Data exposure');
  expect(markdown).toContain('### Add encryption');
  expect(markdown).toContain('"reliability"');
  expect(lensReportMarkdownFilename(report)).toBe('lens-review-report-session-1.md');
});
