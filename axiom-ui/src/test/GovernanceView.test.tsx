import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GovernanceView, ScoreDimension } from '../views/GovernanceView';

let governanceState: Record<string, unknown>;
let sourcingState: Record<string, unknown>;
let architectureState: Record<string, unknown>;

vi.mock('../hooks/useGovernance', () => ({
  useGovernance: () => governanceState,
}));

vi.mock('../hooks/useBuyVsBuild', () => ({
  useBuyVsBuild: () => sourcingState,
}));

vi.mock('../hooks/useArchitecture', () => ({
  useArchitecture: () => architectureState,
}));

vi.mock('../hooks/useTactics', () => ({
  useTactics: () => ({ tactics: [], summary: null, loading: false }),
}));

// Mock child components
vi.mock('../components/MarkdownRenderer', () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="mock-markdown">{content}</div>
  ),
}));
vi.mock('../components/SeverityGrid', () => ({
  SeverityGrid: ({ entries }: { entries: unknown[] }) => (
    <div data-testid="mock-severity-grid">{entries.length} entries</div>
  ),
}));

describe('GovernanceView', () => {
  beforeEach(() => {
    governanceState = {
      tradeOffs: [],
      adl: null,
      weaknesses: null,
      fmea: [],
      governanceReport: null,
      loading: false,
      error: null,
    };
    sourcingState = {
      summary: null,
      loading: false,
      error: null,
      refresh: vi.fn(),
    };
    architectureState = {
      architecture: null,
      loading: false,
      error: null,
      refresh: vi.fn(),
    };
  });

  it('rendersLoadingState', () => {
    governanceState.loading = true;
    render(<GovernanceView />);
    expect(screen.getByTestId('governance-loading')).toBeInTheDocument();
  });

  it('rendersErrorState', () => {
    governanceState.error = 'Failed';
    render(<GovernanceView />);
    expect(screen.getByTestId('governance-error')).toHaveTextContent('Failed');
  });

  it('rendersTradeOffsTab_empty', () => {
    render(<GovernanceView />);
    expect(screen.getByTestId('panel-trade-offs')).toBeInTheDocument();
    expect(screen.getByText('No trade-off decisions available')).toBeInTheDocument();
  });

  it('rendersTradeOffsTab_withData', () => {
    governanceState.tradeOffs = [
      {
        decision_id: 'TD-001',
        decision: 'Use async messaging',
        optimises_characteristics: ['Scalability'],
        sacrifices_characteristics: ['Simplicity'],
        recommendation: 'High throughput needed',
        context_dependency: 'Complexity',
        confidence: 'high',
      },
    ];
    render(<GovernanceView />);
    expect(screen.getByText('Use async messaging')).toBeInTheDocument();
    expect(screen.getByText('Scalability')).toBeInTheDocument();
  });

  it('switchesToADLTab', async () => {
    governanceState.adl = {
      document: 'ADL_DOC_CONTENT',
      rules: [{ rule_id: 'REQUIRE-001', category: 'REQUIRE', subject: 'API', statement: 'TLS required' }],
    };
    const user = userEvent.setup();
    render(<GovernanceView />);

    await user.click(screen.getByTestId('tab-adl'));
    expect(screen.getByTestId('panel-adl')).toBeInTheDocument();
    expect(screen.getByText('Rules (1)')).toBeInTheDocument();
    expect(screen.getByText('REQUIRE')).toBeInTheDocument();
  });

  it('switchesToWeaknessesTab_empty', async () => {
    const user = userEvent.setup();
    render(<GovernanceView />);

    await user.click(screen.getByTestId('tab-weaknesses'));
    expect(screen.getByTestId('panel-weaknesses')).toBeInTheDocument();
    expect(screen.getByText('No weaknesses identified')).toBeInTheDocument();
  });

  it('switchesToWeaknessesTab_withData', async () => {
    governanceState.weaknesses = {
      summary: 'Two issues found',
      weaknesses: [
        {
          id: 'W-1',
          title: 'No auth',
          description: 'Missing auth',
          severity: 9,
          component_affected: 'API',
          mitigation: 'Add OAuth2',
        },
      ],
    };
    const user = userEvent.setup();
    render(<GovernanceView />);

    await user.click(screen.getByTestId('tab-weaknesses'));
    expect(screen.getByText('Two issues found')).toBeInTheDocument();
    expect(screen.getByText('No auth')).toBeInTheDocument();
    expect(screen.getByText('Severity 9/10')).toBeInTheDocument();
    expect(screen.getByText('API')).toBeInTheDocument();
  });

  it('switchesToFMEATab', async () => {
    governanceState.fmea = [{ id: 'F-1' }];
    const user = userEvent.setup();
    render(<GovernanceView />);

    await user.click(screen.getByTestId('tab-fmea'));
    expect(screen.getByTestId('panel-fmea')).toBeInTheDocument();
    expect(screen.getByTestId('mock-severity-grid')).toHaveTextContent('1 entries');
  });

  it('fillsMissingSourcingDecisionsFromComponentOwnership', async () => {
    architectureState.architecture = {
      conversationId: 'conv-1',
      style: 'Layered',
      componentDiagram: 'graph TD; A-->B',
      sequenceDiagram: 'sequenceDiagram\nA->>B: ping',
      interactions: [],
      components: [
        {
          name: 'Authentication Service',
          ownership: 'bought-saas',
          responsibility: 'User authentication',
          technology: 'Auth0',
        },
      ],
    };
    sourcingState.summary = {
      summaryText: '',
      totalDecisions: 0,
      buildCount: 0,
      buyCount: 0,
      adoptCount: 0,
      conflictCount: 0,
      decisions: [],
    };

    const user = userEvent.setup();
    render(<GovernanceView />);

    await user.click(screen.getByTestId('tab-sourcing'));

    expect(screen.getByText('Buy 1')).toBeInTheDocument();
    expect(screen.getByText('Authentication Service')).toBeInTheDocument();
    expect(screen.getByText('Decision inferred from component ownership metadata.')).toBeInTheDocument();
  });

  it('scoreDimension_rendersEvidenceTextBelowBar', () => {
    render(
      <ScoreDimension
        label="Requirement coverage"
        score={16}
        maxScore={20}
        evidence="Covered 8 of 10 requirements."
        positive
      />,
    );

    expect(screen.getByText('Covered 8 of 10 requirements.')).toBeInTheDocument();
    expect(screen.getByText('+16/20')).toBeInTheDocument();
  });

  it('scoreDimension_showsCorrectColorForScoreRatio', () => {
    render(
      <ScoreDimension
        label="Trade-off quality"
        score={18}
        maxScore={20}
        evidence="Strong trade-off coverage."
        positive
      />,
    );

    expect(screen.getByText('+18/20')).toHaveClass('text-emerald-700');
  });
});
