import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  answerGapQuestion,
  assessGaps,
  createReviewSession,
  deleteEvidence,
  forceProceed,
  generateGapQuestions,
  getReviewReport,
  getReviewSession,
  listGapQuestions,
  listEvidence,
  startReview,
  submitEvidence,
  updateReviewSession,
  type ArchitectureEvidence,
  type EvidenceType,
  type GapAssessmentResult,
  type GapQuestion,
  type ReviewReport,
  type ReviewSession,
} from '../../api/lens';
import { CopyButton } from '../../components/CopyButton';
import { MarkdownExportActions } from '../../components/StructuredData';
import { PillarBadge } from '../../components/PillarBadge';
import { ReviewReport as ReviewReportView } from '../../components/lens/ReviewReport';
import { StageProgress } from '../../components/StageProgress';
import { useStore } from '../../store/useStore';
import type { StageState, StageStatus } from '../../types/api';
import { buildLensStatusMarkdown, lensStatusMarkdownFilename } from './lensMarkdown';

const LENS_STAGE_NAMES = [
  'evidence_parsing',
  'azure_waf_analysis',
  'atam_analysis',
  'sei_analysis',
  'structural_analysis',
  'risk_identification',
  'recommendation_generation',
  'executive_summary',
  'report_assembly',
  'review_complete',
] as const;

const EVIDENCE_TYPES: EvidenceType[] = [
  'TEXT_DESCRIPTION',
  'ADL_CONTENT',
  'DIAGRAM_DESCRIPTION',
  'DECISION_RECORD',
  'REQUIREMENTS_BRIEF',
];

function statusTone(status?: ReviewSession['status']): string {
  switch (status) {
    case 'COMPLETE':
      return 'bg-emerald-100 text-emerald-800';
    case 'IN_REVIEW':
      return 'bg-amber-100 text-amber-800';
    case 'READY_FOR_REVIEW':
      return 'bg-sky-100 text-sky-800';
    case 'GAP_ELICITATION':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-700';
  }
}

function asStageStatus(index: number, runningIndex: number, isComplete: boolean): StageStatus {
  if (isComplete) return 'complete';
  if (index < runningIndex) return 'complete';
  if (index === runningIndex) return 'running';
  return 'pending';
}

function initialSession(): ReviewSession {
  return {
    id: '',
    title: 'Untitled review',
    systemDescription: '',
    status: 'EVIDENCE_COLLECTION',
    gapRound: 0,
    gapsResolved: false,
    createdAt: '',
    updatedAt: '',
  };
}

export function LensReviewPage() {
  const token = useStore((state) => state.token);
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [session, setSession] = useState<ReviewSession>(initialSession());
  const [evidence, setEvidence] = useState<ArchitectureEvidence[]>([]);
  const [questions, setQuestions] = useState<GapQuestion[]>([]);
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [assessment, setAssessment] = useState<GapAssessmentResult | null>(null);
  const [assessmentMessage, setAssessmentMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [savingSession, setSavingSession] = useState(false);
  const [startingReview, setStartingReview] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [inReviewStageIndex, setInReviewStageIndex] = useState(0);
  const [createAttempt, setCreateAttempt] = useState(0);

  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceType, setEvidenceType] = useState<EvidenceType>('TEXT_DESCRIPTION');
  const [evidenceContent, setEvidenceContent] = useState('');
  const [sourceLabel, setSourceLabel] = useState('');
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftDescription, setDraftDescription] = useState('');

  const [answersDraft, setAnswersDraft] = useState<Record<string, string>>({});
  const [skipped, setSkipped] = useState<Record<string, boolean>>({});

  const creatingRef = useRef(false);

  useEffect(() => {
    if (!token) return;

    if (!sessionId || location.pathname.endsWith('/new')) {
      if (creatingRef.current) return;
      creatingRef.current = true;
      setLoading(true);
      setErrorMessage(null);
      void createReviewSession(token, 'Untitled review', '')
        .then((created) => {
          navigate(`/lens/sessions/${created.id}`, { replace: true });
        })
        .catch((error: unknown) => {
          setErrorMessage(error instanceof Error ? error.message : 'Failed to create the Lens review.');
          creatingRef.current = false;
        })
        .finally(() => setLoading(false));
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    void Promise.all([
      getReviewSession(token, sessionId),
      listEvidence(token, sessionId),
    ])
      .then(async ([loadedSession, loadedEvidence]) => {
        setSession(loadedSession);
        setDraftTitle(loadedSession.title);
        setDraftDescription(loadedSession.systemDescription ?? '');
        setEvidence(loadedEvidence);
        if (loadedSession.status === 'GAP_ELICITATION' || loadedSession.status === 'READY_FOR_REVIEW' || loadedSession.status === 'COMPLETE') {
          const existing = await listGapQuestions(token, sessionId);
          setQuestions(existing);
        }
        if (loadedSession.status === 'COMPLETE') {
          const loadedReport = await getReviewReport(token, sessionId);
          setReport(loadedReport);
        }
      })
      .catch((error: unknown) => {
        setErrorMessage(error instanceof Error ? error.message : 'Failed to load Lens session.');
      })
      .finally(() => setLoading(false));
  }, [createAttempt, location.pathname, navigate, sessionId, token]);

  const hasSessionEdits = useMemo(
    () => draftTitle.trim() !== session.title || draftDescription !== (session.systemDescription ?? ''),
    [draftDescription, draftTitle, session.systemDescription, session.title],
  );

  useEffect(() => {
    if (!token || !sessionId || session.status !== 'IN_REVIEW') return;

    const timer = window.setInterval(() => {
      setInReviewStageIndex((current) => (current < LENS_STAGE_NAMES.length - 1 ? current + 1 : current));
      void getReviewSession(token, sessionId)
        .then((latest) => {
          setSession(latest);
          if (latest.status === 'COMPLETE') {
            void getReviewReport(token, sessionId).then(setReport);
          }
        })
        .catch(() => {
          // Keep polling state; hard failures are surfaced by the review start call.
        });
    }, 3000);

    return () => window.clearInterval(timer);
  }, [session.status, sessionId, token]);

  const unresolvedCount = useMemo(
    () => questions.filter((question) => question.skipped || !question.answered || !question.answer).length,
    [questions],
  );

  const stageStates = useMemo(
    () => LENS_STAGE_NAMES.map((name, index) => ({
      name: name as never,
      status: asStageStatus(index, inReviewStageIndex, session.status === 'COMPLETE'),
    })) as StageState[],
    [inReviewStageIndex, session.status],
  );

  const statusMarkdown = useMemo(() => buildLensStatusMarkdown({
    session,
    evidence,
    questions,
    assessment,
  }), [assessment, evidence, questions, session]);

  const canGenerateQuestions = evidence.length > 0
    && (session.status === 'EVIDENCE_COLLECTION' || session.status === 'GAP_ELICITATION');

  const handleSaveSessionDetails = async () => {
    if (!token || !sessionId) return;
    if (!draftTitle.trim()) {
      setErrorMessage('Session title is required.');
      return;
    }
    setErrorMessage(null);
    setSaveMessage(null);
    setSavingSession(true);
    try {
      const updated = await updateReviewSession(token, sessionId, {
        title: draftTitle.trim(),
        systemDescription: draftDescription,
      });
      setSession(updated);
      setDraftTitle(updated.title);
      setDraftDescription(updated.systemDescription ?? '');
      setSaveMessage('Session details saved.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to save session details.');
    } finally {
      setSavingSession(false);
    }
  };

  const handleSubmitEvidence = async () => {
    if (!token || !sessionId) return;
    if (!evidenceContent.trim()) {
      setEvidenceError('Evidence content is required.');
      return;
    }

    try {
      setErrorMessage(null);
      setEvidenceError(null);
      setActiveAction('submit-evidence');
      const created = await submitEvidence(token, sessionId, {
        evidenceType,
        content: evidenceContent,
        sourceLabel: sourceLabel.trim() || null,
      });
      setEvidence((current) => [...current, created]);
      setEvidenceContent('');
      setSourceLabel('');
      setShowEvidenceModal(false);
      const latest = await getReviewSession(token, sessionId);
      setSession(latest);
    } catch (error) {
      setEvidenceError(error instanceof Error ? error.message : 'Failed to submit evidence.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleGenerateGaps = async () => {
    if (!token || !sessionId) return;
    setErrorMessage(null);
    setActiveAction('generate-gaps');
    try {
      const generated = await generateGapQuestions(token, sessionId);
      setQuestions(generated);
      const latest = await getReviewSession(token, sessionId);
      setSession(latest);
      setAssessment(null);
      setAssessmentMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to generate gap questions.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleSubmitAnswers = async () => {
    if (!token || !sessionId) return;
    setErrorMessage(null);
    setActiveAction('submit-answers');
    try {
      const updates = questions.map(async (question) => {
        const answer = answersDraft[question.id] ?? question.answer ?? '';
        const skip = skipped[question.id] === true;
        if (!skip && answer.trim().length === 0) return null;
        return answerGapQuestion(token, sessionId, question.id, skip ? '' : answer.trim(), skip);
      });

      await Promise.all(updates.filter((update): update is Promise<GapQuestion> => update !== null));
      setQuestions(await listGapQuestions(token, sessionId));
      setSaveMessage('Gap answers saved.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to submit gap answers.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleAssess = async () => {
    if (!token || !sessionId) return;
    setErrorMessage(null);
    setActiveAction('assess-gaps');
    try {
      const result = await assessGaps(token, sessionId);
      setAssessment(result);
      setAssessmentMessage(result.summary);
      const latest = await getReviewSession(token, sessionId);
      setSession(latest);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to assess gap resolution.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleProceed = async () => {
    if (!token || !sessionId) return;
    setErrorMessage(null);
    setActiveAction('proceed');
    try {
      await forceProceed(token, sessionId);
      const latest = await getReviewSession(token, sessionId);
      setSession(latest);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to proceed.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleDeleteEvidence = async (evidenceId: string) => {
    if (!token || !sessionId) return;
    setErrorMessage(null);
    setActiveAction(`delete-${evidenceId}`);
    try {
      await deleteEvidence(token, sessionId, evidenceId);
      setEvidence((current) => current.filter((item) => item.id !== evidenceId));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to delete evidence.');
    } finally {
      setActiveAction(null);
    }
  };

  const handleStartReview = async () => {
    if (!token || !sessionId) return;
    if (startingReview) return;
    setSession((current) => ({ ...current, status: 'IN_REVIEW' }));
    setInReviewStageIndex(0);
    setErrorMessage(null);
    setStartingReview(true);

    try {
      const completedReport = await startReview(token, sessionId);
      setReport(completedReport);
      const latest = await getReviewSession(token, sessionId);
      setSession(latest);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Review pipeline failed.');
      const latest = await getReviewSession(token, sessionId).catch(() => null);
      if (latest) setSession(latest);
    } finally {
      setStartingReview(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3 sm:p-4 lg:p-6" data-testid="lens-review-page">
      <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <PillarBadge pillar="lens" />
          <h1 className="mt-2 text-xl font-semibold text-gray-900">{session.title || 'Untitled review'}</h1>
          <p className="text-sm text-gray-600">Lens gap elicitation never blocks progress. Unresolved gaps become findings.</p>
          {sessionId && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-gray-600">
              <span className="min-w-0 truncate font-mono">Session {sessionId}</span>
              <CopyButton text={sessionId} label="Copy session ID" title="Copy Lens session ID" />
              <button
                type="button"
                className="rounded-md border border-gray-200 px-2 py-1 font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-gray-50"
                onClick={() => navigate(`/memoria?linkPillar=LENS&linkSessionId=${encodeURIComponent(sessionId)}`)}
              >
                Link to Memoria
              </button>
            </div>
          )}
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone(session.status)}`}>
          {session.status}
        </span>
      </div>

      {errorMessage && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
          {!sessionId && location.pathname.endsWith('/new') && (
            <button
              type="button"
              className="ml-3 rounded-md border border-red-300 px-2 py-1 font-semibold hover:bg-red-100"
              onClick={() => setCreateAttempt((current) => current + 1)}
              disabled={loading}
            >
              Retry creating review
            </button>
          )}
        </div>
      )}

      {saveMessage && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {saveMessage}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(20rem,0.8fr)]">
        <section className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4 sm:p-5">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Session title</label>
            <input
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
              disabled={!sessionId}
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">System description</label>
            <textarea
              className="mt-2 min-h-32 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm sm:min-h-40"
              value={draftDescription}
              onChange={(event) => setDraftDescription(event.target.value)}
              disabled={!sessionId}
            />
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
              onClick={() => void handleSaveSessionDetails()}
              disabled={!sessionId || !hasSessionEdits || savingSession}
            >
              {savingSession ? 'Saving...' : 'Save details'}
            </button>
          </div>

          <div className="space-y-2">
            <div className="space-y-2 xl:max-h-[32rem] xl:overflow-y-auto xl:pr-1">
              {evidence.map((item) => (
                <div key={item.id} className="rounded-xl border border-gray-200 p-3 text-sm">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-semibold">{item.evidenceType}</span>
                      <span className="text-xs text-gray-500">{item.sourceLabel || 'Unlabeled source'}</span>
                    </div>
                    <button
                      type="button"
                      className="self-start text-xs font-semibold text-red-600 sm:self-auto"
                      onClick={() => void handleDeleteEvidence(item.id)}
                      disabled={activeAction === `delete-${item.id}`}
                    >
                      {activeAction === `delete-${item.id}` ? 'Deleting…' : 'Delete'}
                    </button>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap break-words text-gray-700">{item.content}</p>
                </div>
              ))}
              {evidence.length === 0 && (
                <p className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
                  No evidence submitted yet.
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg bg-[var(--color-pillar-lens)] px-3 py-2 text-sm font-semibold text-white"
              onClick={() => {
                setEvidenceError(null);
                setShowEvidenceModal(true);
              }}
              disabled={!sessionId}
            >
              Add Evidence
            </button>
            <button
              type="button"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold"
              onClick={() => void handleGenerateGaps()}
              disabled={!canGenerateQuestions || activeAction !== null}
            >
              {activeAction === 'generate-gaps' ? 'Generating…' : 'Generate gap questions'}
            </button>
          </div>
        </section>

        {evidence.length > 0 && (
        <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-gray-900">Gap elicitation</h2>
            <span className="text-xs text-gray-500">Round {Math.max(session.gapRound, 1)} of 5</span>
          </div>

          {session.gapRound >= 5 && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Final round. Remaining gaps will become insufficient-information findings.
            </p>
          )}

          {session.status === 'GAP_ELICITATION' && questions.length > 0 && (
            <div className="space-y-3 xl:max-h-[32rem] xl:overflow-y-auto xl:pr-1">
              {questions.map((question) => (
                <div key={question.id} className="rounded-xl border border-gray-200 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-orange-50 px-2 py-1 text-xs font-semibold text-orange-700">{question.category}</span>
                    <button
                      type="button"
                      className="text-xs font-semibold text-[var(--color-pillar-lens)]"
                      onClick={() => setSkipped((current) => ({ ...current, [question.id]: !current[question.id] }))}
                    >
                      {skipped[question.id] ? 'Unskip' : 'Skip'}
                    </button>
                  </div>
                  <p className="mt-2 font-medium text-gray-800">{question.question}</p>
                  <details className="mt-2 text-xs text-gray-500">
                    <summary className="cursor-pointer font-semibold">Rationale</summary>
                    <p className="mt-1">{question.rationale || 'No rationale provided.'}</p>
                  </details>
                  <textarea
                    className="mt-2 min-h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    value={answersDraft[question.id] ?? question.answer ?? ''}
                    onChange={(event) => setAnswersDraft((current) => ({ ...current, [question.id]: event.target.value }))}
                    placeholder="Answer this question or skip it."
                    disabled={skipped[question.id]}
                  />
                </div>
              ))}
            </div>
          )}

          {assessmentMessage && (
            <div className={`rounded-xl p-3 text-sm ${assessment?.resolved ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>
              <p>{assessmentMessage}</p>
              {assessment && (
                <dl className="mt-2 grid gap-2 text-xs sm:grid-cols-3">
                  <div><dt className="font-semibold">resolved</dt><dd>{String(assessment.resolved)}</dd></div>
                  <div><dt className="font-semibold">canProceed</dt><dd>{String(assessment.canProceed)}</dd></div>
                  <div><dt className="font-semibold">remainingCount</dt><dd>{assessment.remainingCount}</dd></div>
                </dl>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold"
              onClick={() => void handleSubmitAnswers()}
              disabled={questions.length === 0 || activeAction !== null}
            >
              {activeAction === 'submit-answers' ? 'Submitting…' : 'Submit answers'}
            </button>
            <button
              type="button"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold"
              onClick={() => void handleAssess()}
              disabled={questions.length === 0 || activeAction !== null}
            >
              {activeAction === 'assess-gaps' ? 'Assessing…' : 'Assess gaps'}
            </button>
            <button
              type="button"
              className="text-sm font-semibold text-[var(--color-pillar-lens)]"
              onClick={() => void handleProceed()}
              disabled={questions.length === 0 || activeAction !== null}
            >
              {activeAction === 'proceed' ? 'Proceeding…' : 'Proceed anyway'}
            </button>
          </div>
        </section>
        )}

      </div>

      <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-gray-900">Status and report</h2>
            <MarkdownExportActions
              markdown={statusMarkdown}
              markdownFilename={lensStatusMarkdownFilename(session)}
              copyButtonTitle="Copy Lens status as Markdown"
            />
          </div>
          {loading && <p className="text-sm text-gray-600">Loading session…</p>}

          {session.status === 'READY_FOR_REVIEW' && (
            <div className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
              <p>Evidence items: <strong>{evidence.length}</strong></p>
              <p>Unresolved gaps becoming findings: <strong>{unresolvedCount}</strong></p>
              <button
                type="button"
                className="w-full rounded-xl bg-[var(--color-pillar-lens)] px-4 py-3 text-sm font-semibold text-white"
                onClick={() => void handleStartReview()}
                disabled={startingReview}
              >
                {startingReview ? 'Review running...' : 'Start review'}
              </button>
            </div>
          )}

          {session.status === 'IN_REVIEW' && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600">Review pipeline is running. Status refreshes every 3 seconds.</p>
              <StageProgress stages={stageStates} stageNames={LENS_STAGE_NAMES} />
            </div>
          )}

          {session.status === 'COMPLETE' && report && <ReviewReportView report={report} />}

          {session.status !== 'COMPLETE' && (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
              The completed report appears here after review finalization.
            </div>
          )}
      </section>

      {showEvidenceModal && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-2xl space-y-3 rounded-2xl bg-white p-4 shadow-xl">
            <h2 className="text-base font-semibold text-gray-900">Add evidence</h2>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={evidenceType}
              onChange={(event) => setEvidenceType(event.target.value as EvidenceType)}
            >
              {EVIDENCE_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
            <textarea
              className="min-h-48 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={evidenceContent}
              onChange={(event) => setEvidenceContent(event.target.value)}
              placeholder="Paste architecture evidence here (minimum 50 characters)."
            />
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={sourceLabel}
              onChange={(event) => setSourceLabel(event.target.value)}
              placeholder="Source label (optional)"
            />
            {evidenceError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {evidenceError}
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold"
                onClick={() => setShowEvidenceModal(false)}
                disabled={activeAction === 'submit-evidence'}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-[var(--color-pillar-lens)] px-3 py-2 text-sm font-semibold text-white"
                onClick={() => void handleSubmitEvidence()}
                disabled={activeAction === 'submit-evidence'}
              >
                {activeAction === 'submit-evidence' ? 'Submitting…' : 'Submit evidence'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
