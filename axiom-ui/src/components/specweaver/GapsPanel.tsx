import type { GapArea } from '../../api/specweaver';

interface GapsPanelProps {
  gaps: GapArea[];
}

const SEVERITY_CONFIG = {
  critical: {
    label: 'Critical',
    color: 'var(--color-error)',
    icon: '🚫',
  },
  high: {
    label: 'High',
    color: 'var(--color-warning)',
    icon: '⚠',
  },
  medium: {
    label: 'Medium',
    color: 'var(--color-warning-light)',
    icon: '↓',
  },
  low: {
    label: 'Low',
    color: 'var(--color-text-secondary)',
    icon: 'ℹ',
  },
};

const SEVERITY_ORDER: GapArea['severity'][] = ['critical', 'high', 'medium', 'low'];

/**
 * Lists missing requirement areas and the clarification questions they create.
 */
export function GapsPanel({ gaps }: GapsPanelProps) {
  if (gaps.length === 0) {
    return (
      <div className="gaps-panel gaps-panel--empty">
        <span>✓ No requirement gaps identified</span>
      </div>
    );
  }

  const sorted = [...gaps].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );

  return (
    <div className="gaps-panel">
      <h3 className="gaps-panel-title">Requirement Gaps ({gaps.length})</h3>
      <p className="gaps-panel-description">
        These areas are missing from the requirements and may affect architecture decisions.
      </p>
      <div className="gaps-list">
        {sorted.map((gap) => {
          const config = SEVERITY_CONFIG[gap.severity];
          return (
            <div key={gap.gapId} className={`gap-item gap-item--${gap.severity}`}>
              <div className="gap-item-header">
                <span className="gap-severity-icon">{config.icon}</span>
                <span className="gap-area">{gap.area}</span>
                <span className="gap-severity-badge" style={{ color: config.color }}>
                  {config.label}
                </span>
              </div>
              <p className="gap-explanation">{gap.explanation}</p>
              <div className="gap-question">
                <span className="gap-question-label">Q:</span>
                <span>{gap.clarificationQuestion}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
