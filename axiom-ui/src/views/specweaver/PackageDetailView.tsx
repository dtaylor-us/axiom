import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import type {
  ClassifiedRequirement,
  Confidence,
  RequirementAnnotation,
  RequirementReview,
} from '../../api/specweaver';
import { ConflictsPanel } from '../../components/specweaver/ConflictsPanel';
import { GapsPanel } from '../../components/specweaver/GapsPanel';
import { ReadinessScore } from '../../components/specweaver/ReadinessScore';
import { useStore } from '../../store/useStore';
import { useSpecWeaverStore } from '../../store/useSpecWeaverStore';
import { downloadPackageExport } from './packageExport';
import { PillarBadge } from '../../components/PillarBadge';

const CATEGORY_LABELS: Record<string, string> = {
  business_objectives: 'Business Objectives',
  system_scope: 'System Scope',
  actors_and_users: 'Actors and Users',
  functional: 'Functional Requirements',
  non_functional: 'Non-Functional Requirements',
  constraints: 'Constraints',
  integrations: 'Integrations',
  data_considerations: 'Data Considerations',
  assumptions: 'Assumptions',
  risks: 'Risks',
};

const CATEGORY_ORDER = Object.keys(CATEGORY_LABELS);
const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'requirements', label: 'Requirements' },
  { id: 'gaps', label: 'Gaps' },
  { id: 'conflicts', label: 'Conflicts' },
] as const;

type PackageTab = (typeof TABS)[number]['id'];

function confidenceClass(confidence: Confidence): string {
  if (confidence === 'HIGH') return 'bg-accent/10 text-accent ring-accent/20';
  if (confidence === 'MEDIUM') return 'bg-amber-50 text-amber-700 ring-amber-200';
  if (confidence === 'LOW') return 'bg-red-50 text-red-700 ring-red-100';
  return 'bg-purple-50 text-purple-700 ring-purple-100';
}

function annotationLabel(annotation: RequirementAnnotation): string {
  if (annotation === 'accepted') return 'Accepted';
  if (annotation === 'flagged') return 'Flagged';
  return 'Edited';
}

function groupRequirements(requirements: ClassifiedRequirement[]): Record<string, ClassifiedRequirement[]> {
  return requirements.reduce<Record<string, ClassifiedRequirement[]>>((groups, requirement) => {
    if (!groups[requirement.category]) groups[requirement.category] = [];
    groups[requirement.category].push(requirement);
    return groups;
  }, {});
}

interface RequirementCardProps {
  requirement: ClassifiedRequirement;
  review?: RequirementReview;
  onAnnotate: (
    requirementId: string,
    annotation: RequirementAnnotation,
    note?: string,
    editedStatement?: string,
  ) => void;
}

function RequirementCard({ requirement, review, onAnnotate }: RequirementCardProps) {
  const [draftNote, setDraftNote] = useState(review?.note ?? '');
  const [draftStatement, setDraftStatement] = useState(review?.editedStatement ?? requirement.statement);
  const displayedStatement = review?.editedStatement ?? requirement.statement;

  const annotate = (annotation: RequirementAnnotation) => {
    onAnnotate(
      requirement.requirementId,
      annotation,
      draftNote.trim() || undefined,
      annotation === 'edited' ? draftStatement.trim() || requirement.statement : undefined,
    );
  };

  return (
    <article className="requirement-review-card rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <p className="text-[14px] font-medium leading-relaxed text-gray-900">{displayedStatement}</p>
        <div className="flex shrink-0 flex-wrap gap-1.5">
          <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ring-1 ${confidenceClass(requirement.confidence)}`}>
            {requirement.confidence}
          </span>
          {requirement.isInferred && (
            <span className="rounded-full bg-purple-50 px-2 py-1 text-[10px] font-semibold text-purple-700 ring-1 ring-purple-100">
              INFERRED
            </span>
          )}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span className="rounded bg-gray-100 px-2 py-1 text-[10px] font-medium text-gray-600">
          {requirement.requirementId}
        </span>
        <span className="rounded bg-gray-100 px-2 py-1 text-[10px] font-medium text-gray-600">
          {requirement.type}
        </span>
        {review && (
          <span className={`review-status review-status--${review.annotation}`}>
            {annotationLabel(review.annotation)}
          </span>
        )}
      </div>
      {requirement.inferenceReasoning && (
        <p className="mt-3 rounded border border-purple-100 bg-purple-50 px-3 py-2 text-[12px] text-purple-700">
          {requirement.inferenceReasoning}
        </p>
      )}
      {requirement.ambiguities.length > 0 && (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">Ambiguities</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-[12px] text-amber-900">
            {requirement.ambiguities.map((ambiguity) => (
              <li key={`${requirement.requirementId}-${ambiguity}`}>{ambiguity}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="requirement-review-controls">
        <div className="requirement-review-actions">
          <button type="button" className="review-action-button" onClick={() => annotate('accepted')}>
            ✓ Accept
          </button>
          <button type="button" className="review-action-button" onClick={() => annotate('flagged')}>
            ⚑ Flag
          </button>
          <button type="button" className="review-action-button" onClick={() => annotate('edited')}>
            Edit Statement
          </button>
        </div>
        <label className="review-field">
          <span>Edited statement</span>
          <textarea
            value={draftStatement}
            onChange={(event) => setDraftStatement(event.target.value)}
            rows={2}
          />
        </label>
        <label className="review-field">
          <span>Clarification note</span>
          <textarea
            value={draftNote}
            onChange={(event) => setDraftNote(event.target.value)}
            onBlur={() => {
              if (review) annotate(review.annotation);
            }}
            rows={2}
            placeholder="Add stakeholder clarification or review context"
          />
        </label>
        {review?.note && (
          <p className="review-note">Note: {review.note}</p>
        )}
      </div>

      <details className="mt-3">
        <summary className="cursor-pointer text-[12px] font-medium text-gray-500">Source documents</summary>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {requirement.sourceDocumentIds.map((documentId) => (
            <span key={documentId} className="rounded bg-gray-100 px-2 py-1 text-[11px] text-gray-600">
              {documentId}
            </span>
          ))}
        </div>
      </details>
      <details className="mt-2">
        <summary className="cursor-pointer text-[12px] font-medium text-gray-500">Source excerpts</summary>
        <div className="mt-2 space-y-2">
          {requirement.sourceExcerpts.map((excerpt, index) => (
            <blockquote key={`${requirement.requirementId}-${index.toString()}`} className="rounded bg-gray-50 p-3 text-[12px] leading-relaxed text-gray-600">
              {excerpt}
            </blockquote>
          ))}
        </div>
      </details>
    </article>
  );
}

/**
 * Review workspace for a generated SpecWeaver package before Archon handoff.
 */
export function PackageDetailView() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const token = useStore((state) => state.token)!;
  const currentPackage = useSpecWeaverStore((state) => state.currentPackage);
  const isSending = useSpecWeaverStore((state) => state.isSending);
  const error = useSpecWeaverStore((state) => state.error);
  const loadSession = useSpecWeaverStore((state) => state.loadSession);
  const sendToArchon = useSpecWeaverStore((state) => state.sendToArchon);
  const clearError = useSpecWeaverStore((state) => state.clearError);
  const [activeTab, setActiveTab] = useState<PackageTab>('overview');
  const [reviews, setReviews] = useState<Map<string, RequirementReview>>(new Map());

  useEffect(() => {
    document.title = 'SpecWeaver — Requirements Intelligence | Axiom';
  }, []);

  useEffect(() => {
    if (sessionId) void loadSession(token, sessionId);
  }, [loadSession, sessionId, token]);

  const groupedRequirements = useMemo(
    () => groupRequirements(currentPackage?.requirements ?? []),
    [currentPackage?.requirements],
  );

  if (!sessionId) {
    return <div className="p-6 text-[13px] text-gray-500">Session not found.</div>;
  }

  const handleSendToArchon = async () => {
    const briefText = await sendToArchon(token, sessionId);
      navigate('/archon', {
      state: {
        prefillMessage: briefText,
        source: 'specweaver',
        sessionId,
      },
    });
  };

  const handleAnnotate = (
    requirementId: string,
    annotation: RequirementAnnotation,
    note?: string,
    editedStatement?: string,
  ) => {
    setReviews((previousReviews) => {
      const nextReviews = new Map(previousReviews);
      nextReviews.set(requirementId, {
        requirementId,
        annotation,
        note,
        editedStatement,
      });
      return nextReviews;
    });
  };

  const criticalGaps = currentPackage?.gaps.filter((gap) => gap.severity === 'critical').length ?? 0;
  const highGaps = currentPackage?.gaps.filter((gap) => gap.severity === 'high').length ?? 0;

  return (
    <div className="specweaver-scope package-detail-view h-full overflow-y-auto bg-gray-50" data-testid="specweaver-package-detail">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <div className="package-detail-header">
          <div className="min-w-0 flex-1">
            <div className="mb-2">
              <PillarBadge pillar="specweaver" />
            </div>
            <Link to={`/specweaver/sessions/${sessionId}`} className="text-[12px] font-medium text-accent hover:underline">
              ← Back to session
            </Link>
            <h1>Requirements Package</h1>
            {currentPackage && (
              <p className="package-system-description">{currentPackage.systemDescription}</p>
            )}
          </div>
          {currentPackage && (
            <div className="package-export-actions">
              <button type="button" onClick={() => downloadPackageExport(currentPackage, 'markdown')}>
                Export Markdown
              </button>
              <button type="button" onClick={() => downloadPackageExport(currentPackage, 'text')}>
                Export Text
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-700" role="alert">
            {error}
            <button type="button" className="ml-2 underline" onClick={clearError}>
              Dismiss
            </button>
          </div>
        )}

        {!currentPackage ? (
          <div className="rounded-lg border border-dashed border-gray-200 bg-white p-8 text-center text-[13px] text-gray-500">
            Loading package...
          </div>
        ) : (
          <>
            <div className="package-tabs" role="tablist" aria-label="Package review tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={`package-tab ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                  {tab.id === 'gaps' && currentPackage.gapCount > 0 && (
                    <span className="tab-badge tab-badge--warning">{currentPackage.gapCount}</span>
                  )}
                  {tab.id === 'conflicts' && currentPackage.conflictCount > 0 && (
                    <span className="tab-badge tab-badge--error">{currentPackage.conflictCount}</span>
                  )}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div className="package-tab-content">
                <ReadinessScore
                  score={currentPackage.readinessScore}
                  label={currentPackage.readinessLabel}
                  gapCount={currentPackage.gapCount}
                  conflictCount={currentPackage.conflictCount}
                  inferredCount={currentPackage.inferredCount}
                  totalCount={currentPackage.totalRequirements}
                  criticalGaps={criticalGaps}
                  highGaps={highGaps}
                />

                <div className="package-stats-grid">
                  <div className="stat-card">
                    <span className="stat-value">{currentPackage.totalRequirements}</span>
                    <span className="stat-label">Requirements</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{currentPackage.highConfidenceCount}</span>
                    <span className="stat-label">High Confidence</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{currentPackage.inferredCount}</span>
                    <span className="stat-label">Inferred</span>
                  </div>
                  {currentPackage.duplicateCount > 0 && (
                    <div className="stat-card stat-card--muted">
                      <span className="stat-value">{currentPackage.duplicateCount}</span>
                      <span className="stat-label">Deduplicated</span>
                    </div>
                  )}
                </div>

                <div className="send-to-archon-section">
                  {currentPackage.readinessScore < 0.5 && (
                    <div className="readiness-warning">
                      ⚠ This package has significant gaps or conflicts. Consider addressing them before sending to Archon for best results.
                    </div>
                  )}
                  <button
                    type="button"
                    className="btn btn-primary btn-send-archon"
                    onClick={() => void handleSendToArchon()}
                    disabled={isSending || currentPackage.readinessScore <= 0}
                  >
                    {isSending ? 'Preparing brief...' : 'Open in Archon →'}
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'requirements' && (
              <div className="package-tab-content">
                <div className="space-y-6">
                  {CATEGORY_ORDER.map((category) => {
                    const requirements = groupedRequirements[category] ?? [];
                    return (
                      <section key={category}>
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <h2 className="text-[14px] font-semibold text-gray-900">{CATEGORY_LABELS[category]}</h2>
                          <span className="rounded bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-500">
                            {requirements.length}
                          </span>
                        </div>
                        {requirements.length === 0 ? (
                          <div className="rounded-lg border border-dashed border-gray-200 bg-white p-4 text-[12px] text-gray-400">
                            No requirements in this category.
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {requirements.map((requirement) => (
                              <RequirementCard
                                key={requirement.requirementId}
                                requirement={requirement}
                                review={reviews.get(requirement.requirementId)}
                                onAnnotate={handleAnnotate}
                              />
                            ))}
                          </div>
                        )}
                      </section>
                    );
                  })}
                </div>
              </div>
            )}

            {activeTab === 'gaps' && (
              <div className="package-tab-content">
                <GapsPanel gaps={currentPackage.gaps} />
              </div>
            )}

            {activeTab === 'conflicts' && (
              <div className="package-tab-content">
                <ConflictsPanel
                  conflicts={currentPackage.conflicts}
                  requirements={currentPackage.requirements}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
