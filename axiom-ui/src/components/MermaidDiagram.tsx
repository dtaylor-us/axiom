import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
});

interface MermaidDiagramProps {
  chart: string;
  id?: string;
}

export function MermaidDiagram({ chart, id = 'mermaid-diagram' }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!chart.trim() || !containerRef.current) return;

    let cancelled = false;

    (async () => {
      try {
        const uniqueId = `${id}-${Date.now()}`;
        const { svg } = await mermaid.render(uniqueId, chart);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message ?? 'Failed to render diagram');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (!chart.trim()) {
    return (
      <p className="text-gray-400 italic" data-testid="mermaid-empty">
        No diagram available
      </p>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700" data-testid="mermaid-error">
        <p className="font-semibold">Diagram render error</p>
        <pre className="whitespace-pre-wrap mt-1">{error}</pre>
        <details className="mt-2">
          <summary className="cursor-pointer text-xs">Raw source</summary>
          <pre className="text-xs mt-1 whitespace-pre-wrap">{chart}</pre>
        </details>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-x-auto"
      data-testid="mermaid-container"
    />
  );
}
