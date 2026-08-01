import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MermaidDiagram } from '../components/MermaidDiagram';
import { DiagramErrorBoundary } from '../components/DiagramErrorBoundary';
import { DiagramDisplay, validateMermaidSource } from '../views/ArchitectureView';

// Mock mermaid since jsdom can't render SVG
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(),
  },
}));

import mermaid from 'mermaid';
const mockRender = vi.mocked(mermaid.render);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MermaidDiagram', () => {
  it('rendersEmptyState_whenChartIsEmpty', () => {
    render(<MermaidDiagram chart="" />);
    expect(screen.getByTestId('mermaid-empty')).toBeInTheDocument();
    expect(screen.getByText('No diagram available')).toBeInTheDocument();
  });

  it('rendersEmptyState_whenChartIsWhitespace', () => {
    render(<MermaidDiagram chart="   " />);
    expect(screen.getByTestId('mermaid-empty')).toBeInTheDocument();
  });

  it('rendersSVG_whenChartIsValid', async () => {
    mockRender.mockResolvedValue({ svg: '<svg>test</svg>', bindFunctions: vi.fn() } as never);

    render(<MermaidDiagram chart="graph LR; A-->B" id="test-diag" />);
    const container = screen.getByTestId('mermaid-container');
    expect(container).toBeInTheDocument();

    // Wait for async render
    await vi.waitFor(() => {
      expect(container.innerHTML).toContain('<svg>test</svg>');
    });
  });

  it('rendersErrorState_whenMermaidThrows', async () => {
    mockRender.mockRejectedValue(new Error('Parse error'));

    render(<MermaidDiagram chart="invalid chart" id="error-diag" />);

    const errorEl = await screen.findByTestId('mermaid-error');
    expect(errorEl).toBeInTheDocument();
    expect(errorEl.textContent).toContain('Parse error');
    // Should show raw source fallback
    expect(errorEl.textContent).toContain('invalid chart');
  });
});

describe('DiagramErrorBoundary', () => {
  it('catchesRenderErrors_withoutPropagatingToParent', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const BrokenDiagram = () => {
      throw new Error('boom');
    };

    render(
      <DiagramErrorBoundary
        diagramId="d1"
        diagramType="c4_container"
        source={'graph TD\nA-->B\nB-->C'}
      >
        <BrokenDiagram />
      </DiagramErrorBoundary>,
    );

    expect(screen.getByTestId('diagram-boundary-error')).toHaveTextContent(
      'Diagram could not be rendered',
    );
    consoleSpy.mockRestore();
  });

  it('showsRawSourceOnError', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const BrokenDiagram = () => {
      throw new Error('parse failed');
    };

    render(
      <DiagramErrorBoundary
        diagramId="d1"
        diagramType="sequence_primary"
        source={'sequenceDiagram\nA->>B: hello\nB-->>A: ok'}
      >
        <BrokenDiagram />
      </DiagramErrorBoundary>,
    );

    expect(screen.getByText('View raw source')).toBeInTheDocument();
    expect(screen.getByText(/sequenceDiagram/)).toBeInTheDocument();
    consoleSpy.mockRestore();
  });
});

describe('DiagramDisplay', () => {
  it('returnsErrorState_whenHasSyntaxErrorTrue', () => {
    render(
      <DiagramDisplay
        diagram={{
          diagramId: 'd1',
          type: 'c4_container',
          title: 'Containers',
          description: '',
          mermaidSource: 'bad',
          characteristicAddressed: '',
          hasSyntaxError: true,
          syntaxErrorDescription: 'Invalid syntax',
        }}
      />,
    );

    expect(screen.getByTestId('diagram-error-state')).toHaveTextContent('Invalid syntax');
  });

  it('preValidatesSourceBeforeRenderAttempt', () => {
    render(
      <DiagramDisplay
        diagram={{
          diagramId: 'd1',
          type: 'c4_container',
          title: 'Containers',
          description: '',
          mermaidSource: 'not-mermaid\nA-->B\nB-->C',
          characteristicAddressed: '',
        }}
      />,
    );

    expect(screen.getByTestId('diagram-validation-error')).toHaveTextContent(
      'Unrecognised diagram type',
    );
    expect(mockRender).not.toHaveBeenCalled();
  });
});

describe('validateMermaidSource', () => {
  it('returnsNullForValidGraphTD', () => {
    const source = 'graph TD\nA[Client] --> B[API]\nB --> C[DB]';

    expect(validateMermaidSource(source)).toBeNull();
  });

  it('returnsErrorForUndefinedInLabels', () => {
    const source = 'graph TD\nA --> undefined\nB --> C';

    expect(validateMermaidSource(source)).toBe('Literal undefined in edge label');
  });
});
