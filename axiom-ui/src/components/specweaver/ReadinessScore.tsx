interface ReadinessScoreProps {
  score: number;
  label: string;
  gapCount: number;
  conflictCount: number;
  inferredCount: number;
  totalCount: number;
  criticalGaps: number;
  highGaps: number;
}

/**
 * Displays package readiness as a visual gauge with the main review drivers.
 */
export function ReadinessScore({
  score,
  label,
  gapCount,
  conflictCount,
  inferredCount,
  totalCount,
  criticalGaps,
  highGaps,
}: ReadinessScoreProps) {
  const percentage = Math.round(score * 100);
  const hasHighInferredRatio = totalCount > 0 && inferredCount / totalCount > 0.4;
  const scoreColor =
    score >= 0.85 ? 'var(--color-success)' :
      score >= 0.70 ? 'var(--color-warning)' :
        score >= 0.50 ? 'var(--color-warning-dark)' :
          'var(--color-error)';

  return (
    <div className="readiness-score">
      <div className="readiness-score-header">
        <span className="readiness-score-label">Readiness Score</span>
        <span className="readiness-score-value" style={{ color: scoreColor }}>
          {percentage}%
        </span>
      </div>

      <div
        className="readiness-score-bar"
        aria-label={`Readiness score ${percentage}%, ${gapCount} gaps, ${conflictCount} conflicts`}
      >
        <div
          className="readiness-score-fill"
          style={{
            width: `${percentage}%`,
            background: scoreColor,
          }}
        />
      </div>

      <p className="readiness-score-description">{label}</p>

      <div className="readiness-score-breakdown">
        {criticalGaps > 0 && (
          <div className="readiness-deduction critical">
            ⚠ {criticalGaps} critical gap{criticalGaps > 1 ? 's' : ''}
          </div>
        )}
        {highGaps > 0 && (
          <div className="readiness-deduction high">
            ↓ {highGaps} high-severity gap{highGaps > 1 ? 's' : ''}
          </div>
        )}
        {conflictCount > 0 && (
          <div className="readiness-deduction conflict">
            ⚡ {conflictCount} unresolved conflict{conflictCount > 1 ? 's' : ''}
          </div>
        )}
        {hasHighInferredRatio && (
          <div className="readiness-deduction inferred">
            ~ High inferred requirement ratio
          </div>
        )}
      </div>
    </div>
  );
}
