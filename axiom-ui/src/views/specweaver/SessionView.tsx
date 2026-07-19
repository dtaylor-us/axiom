import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useStore } from '../../store/useStore';
import { useSpecWeaverStore } from '../../store/useSpecWeaverStore';
import type { DocumentType, SessionDocument } from '../../api/specweaver';
import { downloadPackageExport } from './packageExport';
import { CopyButton } from '../../components/CopyButton';
import { PillarBadge } from '../../components/PillarBadge';

const TEXT_DOCUMENT_TYPES: DocumentType[] = ['PLAIN_TEXT', 'MARKDOWN', 'EMAIL'];
const FILE_DOCUMENT_TYPES: DocumentType[] = ['PDF', 'DOCX'];

function detectDocumentType(file: File | null): DocumentType {
  if (!file) return 'PLAIN_TEXT';
  const name = file.name.toLowerCase();
  if (name.endsWith('.pdf')) return 'PDF';
  if (name.endsWith('.docx')) return 'DOCX';
  return 'PLAIN_TEXT';
}

function documentName(document: SessionDocument): string {
  return document.filename ?? document.sourceLabel ?? 'Untitled document';
}

function statusClass(status: SessionDocument['status']): string {
  if (status === 'EXTRACTED') return 'bg-accent/10 text-accent ring-accent/20';
  if (status === 'FAILED') return 'bg-red-50 text-red-700 ring-red-100';
  if (status === 'PROCESSING') return 'bg-amber-50 text-amber-700 ring-amber-200';
  return 'bg-gray-50 text-gray-600 ring-gray-200';
}

function stageLabel(name: string): string {
  if (name === 'extraction') return 'Extraction';
  if (name === 'classification') return 'Classification';
  return 'Output formatting';
}

function stageBulletClass(status: 'pending' | 'running' | 'complete' | 'error'): string {
  if (status === 'complete') return 'bg-emerald-500 ring-emerald-100';
  if (status === 'running') return 'bg-accent ring-accent/20';
  if (status === 'error') return 'bg-red-500 ring-red-100';
  return 'bg-gray-300 ring-gray-100';
}

function stageTextClass(status: 'pending' | 'running' | 'complete' | 'error'): string {
  if (status === 'complete') return 'text-emerald-700';
  if (status === 'running') return 'text-gray-900';
  if (status === 'error') return 'text-red-700';
  return 'text-gray-500';
}

function stageStatusLabel(status: 'pending' | 'running' | 'complete' | 'error'): string {
  if (status === 'complete') return 'Complete';
  if (status === 'running') return 'Running';
  if (status === 'error') return 'Error';
  return 'Pending';
}

/**
 * Main SpecWeaver workspace for uploading evidence and generating a package.
 */
export function SessionView() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const token = useStore((state) => state.token)!;
  const currentSession = useSpecWeaverStore((state) => state.currentSession);
  const currentPackage = useSpecWeaverStore((state) => state.currentPackage);
  const error = useSpecWeaverStore((state) => state.error);
  const isGenerating = useSpecWeaverStore((state) => state.isGenerating);
  const generationStages = useSpecWeaverStore((state) => state.generationStages);
  const isSending = useSpecWeaverStore((state) => state.isSending);
  const loadSession = useSpecWeaverStore((state) => state.loadSession);
  const uploadDocument = useSpecWeaverStore((state) => state.uploadDocument);
  const deleteDocument = useSpecWeaverStore((state) => state.deleteDocument);
  const generatePackage = useSpecWeaverStore((state) => state.generatePackage);
  const sendToArchon = useSpecWeaverStore((state) => state.sendToArchon);
  const updateSessionTitle = useSpecWeaverStore((state) => state.updateSessionTitle);
  const clearError = useSpecWeaverStore((state) => state.clearError);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [sourceLabel, setSourceLabel] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('PLAIN_TEXT');
  const [isUploading, setIsUploading] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const sessionDocuments = currentSession?.documents ?? [];

  useEffect(() => {
    document.title = 'SpecWeaver — Requirements Intelligence | Axiom';
  }, []);

  useEffect(() => {
    if (sessionId) void loadSession(token, sessionId);
  }, [loadSession, sessionId, token]);

  useEffect(() => {
    setTitleDraft(currentSession?.title ?? '');
  }, [currentSession?.id, currentSession?.title]);

  const hasExtractedDocument = useMemo(
    () => sessionDocuments.some((document) => document.status === 'EXTRACTED'),
    [sessionDocuments],
  );

  const confidenceCounts = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0, INFERRED: 0 };
    currentPackage?.requirements.forEach((requirement) => {
      counts[requirement.confidence] += 1;
    });
    return counts;
  }, [currentPackage?.requirements]);

  const isOwnershipError =
    error === 'You do not have access to this SpecWeaver session.'
    || error === 'You cannot edit this session title because it belongs to another user.';

  if (!sessionId) {
    return <div className="p-6 text-[13px] text-gray-500">Session not found.</div>;
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setDocumentType(detectDocumentType(nextFile));
  };

  const handleAddDocument = async () => {
    if (!file && !text.trim()) return;
    setIsUploading(true);
    try {
      await uploadDocument(token, sessionId, file, text.trim() || null, documentType, sourceLabel.trim() || undefined);
      setFile(null);
      setText('');
      setSourceLabel('');
      setDocumentType('PLAIN_TEXT');
    } finally {
      setIsUploading(false);
    }
  };

  const handleGeneratePackage = async () => {
    await generatePackage(token, sessionId);
  };

  const handlePersistTitle = async () => {
    if (!currentSession) {
      return;
    }
    const normalizedDraft = titleDraft.trim();
    const normalizedCurrent = (currentSession.title ?? '').trim();
    if (normalizedDraft === normalizedCurrent) {
      return;
    }

    setIsSavingTitle(true);
    try {
      const updatedSession = await updateSessionTitle(token, sessionId, normalizedDraft || null);
      setTitleDraft(updatedSession.title ?? '');
    } catch {
      // Store-level action already captures and exposes a user-facing error.
      // Swallow here to avoid unhandled promise rejections from blur/enter handlers.
      setTitleDraft(currentSession.title ?? '');
    } finally {
      setIsSavingTitle(false);
    }
  };

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

  const renderDocument = (document: SessionDocument) => (
    <div key={document.id} className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-medium text-gray-900">{documentName(document)}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
              {document.documentType}
            </span>
            <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ring-1 ${statusClass(document.status)}`}>
              {document.status}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void deleteDocument(token, sessionId, document.id)}
          className="rounded p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-600"
          aria-label={`Delete ${documentName(document)}`}
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 4h12M6 4V2h4v2m-6 0l.7 10h6.6L12 4" />
          </svg>
        </button>
      </div>
      {document.extractedText && (
        <details className="mt-3">
          <summary className="cursor-pointer text-[11px] font-medium text-gray-500">Extracted text preview</summary>
          <p className="mt-2 max-h-32 overflow-y-auto rounded bg-gray-50 p-2 text-[12px] text-gray-600">
            {document.extractedText}
          </p>
        </details>
      )}
    </div>
  );

  return (
    <div className="specweaver-scope h-full overflow-hidden bg-gray-50" data-testid="specweaver-session-view">
      <div className="flex h-full flex-col lg:flex-row">
        <section className="flex min-h-0 flex-1 flex-col border-gray-200 bg-white lg:border-r">
          <div className="shrink-0 border-b border-gray-200 px-4 py-3">
            <div className="mb-2 flex items-center gap-2">
              <PillarBadge pillar="specweaver" size="sm" />
              <span className="text-[12px] font-medium text-gray-500">Session</span>
            </div>
            <input
              value={titleDraft}
              onChange={(event) => setTitleDraft(event.target.value)}
              onBlur={() => void handlePersistTitle()}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  void handlePersistTitle();
                  event.currentTarget.blur();
                }
              }}
              placeholder="Untitled session"
              className="w-full rounded-lg border border-transparent px-2 py-1 text-[18px] font-semibold text-gray-900 outline-none focus:border-gray-200 focus:ring-2 focus:ring-accent/30"
              aria-label="Session title"
            />
            <p className="px-2 text-[11px] text-gray-400">
              {isSavingTitle ? 'Saving title…' : 'Title saves automatically when you leave the field.'}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-[11px] text-gray-600">
              <span className="min-w-0 truncate font-mono">Session {sessionId}</span>
              <CopyButton text={sessionId} label="Copy session ID" title="Copy SpecWeaver session ID" />
              <button
                type="button"
                className="rounded-md border border-gray-200 bg-white px-2 py-1 font-semibold text-[var(--color-pillar-memoria-text)] hover:bg-gray-50"
                onClick={() => navigate(`/memoria?linkPillar=SPECWEAVER&linkSessionId=${encodeURIComponent(sessionId)}`)}
              >
                Link to Memoria
              </button>
            </div>
          </div>

          {error && (
            <div className="border-b border-red-100 bg-red-50 px-4 py-2 text-[12px] text-red-700" role="alert">
              <span>{error}</span>
              {isOwnershipError && (
                <button
                  type="button"
                  className="ml-2 underline"
                  onClick={() => navigate('/specweaver')}
                >
                  Back to sessions
                </button>
              )}
              <button type="button" className="ml-2 underline" onClick={clearError}>
                Dismiss
              </button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <h2 className="text-[13px] font-semibold text-gray-900">Add Evidence</h2>
                <label className="mt-3 flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-white px-3 py-6 text-center hover:bg-gray-50">
                  <svg className="mb-2 h-5 w-5 text-gray-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                    <path d="M8 11V3m0 0L5 6m3-3l3 3M3 13h10" />
                  </svg>
                  <span className="text-[12px] font-medium text-gray-700">
                    {file ? file.name : 'Drop or choose PDF / DOCX'}
                  </span>
                  <input className="sr-only" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={handleFileChange} />
                </label>

                <label className="mt-3 block text-[12px] font-medium text-gray-700" htmlFor="specweaver-text">
                  Text evidence
                </label>
                <textarea
                  id="specweaver-text"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  rows={8}
                  placeholder="Paste meeting notes, markdown, or email content"
                  className="mt-1 w-full resize-none rounded-lg border border-gray-200 px-3 py-2 text-[13px] text-gray-800 outline-none focus:ring-2 focus:ring-accent/30"
                />

                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="block text-[12px] font-medium text-gray-700">
                    Source label
                    <input
                      value={sourceLabel}
                      onChange={(event) => setSourceLabel(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent/30"
                      placeholder="Q3 workshop notes"
                    />
                  </label>
                  <label className="block text-[12px] font-medium text-gray-700">
                    Document type
                    <select
                      value={documentType}
                      onChange={(event) => setDocumentType(event.target.value as DocumentType)}
                      className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent/30"
                    >
                      {[...TEXT_DOCUMENT_TYPES, ...FILE_DOCUMENT_TYPES].map((type) => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <button
                  type="button"
                  onClick={handleAddDocument}
                  disabled={isUploading || (!file && !text.trim())}
                  className="mt-4 w-full rounded-lg bg-accent px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                >
                  {isUploading ? 'Adding…' : 'Add Document'}
                </button>
              </div>

              <div>
                <h2 className="mb-3 text-[13px] font-semibold text-gray-900">Uploaded Documents</h2>
                {sessionDocuments.length ? (
                  <div className="space-y-3">{sessionDocuments.map(renderDocument)}</div>
                ) : (
                  <div className="rounded-lg border border-dashed border-gray-200 bg-white p-6 text-center text-[12px] text-gray-500">
                    No documents added yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        <aside className="flex min-h-0 flex-col bg-gray-50 lg:w-[420px]">
          <div className="border-b border-gray-200 bg-white px-4 py-3">
            <h2 className="text-[14px] font-semibold text-gray-900">Package Generation</h2>
            <p className="mt-1 text-[12px] text-gray-500">Generate the typed ArchInputPackage after extraction completes.</p>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {!hasExtractedDocument ? (
              <p className="rounded-lg border border-gray-200 bg-white p-4 text-[12px] text-gray-500">
                Package generation unlocks after at least one document is extracted.
              </p>
            ) : (
              <button
                type="button"
                onClick={handleGeneratePackage}
                disabled={isGenerating}
                className="w-full rounded-lg bg-accent px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
              >
                {isGenerating ? 'Generating package…' : 'Generate Package'}
              </button>
            )}

            {isGenerating && (
              <div className="mt-4 rounded-lg border border-gray-200 bg-white p-3">
                <div className="mb-3 flex items-center gap-2 text-[12px] text-gray-600">
                  <svg className="h-4 w-4 animate-spin text-accent" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                    <path d="M8 2a6 6 0 016 6" />
                  </svg>
                  Polling every 5 seconds until the package is ready.
                </div>
                <ol className="space-y-2" aria-label="SpecWeaver generation stages">
                  {generationStages.map((stage) => (
                    <li key={stage.name} className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className={`inline-block h-2.5 w-2.5 rounded-full ring-4 ${stageBulletClass(stage.status)}`}
                          aria-hidden="true"
                        />
                        <span className={`text-[12px] font-medium ${stageTextClass(stage.status)}`}>
                          {stageLabel(stage.name)}
                        </span>
                      </div>
                      <span className={`text-[11px] font-medium ${stageTextClass(stage.status)}`}>
                        {stageStatusLabel(stage.status)}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {currentPackage && (
              <div className="mt-4 space-y-4">
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-[20px] font-semibold text-gray-900">{currentPackage.totalRequirements}</p>
                      <p className="text-[10px] uppercase tracking-wide text-gray-400">Total</p>
                    </div>
                    <div>
                      <p className="text-[20px] font-semibold text-gray-900">{currentPackage.highConfidenceCount}</p>
                      <p className="text-[10px] uppercase tracking-wide text-gray-400">High</p>
                    </div>
                    <div>
                      <p className="text-[20px] font-semibold text-gray-900">{currentPackage.inferredCount}</p>
                      <p className="text-[10px] uppercase tracking-wide text-gray-400">Inferred</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {Object.entries(confidenceCounts).map(([label, count]) => (
                      <span key={label} className="rounded bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600">
                        {label}: {count}
                      </span>
                    ))}
                  </div>
                  <p className="mt-4 text-[12px] leading-relaxed text-gray-600">{currentPackage.systemDescription}</p>
                </div>

                <Link
                  to={`/specweaver/sessions/${sessionId}/package`}
                  className="block rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-center text-[13px] font-medium text-gray-700 hover:bg-gray-50"
                >
                  View package details
                </Link>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => downloadPackageExport(currentPackage, 'markdown')}
                    className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-[13px] font-medium text-gray-700 transition-colors hover:bg-gray-50"
                  >
                    Export as Markdown
                  </button>
                  <button
                    type="button"
                    onClick={() => downloadPackageExport(currentPackage, 'text')}
                    className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-[13px] font-medium text-gray-700 transition-colors hover:bg-gray-50"
                  >
                    Export as Text
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleSendToArchon}
                  disabled={isSending}
                  className="w-full rounded-lg bg-accent px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                >
                  {isSending ? 'Preparing brief…' : 'Open in Archon →'}
                </button>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
