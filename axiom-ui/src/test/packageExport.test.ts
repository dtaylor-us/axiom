import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ArchInputPackage } from '../api/specweaver';
import {
  buildPackageMarkdown,
  buildPackageText,
  downloadPackageExport,
} from '../views/specweaver/packageExport';

function buildSamplePackage(overrides: Partial<ArchInputPackage> = {}): ArchInputPackage {
  return {
    packageId: 'pkg-1',
    sessionId: 'sw-1',
    createdAt: '2026-06-01T00:00:00Z',
    readinessScore: 0.82,
    readinessLabel: 'Good',
    systemDescription: 'Claims intake service.',
    totalRequirements: 1,
    highConfidenceCount: 1,
    inferredCount: 0,
    duplicateCount: 0,
    gapCount: 1,
    conflictCount: 1,
    requirements: [
      {
        requirementId: 'REQ-1',
        category: 'non_functional',
        statement: 'System must retain records.\nFor seven years.',
        type: 'QUALITY_ATTRIBUTE',
        confidence: 'HIGH',
        isInferred: true,
        inferenceReasoning: 'Required by policy.',
        ambiguities: ['What is the archival format?'],
        sourceDocumentIds: ['doc-1'],
        sourceExcerpts: ['Records retained >= 7 years.'],
      },
    ],
    gaps: [
      {
        gapId: 'gap-1',
        area: 'Observability',
        severity: 'high',
        explanation: 'Telemetry requirements are missing.',
        clarificationQuestion: 'Which SLOs must be tracked?',
        affectedCategories: ['non_functional'],
      },
    ],
    conflicts: [
      {
        conflictId: 'conf-1',
        requirementIds: ['REQ-1', 'REQ-2'],
        description: 'Two retention periods are specified.',
        interpretations: ['7 years', '10 years'],
        clarificationQuestion: 'Which retention period is authoritative?',
      },
    ],
    sourceDocuments: [
      {
        id: 'doc-1',
        filename: 'requirements.md',
        sourceLabel: 'Workshop notes',
        documentType: 'MARKDOWN',
      },
    ],
    ...overrides,
  };
}

describe('packageExport', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('buildPackageMarkdown_formats_sections_and_escapes_content', () => {
    const content = buildPackageMarkdown(buildSamplePackage());

    expect(content).toContain('# SpecWeaver Package Export');
    expect(content).toContain('### Non Functional');
    expect(content).toContain('System must retain records\\. For seven years\\.');
    expect(content).toContain('Confidence: HIGH (inferred)');
    expect(content).toContain('## Gaps');
    expect(content).toContain('## Conflicts');
    expect(content).toContain('## Source Documents');
  });

  it('buildPackageText_formats_sections_with_fallbacks_for_empty_lists', () => {
    const content = buildPackageText(
      buildSamplePackage({
        requirements: [],
        gaps: [],
        conflicts: [],
        sourceDocuments: [],
        systemDescription: '',
      }),
    );

    expect(content).toContain('SpecWeaver Package Export');
    expect(content).toContain('No system description provided.');
    expect(content).toContain('No requirements found.');
    expect(content).toContain('No gaps identified.');
    expect(content).toContain('No conflicts identified.');
    expect(content).toContain('No source documents listed.');
  });

  it('downloadPackageExport_creates_clicks_and_cleans_up_anchor_for_markdown', () => {
    const createObjectUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:export-md');
    const revokeObjectUrlSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);

    const clickSpy = vi.fn();
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    const removeSpy = vi.spyOn(document.body, 'removeChild');
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = document.createElementNS('http://www.w3.org/1999/xhtml', tagName);
      if (tagName.toLowerCase() === 'a') {
        Object.defineProperty(element, 'click', {
          value: clickSpy,
          configurable: true,
        });
      }
      return element as HTMLElement;
    });

    downloadPackageExport(buildSamplePackage(), 'markdown');

    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(appendSpy).toHaveBeenCalledTimes(1);
    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith('blob:export-md');
  });

  it('downloadPackageExport_uses_text_extension_for_plain_text_export', () => {
    const createObjectUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:export-txt');
    const revokeObjectUrlSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);

    const clickSpy = vi.fn();
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = document.createElementNS('http://www.w3.org/1999/xhtml', tagName);
      if (tagName.toLowerCase() === 'a') {
        Object.defineProperty(element, 'click', {
          value: clickSpy,
          configurable: true,
        });
      }
      return element as HTMLElement;
    });

    downloadPackageExport(buildSamplePackage(), 'text');

    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith('blob:export-txt');

    const anchor = createElementSpy.mock.results
      .map((result) => result.value)
      .find((value) => value instanceof HTMLAnchorElement) as HTMLAnchorElement;
    expect(anchor.download).toMatch(/\.txt$/);
  });
});
