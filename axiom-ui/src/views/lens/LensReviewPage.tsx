import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  assessGaps,
  createReviewSession,
  deleteEvidence,
  forceProceed,
  generateGapQuestions,
  getReviewReport,
  getReviewSession,
  listEvidence,
  submitEvidence,
  type ArchitectureEvidence,
  type GapQuestion,
  type ReviewReport,
  type ReviewSession,
} from '../../api/lens';
import { PillarBadge } from '../../components/PillarBadge';
import { StageProgress } from '../../components/StageProgress';
import { useStore } from '../../store/useStore';
import { ReviewReport as ReviewReportView } from '../../components/lens/ReviewReport';
import type { StageState } from '../../types/api';

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

function statusTone(status?: ReviewSession['status']): string {
  switch (status) {
    case 'COMPLETE': return 'bg-emerald-100 text-emerald-800';
    case 'IN_REVIEW': return 'bg-amber-100 text-amber-800';
    case 'READY_FOR_REVIEW': return 'bg-sky-100 text-sky-800';
    case 'GAP_ELICITATION': return 'bg-orange-100 text-orange-800';
    default: return 'bg-gray-100 text-gray-700';
  }
}

function defaultReviewSession(): ReviewSession {
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
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const token = useStore((state) => state.token);
  const [session, setSession] = useState<ReviewSession>(defaultReviewSession());
  const [evidence, setEvidence] = useState<ArchitectureEvidence[]>([]);
  const [questions, setQuestions] = useState<GapQuestion[]>([]);
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftDescription, setDraftDescription] = useState('');
  const [showEvidenceForm, setShowEvidenceForm] = useState(false);
  const [evidenceType, setEvidenceType] = useState<ArchitectureEvidence['evidenceType']>('TEXT_DESCRIPTION');
  const [evidenceContent, setEvidenceContent] = useState('');
  const [sourceLabel, setSourceLabel] = useState('');
  const [gapAssessment, setGapAssessment] = useState<string | null>(null);
  const creatingRef = useRef(false);

  useEffect(() => {
    if (!token) return;
    if (!sessionId || location.pathname.endsWith('/new')) {
      if (creatingRef.current) return;
      creatingRef.current = true;
      void createReviewSession(token, 'Untitled review', '').then((created) => {
        navigate(`/lens/sessions/${created.id}`, { replace: true });
      });
      return;
    }

    setLoading(true);
    void Promise.all([
      getReviewSession(token, sessionId),
      listEvidence(token, sessionId),
    ])
      .then(([currentSession, currentEvidence]) => {
        setSession(currentSession);
        setDraftTitle(currentSession.title);
        setDraftDescription(currentSession.systemDescription);
        setEvidence(currentEvidence);
        if (currentSession.status === 'COMPLETE') {
          void getReviewReport(token, sessionId).then(setReport).catch(() => setReport(null));
        }
      })
      .finally(() => setLoading(false));
  }, [location.pathname, navigate, sessionId, token]);

  const stageStates = useMemo<StageState[]>(() => LENS_STAGE_NAMES.map((name, index) => ({
    name: name as StageState['name'],
    status: index < 3 && session.status === 'IN_REVIEW' ? 'complete' : index === 3 && session.status === 'IN_REVIEW' ? 'running' : 'pending',
  })), [session.status]);

  const handleAddEvidence = async () => {
    if (!token || !sessionId) return;
    const created = await submitEvidence(token, sessionId, { evidenceType, content: evidenceContent, sourceLabel: sourceLabel || null });
    setEvidence((current) => [...current, created]);
    setEvidenceContent('');
    setSourceLabel('');
    setShowEvidenceForm(false);
  };

  const handleGenerateQuestions = async () => {
    if (!token || !sessionId) return;
    const generated = await generateGapQuestions(token, sessionId);
    setQuestions(generated);
    setSession((current) => ({ ...current, status: 'GAP_ELICITATION', gapRound: current.gapRound + 1 }));
  };

  const handleAssess = async () => {
    if (!token || !sessionId) return;
    const result = await assessGaps(token, sessionId);
    setGapAssessment(result.summary);
    if (result.canProceed) {
      setSession((current) => ({ ...current, status: 'READY_FOR_REVIEW' }));
    }
  };

  const handleProceed = async () => {
    if (!token || !sessionId) return;
    const updated = await forceProceed(token, sessionId);
    setSession(updated);
  };

  const handleStartReview = () => {
    setSession((current) => ({ ...current, status: 'IN_REVIEW' }));
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4" data-testid="lens-review-page">
      <div className="flex items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white p-4">
        <div>
          <PillarBadge pillar="lens" />
          <h1 className="mt-2 text-xl font-semibold text-gray-900">{draftTitle || 'Untitled review'}</h1>
          <p className="text-sm text-gray-600">Lens is evidence-first. Gaps become findings, not blockers.</p>
        </div>
        <div className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone(session.status)}`}>{session.status}</div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr_1fr]">
        <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Session title</label>
            <input className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">System description</label>
            <textarea className="mt-2 min-h-40 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" value={draftDescription} onChange={(event) => setDraftDescription(event.target.value)} />
          </div>
          <div className="space-y-2">
            {evidence.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-200 p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-semibold">{item.evidenceType}</span>
                  <button type="button" className="text-xs text-red-600" onClick={() => deleteEvidence(token ?? '', sessionId ?? '', item.id).then(() => setEvidence((current) => current.filter((entry) => entry.id !== item.id)))}>
                    Delete
                  </button>
                </div>
                <p className="mt-2 text-gray-700 whitespace-pre-wrap">{item.content}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="rounded-lg bg-[var(--color-pillar-lens)] px-3 py-2 text-sm font-semibold text-white" onClick={() => setShowEvidenceForm((current) => !current)}>
              Add evidence
            </button>
            <button type="button" className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold" onClick={handleGenerateQuestions} disabled={!evidence.length}>
              Generate gap questions
            </button>
          </div>
          {showEvidenceForm && (
            <div className="space-y-2 rounded-xl border border-gray-200 bg-gray-50 p-3">
              <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" value={evidenceType} onChange={(event) => setEvidenceType(event.target.value as ArchitectureEvidence['evidenceType'])}>
                {['TEXT_DESCRIPTION', 'ADL_CONTENT', 'DIAGRAM_DESCRIPTION', 'DECISION_RECORD', 'REQUIREMENTS_BRIEF'].map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
              <textarea className="min-h-32 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" value={evidenceContent} onChange={(event) => setEvidenceContent(event.target.value)} />
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Source label" value={sourceLabel} onChange={(event) => setSourceLabel(event.target.value)} />
              <button type="button" className="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white" onClick={handleAddEvidence}>Submit evidence</button>
            </div>
          )}
        </section>

        <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-gray-900">Gap elicitation</h2>
            <span className="text-xs text-gray-500">Round {session.gapRound || 0} of 5</span>
          </div>
          {questions.map((question) => (
            <div key={question.id} className="rounded-xl border border-gray-200 p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-orange-50 px-2 py-1 text-xs font-semibold text-orange-700">{question.category}</span>
                <span className="text-xs text-gray-500">{question.answered ? 'Answered' : question.skipped ? 'Skipped' : 'Open'}</span>
              </div>
              <p className="mt-2 font-medium text-gray-800">{question.question}</p>
              <p className="mt-1 text-xs text-gray-500">{question.rationale}</p>
            </div>
          ))}
          {gapAssessment && <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{gapAssessment}</p>}
          <button type="button" className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold" onClick={handleAssess}>
            Assess gaps
          </button>
          <button type="button" className="text-sm font-semibold text-[var(--color-pillar-lens)]" onClick={handleProceed}>
            Proceed anyway
          </button>
        </section>

        <section className="space-y-3 rounded-2xl border border-gray-200 bg-white p-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Status</h2>
            <p className="mt-1 text-sm text-gray-600">{loading ? 'Loading review session...' : session.systemDescription || 'No description yet.'}</p>
          </div>
          {session.status === 'READY_FOR_REVIEW' && (
            <button type="button" className="rounded-xl bg-[var(--color-pillar-lens)] px-4 py-3 text-sm font-semibold text-white" onClick={handleStartReview}>
              Start review
            </button>
          )}
          {session.status === 'IN_REVIEW' && <StageProgress stages={stageStates} stageNames={LENS_STAGE_NAMES} />}
          {session.status === 'COMPLETE' && report && <ReviewReportView report={report} />}
          {session.status !== 'COMPLETE' && (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-600">
              When the review completes, the final report will appear here.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
