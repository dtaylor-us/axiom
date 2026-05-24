import React from 'react';

interface Props {
  diagramId: string;
  diagramType: string;
  source?: string;
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

/**
 * Contains render failures for one diagram so sibling diagrams still render.
 */
export class DiagramErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error.message,
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(
      'DiagramErrorBoundary caught error. ' +
        'diagramId=' + this.props.diagramId + ' ' +
        'diagramType=' + this.props.diagramType,
      error,
      info,
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="diagram-boundary-error border border-amber-200 rounded-lg px-4 py-3 bg-amber-50 min-h-[120px] max-w-full overflow-hidden [contain:layout_style]"
          data-testid="diagram-boundary-error"
        >
          <div className="diagram-boundary-error-header flex items-center gap-2">
            <span className="diagram-type-chip text-xs font-semibold rounded bg-amber-100 text-amber-900 px-2 py-0.5">
              {this.props.diagramType}
            </span>
            <span className="diagram-error-label text-sm font-semibold text-amber-950">
              Diagram could not be rendered
            </span>
          </div>
          <p className="diagram-error-detail text-sm text-amber-900 mt-2">
            {this.state.errorMessage}
          </p>
          {this.props.source && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-amber-900">
                View raw source
              </summary>
              <pre className="diagram-raw-source font-mono text-[11px] overflow-x-auto max-h-[200px] bg-white p-2 rounded mt-2 whitespace-pre">
                {this.props.source}
              </pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
