import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AttributePanel } from '../views/workshop/components/AttributePanel';
import type { QualityAttribute } from '../types/workshop';

// Mock the export component to keep tests focused on AttributePanel behaviour.
vi.mock('../components/StructuredData', () => ({
  MarkdownExportActions: () => <div data-testid="mock-export-actions" />,
}));

function makeAttribute(overrides: Partial<QualityAttribute> = {}): QualityAttribute {
  return {
    attributeId: 'qa-001',
    name: 'Performance',
    category: 'performance_efficiency',
    description: 'Response time < 200ms.',
    importance: 'high',
    confidence: 'confirmed',
    scenarioCompleteness: 'complete',
    openQuestions: [],
    evidenceQuotes: [],
    resolvedAnswers: [],
    questionsResolvedCount: 0,
    firstGenerationPass: null,
    lastGenerationPass: null,
    lastUpdateSummary: undefined,
    lastUpdatedTurn: undefined,
    ...overrides,
  };
}

const BASE_PROPS = {
  attributes: [],
  sessionId: null,
  systemName: 'Order Service',
  hasSufficientAttributes: false,
  onSendToPipeline: vi.fn(),
  sendingToPipeline: false,
  generationCount: 0,
  sessionAttributesStale: false,
};

describe('AttributePanel', () => {
  it('rendersAttributePanelContainer', () => {
    render(<AttributePanel {...BASE_PROPS} />);
    expect(screen.getByTestId('attribute-panel')).toBeInTheDocument();
  });

  it('showsNotYetGeneratedTitleWhenGenerationCountIsZero', () => {
    render(<AttributePanel {...BASE_PROPS} generationCount={0} />);
    expect(screen.getByText(/Not yet generated/)).toBeInTheDocument();
  });

  it('showsPassNumberInTitleAfterFirstGeneration', () => {
    render(<AttributePanel {...BASE_PROPS} generationCount={2} />);
    expect(screen.getByText(/Pass 2/)).toBeInTheDocument();
  });

  it('showsEmptyStateMessageWhenNoAttributes', () => {
    render(<AttributePanel {...BASE_PROPS} attributes={[]} />);
    expect(screen.getByText(/Attributes will appear/)).toBeInTheDocument();
  });

  it('rendersAttributeCardsWhenAttributesPresent', () => {
    const attrs = [makeAttribute({ attributeId: 'qa-001', name: 'Performance' })];
    render(<AttributePanel {...BASE_PROPS} attributes={attrs} generationCount={1} />);
    // AttributeCard renders the attribute name
    expect(screen.getByText(/Performance/)).toBeInTheDocument();
  });

  it('showsCountOfElicitedAttributes', () => {
    const attrs = [makeAttribute(), makeAttribute({ attributeId: 'qa-002', name: 'Security' })];
    render(<AttributePanel {...BASE_PROPS} attributes={attrs} />);
    expect(screen.getByText('2 elicited')).toBeInTheDocument();
  });

  it('showsConfidenceCountsAfterFirstGeneration', () => {
    const attrs = [
      makeAttribute({ confidence: 'confirmed' }),
      makeAttribute({ attributeId: 'qa-002', confidence: 'inferred' }),
      makeAttribute({ attributeId: 'qa-003', confidence: 'tentative' }),
    ];
    render(<AttributePanel {...BASE_PROPS} attributes={attrs} generationCount={1} />);
    expect(screen.getByText(/1 confirmed/)).toBeInTheDocument();
  });

  it('showsResolvedAndOpenQuestionCounts', () => {
    const attrs = [
      makeAttribute({ questionsResolvedCount: 3, openQuestions: ['Open question?'] }),
    ];
    render(<AttributePanel {...BASE_PROPS} attributes={attrs} />);
    expect(screen.getByText(/3 questions resolved/)).toBeInTheDocument();
    expect(screen.getByText(/1 still open/)).toBeInTheDocument();
  });

  it('rendersExportActionsWhenAttributesPresentAndSessionIdSet', () => {
    const attrs = [makeAttribute()];
    render(
      <AttributePanel
        {...BASE_PROPS}
        attributes={attrs}
        sessionId="ws-123"
        generationCount={1}
      />,
    );
    expect(screen.getByTestId('attribute-markdown-export')).toBeInTheDocument();
  });

  it('doesNotRenderExportActionsWhenSessionIdIsNull', () => {
    const attrs = [makeAttribute()];
    render(
      <AttributePanel {...BASE_PROPS} attributes={attrs} sessionId={null} generationCount={1} />,
    );
    expect(screen.queryByTestId('attribute-markdown-export')).not.toBeInTheDocument();
  });
});
