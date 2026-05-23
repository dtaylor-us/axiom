import { describe, it, expect } from 'vitest';
import {
  buildQualityAttributesMarkdown,
  buildScenariosMarkdown,
} from '../views/workshop/workshopMarkdown';
import type { QualityAttribute, WorkshopScenario } from '../types/workshop';

/** Minimal QualityAttribute fixture with required fields only. */
function makeAttribute(overrides: Partial<QualityAttribute> = {}): QualityAttribute {
  return {
    attributeId: 'qa-001',
    name: 'Performance',
    category: 'performance_efficiency',
    description: 'Response time under 200ms at 95th percentile.',
    importance: 'H',
    confidence: 'confirmed',
    scenarioCompleteness: 'FULL',
    openQuestions: [],
    evidenceQuotes: [],
    resolvedAnswers: [],
    firstGenerationPass: null,
    lastGenerationPass: null,
    lastUpdateSummary: null,
    lastUpdatedTurn: null,
    ...overrides,
  };
}

/** Minimal WorkshopScenario fixture. */
function makeScenario(overrides: Partial<WorkshopScenario> = {}): WorkshopScenario {
  return {
    scenarioId: 'scn-001',
    title: 'Peak load checkout',
    completeness: 'FULL',
    derivedInTurn: 3,
    stimulus: 'User submits order',
    source: 'End customer',
    environment: 'Normal operation',
    artifact: 'Checkout service',
    response: 'Order confirmed',
    responseMeasure: '< 200ms',
    exercisesAttributes: ['Performance'],
    evidenceQuote: '',
    ...overrides,
  };
}

describe('buildQualityAttributesMarkdown', () => {
  it('startsWithH1Heading', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute()]);
    expect(md).toMatch(/^# Quality attributes/);
  });

  it('includesSystemNameWhenProvided', () => {
    const md = buildQualityAttributesMarkdown([], { systemName: 'Order Service' });
    expect(md).toContain('**System:** Order Service');
  });

  it('includesSessionIdWhenProvided', () => {
    const md = buildQualityAttributesMarkdown([], { sessionId: 'ws-123' });
    expect(md).toContain('**Session:** `ws-123`');
  });

  it('doesNotIncludeSystemNameWhenNotProvided', () => {
    const md = buildQualityAttributesMarkdown([]);
    expect(md).not.toContain('**System:**');
  });

  it('rendersAttributeNameAsH2', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({ name: 'Scalability' })]);
    expect(md).toContain('## Scalability');
  });

  it('rendersAttributeIdWithBackticks', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({ attributeId: 'qa-99' })]);
    expect(md).toContain('`qa-99`');
  });

  it('rendersAttributeCategoryImportanceConfidence', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      category: 'reliability',
      importance: 'M',
      confidence: 'partial',
    })]);
    expect(md).toContain('- **Category:** reliability');
    expect(md).toContain('- **Importance:** M');
    expect(md).toContain('- **Confidence:** partial');
  });

  it('rendersDescriptionBlock', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      description: 'Must handle 10k rps.',
    })]);
    expect(md).toContain('Must handle 10k rps.');
  });

  it('rendersEmptyDescriptionAsPlaceholder', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({ description: '' })]);
    expect(md).toContain('_—_');
  });

  it('rendersOpenQuestionsWhenPresent', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      openQuestions: ['What is the SLA?', 'Who defines the budget?'],
    })]);
    expect(md).toContain('### Open questions');
    expect(md).toContain('- What is the SLA?');
    expect(md).toContain('- Who defines the budget?');
  });

  it('doesNotRenderOpenQuestionsWhenEmpty', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({ openQuestions: [] })]);
    expect(md).not.toContain('### Open questions');
  });

  it('rendersEvidenceQuotesWhenPresent', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      evidenceQuotes: ['We need 99.9% uptime.'],
    })]);
    expect(md).toContain('### Evidence quotes');
    expect(md).toContain('> We need 99.9% uptime.');
  });

  it('rendersGenerationPassesWhenBothSet', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      firstGenerationPass: 2,
      lastGenerationPass: 5,
    })]);
    expect(md).toContain('**Generation passes:** 2 → 5');
  });

  it('rendersLastUpdateSummaryWhenPresent', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      lastUpdateSummary: 'Refined threshold.',
    })]);
    expect(md).toContain('**Last update:** Refined threshold.');
  });

  it('rendersLastUpdatedTurnWhenPresent', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({ lastUpdatedTurn: 7 })]);
    expect(md).toContain('**Last updated turn:** 7');
  });

  it('rendersResolvedAnswersWhenPresent', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute({
      resolvedAnswers: [{
        question: 'What is the target?',
        answer: '200ms at p95.',
        resolvedInTurn: 4,
        evidenceQuote: 'User said 200ms.',
      }],
    })]);
    expect(md).toContain('### Resolved answers');
    expect(md).toContain('#### Q (turn 4)');
    expect(md).toContain('What is the target?');
    expect(md).toContain('200ms at p95.');
    expect(md).toContain('_Evidence:_ User said 200ms.');
  });

  it('endsWithHorizontalRule', () => {
    const md = buildQualityAttributesMarkdown([makeAttribute()]);
    expect(md).toContain('---');
  });

  it('handlesMultipleAttributes', () => {
    const md = buildQualityAttributesMarkdown([
      makeAttribute({ name: 'Performance' }),
      makeAttribute({ attributeId: 'qa-002', name: 'Security' }),
    ]);
    expect(md).toContain('## Performance');
    expect(md).toContain('## Security');
  });
});

describe('buildScenariosMarkdown', () => {
  it('startsWithH1Heading', () => {
    const md = buildScenariosMarkdown([makeScenario()]);
    expect(md).toMatch(/^# Workshop scenarios/);
  });

  it('includesSystemNameWhenProvided', () => {
    const md = buildScenariosMarkdown([], { systemName: 'Billing Service' });
    expect(md).toContain('**System:** Billing Service');
  });

  it('includesSessionIdWhenProvided', () => {
    const md = buildScenariosMarkdown([], { sessionId: 'ws-456' });
    expect(md).toContain('**Session:** `ws-456`');
  });

  it('rendersScenarioTitleAsH2', () => {
    const md = buildScenariosMarkdown([makeScenario({ title: 'High load checkout' })]);
    expect(md).toContain('## High load checkout');
  });

  it('rendersUntitledWhenTitleIsEmpty', () => {
    const md = buildScenariosMarkdown([makeScenario({ title: '' })]);
    expect(md).toContain('## Untitled scenario');
  });

  it('rendersScenarioId', () => {
    const md = buildScenariosMarkdown([makeScenario({ scenarioId: 'scn-999' })]);
    expect(md).toContain('`scn-999`');
  });

  it('replacesUnderscoresInCompleteness', () => {
    const md = buildScenariosMarkdown([makeScenario({ completeness: 'IN_PROGRESS' as 'FULL' })]);
    expect(md).toContain('IN PROGRESS');
  });

  it('rendersStimulusSourceEnvironment', () => {
    const md = buildScenariosMarkdown([makeScenario({
      stimulus: 'Payment submitted',
      source: 'Merchant',
      environment: 'Peak hours',
    })]);
    expect(md).toContain('**Stimulus:** Payment submitted');
    expect(md).toContain('**Source:** Merchant');
    expect(md).toContain('**Environment:** Peak hours');
  });

  it('rendersArtifactResponseMeasure', () => {
    const md = buildScenariosMarkdown([makeScenario({
      artifact: 'Payment gateway',
      response: 'Payment processed',
      responseMeasure: '< 500ms',
    })]);
    expect(md).toContain('**Artifact:** Payment gateway');
    expect(md).toContain('**Response:** Payment processed');
    expect(md).toContain('**Response measure:** < 500ms');
  });

  it('rendersExercisesAttributesWhenPresent', () => {
    const md = buildScenariosMarkdown([makeScenario({ exercisesAttributes: ['Performance', 'Security'] })]);
    expect(md).toContain('**Exercises attributes:** Performance, Security');
  });

  it('rendersEvidenceQuoteWhenPresent', () => {
    const md = buildScenariosMarkdown([makeScenario({ evidenceQuote: 'Must be fast' })]);
    expect(md).toContain('### Evidence');
    expect(md).toContain('> Must be fast');
  });

  it('doesNotRenderEvidenceSectionWhenQuoteIsEmpty', () => {
    const md = buildScenariosMarkdown([makeScenario({ evidenceQuote: '' })]);
    expect(md).not.toContain('### Evidence');
  });

  it('skipsEmptyOptionalFields', () => {
    const md = buildScenariosMarkdown([makeScenario({
      stimulus: '',
      source: '',
      environment: '',
    })]);
    expect(md).not.toContain('**Stimulus:**');
    expect(md).not.toContain('**Source:**');
    expect(md).not.toContain('**Environment:**');
  });

  it('handlesMultipleScenarios', () => {
    const md = buildScenariosMarkdown([
      makeScenario({ title: 'Scenario A' }),
      makeScenario({ scenarioId: 'scn-002', title: 'Scenario B' }),
    ]);
    expect(md).toContain('## Scenario A');
    expect(md).toContain('## Scenario B');
  });

  it('endsWithHorizontalRule', () => {
    const md = buildScenariosMarkdown([makeScenario()]);
    expect(md).toContain('---');
  });
});
