import type { ClassifiedRequirement, ConflictItem } from '../../api/specweaver';

interface ConflictsPanelProps {
  conflicts: ConflictItem[];
  requirements: ClassifiedRequirement[];
}

/**
 * Shows conflicting requirements with source statements and clarifying questions.
 */
export function ConflictsPanel({ conflicts, requirements }: ConflictsPanelProps) {
  if (conflicts.length === 0) {
    return (
      <div className="conflicts-panel conflicts-panel--empty">
        <span>✓ No requirement conflicts detected</span>
      </div>
    );
  }

  const getRequirements = (ids: string[]) =>
    requirements.filter((requirement) => ids.includes(requirement.requirementId));

  return (
    <div className="conflicts-panel">
      <h3 className="conflicts-panel-title">Conflicts ({conflicts.length})</h3>
      <p className="conflicts-panel-description">
        These requirements contradict each other and require stakeholder clarification before architecture work begins.
      </p>
      <div className="conflicts-list">
        {conflicts.map((conflict) => (
          <div key={conflict.conflictId} className="conflict-item">
            <p className="conflict-description">⚡ {conflict.description}</p>

            <div className="conflict-requirements">
              {getRequirements(conflict.requirementIds).map((requirement) => (
                <div key={requirement.requirementId} className="conflict-requirement-ref">
                  <span className="conflict-req-id">{requirement.requirementId}</span>
                  <span className="conflict-req-statement">{requirement.statement}</span>
                </div>
              ))}
            </div>

            {conflict.interpretations.length > 0 && (
              <details className="conflict-interpretations">
                <summary>Possible interpretations</summary>
                <ul>
                  {conflict.interpretations.map((interpretation, index) => (
                    <li key={`${conflict.conflictId}-${index.toString()}`}>{interpretation}</li>
                  ))}
                </ul>
              </details>
            )}

            <div className="conflict-question">
              <span className="conflict-question-label">Q:</span>
              <span>{conflict.clarificationQuestion}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
