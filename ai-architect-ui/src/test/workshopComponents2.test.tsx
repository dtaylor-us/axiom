import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgressTracker } from '../views/workshop/components/ProgressTracker';
import { ScenarioCard } from '../views/workshop/components/ScenarioCard';
import { GapIndicator } from '../views/workshop/components/GapIndicator';
import { ReadinessModal } from '../views/workshop/components/ReadinessModal';
import { AttributeCard } from '../views/workshop/components/AttributeCard';
import type { WorkshopScenario, QualityAttribute, OpenGap } from '../types/workshop';
import type { GenerationReadinessDto } from '../types/workshop';

// ─── ProgressTracker ──────────────────────────────────────────────────────────

describe('ProgressTracker', () => {
  it('rendersAllFivePhaseLabels', () => {
    render(
      <ProgressTracker
        currentPhase="CONTEXT_SETTING"
        turnNumber={1}
        hasSufficientAttributes={false}
      />,
    );
    expect(screen.getByText('Context')).toBeInTheDocument();
    expect(screen.getByText('Stakeholders')).toBeInTheDocument();
    expect(screen.getByText('Attributes')).toBeInTheDocument();
    expect(screen.getByText('Scenarios')).toBeInTheDocument();
    expect(screen.getByText('Consolidate')).toBeInTheDocument();
  });

  it('hasAccessibleProgressLandmark', () => {
    render(
      <ProgressTracker
        currentPhase="CONSOLIDATION"
        turnNumber={10}
        hasSufficientAttributes
      />,
    );
    expect(screen.getByLabelText('Workshop phase progress')).toBeInTheDocument();
  });

  it('normalisesPythonPhaseNamesToUiPhases', () => {
    // 'input_analysis' maps to 'CONTEXT_SETTING'; ProgressTracker renders without crashing
    render(
      <ProgressTracker
        currentPhase="input_analysis"
        turnNumber={2}
        hasSufficientAttributes={false}
      />,
    );
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
  });

  it('rendersWithUnknownPhaseWithoutCrashing', () => {
    render(
      <ProgressTracker
        currentPhase="UNKNOWN_PHASE"
        turnNumber={0}
        hasSufficientAttributes={false}
      />,
    );
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
  });
});

// ─── ScenarioCard ─────────────────────────────────────────────────────────────

function makeScenario(overrides: Partial<WorkshopScenario> = {}): WorkshopScenario {
  return {
    scenarioId: 'scn-001',
    title: 'Checkout under peak load',
    completeness: 'complete',
    derivedInTurn: 3,
    stimulus: 'User submits order',
    source: 'End customer',
    environment: 'Normal operation',
    artifact: 'Checkout service',
    response: 'Order confirmed',
    responseMeasure: '< 200ms at p95',
    exercisesAttributes: ['Performance'],
    evidenceQuote: '',
    ...overrides,
  };
}

describe('ScenarioCard', () => {
  it('rendersScenarioIdAndTitle', () => {
    render(<ScenarioCard scenario={makeScenario()} />);
    expect(screen.getByText('scn-001')).toBeInTheDocument();
    expect(screen.getByText('Checkout under peak load')).toBeInTheDocument();
  });

  it('rendersCompletenessLabel', () => {
    render(<ScenarioCard scenario={makeScenario({ completeness: 'complete' })} />);
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('rendersMissingMeasureLabelForNeedsMeasure', () => {
    render(<ScenarioCard scenario={makeScenario({ completeness: 'needs_measure', responseMeasure: '' })} />);
    // 'Missing response measure' appears in both the completeness badge and the measure field.
    expect(screen.getAllByText('Missing response measure').length).toBeGreaterThan(0);
  });

  it('rendersExercisesAttributesWhenPresent', () => {
    render(<ScenarioCard scenario={makeScenario({ exercisesAttributes: ['Performance', 'Security'] })} />);
    expect(screen.getByText(/Performance/)).toBeInTheDocument();
  });

  it('showsMeasureInputWhenScenarioNeedsMeasureAndHandlerProvided', () => {
    render(
      <ScenarioCard
        scenario={makeScenario({ completeness: 'needs_measure', responseMeasure: '' })}
        onSubmitMeasure={vi.fn()}
      />,
    );
    expect(screen.getByPlaceholderText(/measurable threshold/)).toBeInTheDocument();
  });

  it('callsOnSubmitMeasureWithScenarioIdAndValue', () => {
    const onSubmitMeasure = vi.fn();
    render(
      <ScenarioCard
        scenario={makeScenario({ completeness: 'needs_measure', responseMeasure: '' })}
        onSubmitMeasure={onSubmitMeasure}
      />,
    );
    const input = screen.getByPlaceholderText(/measurable threshold/);
    fireEvent.change(input, { target: { value: '< 300ms' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSubmitMeasure).toHaveBeenCalledWith('scn-001', '< 300ms');
  });

  it('doesNotShowMeasureInputWhenNoHandler', () => {
    render(
      <ScenarioCard scenario={makeScenario({ completeness: 'needs_measure', responseMeasure: '' })} />,
    );
    expect(screen.queryByPlaceholderText(/measurable threshold/)).not.toBeInTheDocument();
  });

  it('rendersUntitledWhenTitleIsEmpty', () => {
    render(<ScenarioCard scenario={makeScenario({ title: '' })} />);
    expect(screen.getByText('Untitled scenario')).toBeInTheDocument();
  });
});

// ─── GapIndicator ─────────────────────────────────────────────────────────────

const sampleGap: OpenGap = {
  gapId: 'gap-001',
  category: 'business_context',
  priority: 'high',
  description: 'What are the primary business constraints?',
  resolutionConfidence: 0,
};

describe('GapIndicator', () => {
  it('rendersProgressBar', () => {
    render(
      <GapIndicator
        totalGaps={10}
        filledGaps={3}
        gapCompletionPct={30}
        inProgressCount={0}
        openGaps={[]}
      />,
    );
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('3/10 filled')).toBeInTheDocument();
  });

  it('rendersCompletionPercentage', () => {
    render(
      <GapIndicator
        totalGaps={10}
        filledGaps={5}
        gapCompletionPct={50}
        inProgressCount={0}
        openGaps={[]}
      />,
    );
    expect(screen.getByText('50% complete')).toBeInTheDocument();
  });

  it('rendersInProgressCountWhenPresent', () => {
    render(
      <GapIndicator
        totalGaps={10}
        filledGaps={5}
        gapCompletionPct={50}
        inProgressCount={2}
        openGaps={[]}
      />,
    );
    expect(screen.getByText(/2 in progress/)).toBeInTheDocument();
  });

  it('rendersCategoryHeaderForOpenGaps', () => {
    render(
      <GapIndicator
        totalGaps={5}
        filledGaps={0}
        gapCompletionPct={0}
        inProgressCount={0}
        openGaps={[sampleGap]}
      />,
    );
    expect(screen.getByText('Business Context')).toBeInTheDocument();
  });

  it('togglesCategoryCollapsed', () => {
    render(
      <GapIndicator
        totalGaps={5}
        filledGaps={0}
        gapCompletionPct={0}
        inProgressCount={0}
        openGaps={[sampleGap]}
      />,
    );
    const button = screen.getByRole('button', { name: /Business Context/ });
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    // After collapse the question should no longer be visible
    expect(screen.queryByText('What are the primary business constraints?')).not.toBeInTheDocument();
    // Click again to expand
    fireEvent.click(button);
    expect(screen.getByText('What are the primary business constraints?')).toBeInTheDocument();
  });
});

// ─── ReadinessModal ───────────────────────────────────────────────────────────

const readinessData: GenerationReadinessDto = {
  overallReadiness: 'partial',
  confidenceNote: 'You have provided useful context.',
  attributePreview: [
    { name: 'Performance', confidence: 'confirmed', reason: 'Stated explicitly.' },
  ],
  highValueGaps: [
    { gapId: 'g1', description: 'Define SLA', impact: 'Better measurability' },
  ],
  missingDomains: ['Usability'],
  canProduceUsefulOutput: true,
};

describe('ReadinessModal', () => {
  it('rendersNothingWhenClosed', () => {
    const { container } = render(
      <ReadinessModal
        open={false}
        data={readinessData}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('rendersNothingWhenDataIsNull', () => {
    const { container } = render(
      <ReadinessModal
        open
        data={null}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('rendersModalWithReadinessBadgeWhenOpen', () => {
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Partial evidence')).toBeInTheDocument();
  });

  it('rendersAttributePreviewTable', () => {
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('confirmed')).toBeInTheDocument();
  });

  it('rendersHighValueGaps', () => {
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByText('Define SLA')).toBeInTheDocument();
    expect(screen.getByText(/Better measurability/)).toBeInTheDocument();
  });

  it('rendersMissingDomains', () => {
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByText(/Usability/)).toBeInTheDocument();
  });

  it('callsOnCloseWhenCloseButtonClicked', () => {
    const onClose = vi.fn();
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={onClose}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalled();
  });

  it('callsOnKeepGoingAndOnCloseWhenKeepGoingClicked', () => {
    const onClose = vi.fn();
    const onKeepGoing = vi.fn();
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={onClose}
        onKeepGoing={onKeepGoing}
        onGenerateAnyway={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText(/Keep going/));
    expect(onKeepGoing).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('callsOnGenerateAnywayAndOnCloseWhenGenerateClicked', () => {
    const onClose = vi.fn();
    const onGenerateAnyway = vi.fn();
    render(
      <ReadinessModal
        open
        data={readinessData}
        onClose={onClose}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={onGenerateAnyway}
      />,
    );
    fireEvent.click(screen.getByText(/Generate now anyway/));
    expect(onGenerateAnyway).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('rendersInsufficientBadgeLevel', () => {
    render(
      <ReadinessModal
        open
        data={{ ...readinessData, overallReadiness: 'insufficient' }}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByText('Limited evidence')).toBeInTheDocument();
  });

  it('rendersStrongBadgeLevel', () => {
    render(
      <ReadinessModal
        open
        data={{ ...readinessData, overallReadiness: 'strong' }}
        onClose={vi.fn()}
        onKeepGoing={vi.fn()}
        onGenerateAnyway={vi.fn()}
      />,
    );
    expect(screen.getByText('Strong evidence')).toBeInTheDocument();
  });
});

// ─── AttributeCard ────────────────────────────────────────────────────────────

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
    firstGenerationPass: null,
    lastGenerationPass: null,
    lastUpdateSummary: undefined,
    lastUpdatedTurn: undefined,
    ...overrides,
  };
}

describe('AttributeCard', () => {
  it('rendersAttributeIdAndName', () => {
    render(<AttributeCard attribute={makeAttribute()} />);
    expect(screen.getByText(/qa-001/)).toBeInTheDocument();
    expect(screen.getByText(/Performance/)).toBeInTheDocument();
  });

  it('rendersConfidenceBadge', () => {
    render(<AttributeCard attribute={makeAttribute({ confidence: 'inferred' })} />);
    expect(screen.getByText('inferred')).toBeInTheDocument();
  });

  it('rendersImportanceLabel', () => {
    render(<AttributeCard attribute={makeAttribute({ importance: 'critical' })} />);
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('rendersOpenQuestionsWhenPresent', () => {
    render(
      <AttributeCard
        attribute={makeAttribute({ openQuestions: ['What is the SLA?'] })}
      />,
    );
    expect(screen.getByText(/What is the SLA\?/)).toBeInTheDocument();
  });

  it('doesNotRenderOpenQuestionsSectionWhenEmpty', () => {
    render(<AttributeCard attribute={makeAttribute({ openQuestions: [] })} />);
    expect(screen.queryByText('Open questions')).not.toBeInTheDocument();
  });

  it('rendersGenerationPassLabelWhenFirstPassSet', () => {
    render(<AttributeCard attribute={makeAttribute({ firstGenerationPass: 1, lastGenerationPass: 1 })} />);
    expect(screen.getByText('Generated in pass 1')).toBeInTheDocument();
  });

  it('rendersUpdatedPassLabelWhenBothPassesDiffer', () => {
    render(<AttributeCard attribute={makeAttribute({ firstGenerationPass: 1, lastGenerationPass: 3 })} />);
    expect(screen.getByText('Generated in pass 1 · Updated in pass 3')).toBeInTheDocument();
  });

  it('rendersLastUpdateSummaryWhenPresent', () => {
    render(
      <AttributeCard
        attribute={makeAttribute({ lastUpdateSummary: 'Refined threshold.' })}
      />,
    );
    expect(screen.getByText(/Updated: Refined threshold\./)).toBeInTheDocument();
  });

  it('rendersStaleWarningWhenAttributesStaleAndNoSummary', () => {
    render(
      <AttributeCard
        attribute={makeAttribute({ firstGenerationPass: 1, lastUpdateSummary: undefined })}
        sessionAttributesStale
      />,
    );
    expect(screen.getByText(/New context available/)).toBeInTheDocument();
  });
});
