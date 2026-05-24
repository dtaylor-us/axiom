import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArchitectureView } from '../views/ArchitectureView';

let architectureState: Record<string, unknown>;
let diagramsState: Record<string, unknown>;

vi.mock('../hooks/useArchitecture', () => ({
  useArchitecture: () => architectureState,
}));

vi.mock('../hooks/useDiagrams', () => ({
  useDiagrams: () => diagramsState,
}));

// Mock MermaidDiagram to avoid mermaid import in jsdom
vi.mock('../components/MermaidDiagram', () => ({
  MermaidDiagram: ({ chart }: { chart: string }) => (
    <div data-testid="mock-mermaid">{chart}</div>
  ),
}));

describe('ArchitectureView', () => {
  beforeEach(() => {
    architectureState = {
      architecture: null,
      loading: false,
      error: null,
    };
    diagramsState = { collection: null, loading: false, error: null };
  });

  it('rendersLoadingState', () => {
    architectureState.loading = true;
    render(<ArchitectureView />);
    expect(screen.getByTestId('architecture-loading')).toBeInTheDocument();
  });

  it('rendersErrorState', () => {
    architectureState.error = 'API failed';
    render(<ArchitectureView />);
    expect(screen.getByTestId('architecture-error')).toHaveTextContent('API failed');
  });

  it('rendersEmptyState', () => {
    render(<ArchitectureView />);
    expect(screen.getByTestId('architecture-empty')).toBeInTheDocument();
  });

  it('rendersFallbackDiagramsWhenCollectionEmpty', () => {
    architectureState.architecture = {
      conversationId: 'c1',
      style: 'Microservices',
      components: [
        { name: 'API Gateway', ownership: 'enterprise-built', responsibility: 'Routing', technology: 'Spring' },
        { name: 'Okta Integration', ownership: 'bought-saas', responsibility: 'Auth', technology: 'Okta SDK' },
      ],
      interactions: [
        { from: 'API Gateway', to: 'Okta Integration', protocol: 'HTTP', purpose: 'Auth' },
      ],
      componentDiagram: 'graph LR; A-->B',
      sequenceDiagram: 'sequenceDiagram; A->>B: call',
    };

    render(<ArchitectureView />);
    expect(screen.getByTestId('architecture-view')).toBeInTheDocument();
    expect(screen.getByText('Microservices')).toBeInTheDocument();
    expect(screen.getByText('Built')).toBeInTheDocument();
    expect(screen.getByText('Bought')).toBeInTheDocument();
    // Falls back to two compat diagram sections
    expect(screen.getAllByTestId('mock-mermaid')).toHaveLength(2);
  });

  it('rendersDiagramCollectionWhenPresent', () => {
    architectureState.architecture = {
      conversationId: 'c1',
      style: 'Microservices',
      components: [],
      interactions: [],
      componentDiagram: '',
      sequenceDiagram: '',
    };
    diagramsState = {
      collection: {
        diagramCount: 3,
        diagramTypes: ['c4_container', 'sequence_primary', 'state'],
        diagrams: [
          {
            diagramId: 'D-001',
            type: 'c4_container',
            title: 'C4 Container View',
            description: 'Container architecture',
            mermaidSource: 'graph TD\nA-->B\nB-->C',
            characteristicAddressed: 'modularity',
          },
          {
            diagramId: 'D-002',
            type: 'sequence_primary',
            title: 'Primary Flow',
            description: 'Happy path sequence',
            mermaidSource: 'sequenceDiagram\nA->>B: call\nB-->>A: response',
            characteristicAddressed: 'performance',
          },
          {
            diagramId: 'D-003',
            type: 'state',
            title: 'Order State Machine',
            description: 'Order lifecycle states',
            mermaidSource: 'stateDiagram-v2\n[*] --> pending\npending --> complete',
            characteristicAddressed: 'reliability',
          },
        ],
      },
      loading: false,
      error: null,
    };

    render(<ArchitectureView />);
    expect(screen.getAllByTestId('mock-mermaid')).toHaveLength(3);
    expect(screen.getByText('C4 Container View')).toBeInTheDocument();
    expect(screen.getByText('Primary Flow')).toBeInTheDocument();
    expect(screen.getByText('Order State Machine')).toBeInTheDocument();
    expect(screen.getByText('Addresses: modularity')).toBeInTheDocument();
  });
});
