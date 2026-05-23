import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useConversation } from '../hooks/useConversation';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { useStore } from '../store/useStore';

const EXAMPLES: { label: string; prompt: string }[] = [
  {
    label: 'SaaS billing + entitlements',
    prompt:
      'Design a multi-tenant SaaS billing, entitlements, and usage metering platform.\n\nContext:\n- We sell a B2B SaaS product with per-seat + usage add-ons.\n- Tenants are organizations; users belong to one org.\n- We need strong auditability, compliance posture, and clear governance rules.\n\nFunctional requirements:\n- Subscription lifecycle: trial → active → past_due → canceled; upgrade/downgrade with proration\n- Plans: Free, Pro, Enterprise; feature flags + quota limits per plan\n- Entitlements service: low-latency “can user do X?” checks used on every API request\n- Usage metering: ingest events from product services; compute billable usage daily + monthly\n- Invoicing: invoices, credit notes, taxes/VAT, multi-currency support\n- Payments: integrate with a payment provider (e.g., Stripe) and handle asynchronous webhooks\n- Idempotency: webhook + usage ingestion must be idempotent and replay-safe\n- Admin portal: view tenant billing status, invoices, usage trends, entitlements, audit log\n\nKey scenarios:\n1) “API call gating”: user makes an API call that consumes quota; entitlement check must be fast and consistent.\n2) “Webhook storm”: payment provider retries webhooks; we must not double-charge or duplicate state transitions.\n3) “Enterprise upgrade”: tenant upgrades mid-cycle; proration + entitlement changes should be near-real-time.\n4) “Dispute/chargeback”: payment reversed; access should degrade gracefully with clear comms.\n\nNon-functional requirements:\n- Latency: entitlement checks < 50ms p95, < 120ms p99 (global)\n- Throughput: 2k usage events/sec sustained, 10k/sec bursts; 500 entitlement checks/sec per tenant peak\n- Availability: 99.95% for entitlements; billing workflows may be eventually consistent\n- Consistency: no double-billing; invoice state transitions must be correct under retries\n- Security: SSO (OIDC/SAML), RBAC (admin/billing-viewer), audit log immutable, PII minimization\n- Compliance: SOC2-friendly logging, data retention 7 years for invoices/audit\n\nConstraints / preferences:\n- Prefer managed services where appropriate, but minimize deep lock-in\n- Data residency: EU and US; tenant pinned to a region\n- Avoid storing full card details; keep PCI scope minimal\n\nGovernance expectations:\n- Produce Mark Richards ADL with executable rules (ArchUnit/PyTestArch/Semgrep)\n- Include FMEA with RPN scoring for payment + entitlement paths\n- Buy vs build analysis naming real providers (tax, billing, metering, auth)\n- Architecture review should challenge assumptions around consistency and retry handling',
  },
  {
    label: 'Real-time collaboration',
    prompt:
      'Design a real-time collaborative document editor with offline support and enterprise governance.\n\nFunctional requirements:\n- Document model supports rich text + embedded blocks (tables, code blocks, images)\n- Concurrent editing with presence (cursors/selection) and per-block locking option\n- Conflict resolution: choose OT or CRDT (justify), including how you handle large docs\n- Offline mode: edits queue locally and reconcile on reconnect; conflict UX must be defined\n- Comments + mentions + notifications\n- Version history: named versions, diff view, restore; export PDF/Markdown\n- Access control: per-doc RBAC, share links with expiration, external guest access optional\n\nKey scenarios:\n1) “Global co-edit”: 30 users edit the same doc from 3 regions; propagation and merge must stay responsive.\n2) “Offline travel”: user edits offline for 2 hours, reconnects, merges with ongoing edits.\n3) “Compliance request”: export audit log and version history for a specific document.\n4) “Incident”: collaboration backend partially fails; define graceful degradation (read-only, delayed presence, etc).\n\nNon-functional requirements:\n- Latency: edit propagation < 200ms p95 within region, < 450ms p95 cross-region\n- Concurrency: 50k concurrent users; 5k active docs; 100 users per hot doc worst case\n- Availability: 99.9%; must survive single-node failures without losing edits\n- Durability: never lose acknowledged edits; must support replay and recovery after crash\n- Security: SSO (OIDC/SAML), SCIM provisioning, encryption at rest + in transit\n- Data residency: EU and US with strict tenant pinning; cross-region replication strategy defined\n- Observability: per-doc metrics (edit rate, merge conflicts), tracing for edit pipeline\n\nConstraints / preferences:\n- Prefer WebSocket for realtime transport, but explain fallback strategy\n- Avoid exotic databases unless justified; operational simplicity matters\n\nGovernance expectations:\n- Produce ADL rules for service boundaries, data residency, and audit immutability\n- Include FMEA with cascading failures across realtime transport, persistence, and merge logic\n- Trade-off record must explicitly address consistency vs latency vs UX',
  },
  {
    label: 'Event-driven order platform',
    prompt:
      'Design an event-driven order management and fulfillment platform for an e-commerce marketplace.\n\nFunctional requirements:\n- Order lifecycle: cart → checkout → order_created → payment_authorized → inventory_reserved → shipped → delivered → returns/refunds\n- Payments: integrate with a provider; ensure PCI scope minimization\n- Inventory: multi-warehouse; reservation TTL; oversell prevention strategy\n- Shipping: carrier integrations; label generation; tracking updates; SLA tracking\n- Customer comms: email/SMS notifications with templates and localization\n- Search: product search with near-real-time indexing; catalog updates\n- Fraud: basic risk scoring; manual review queue\n\nKey scenarios:\n1) “Flash sale”: 10k orders/min peak for 15 minutes; inventory correctness + checkout reliability are critical.\n2) “Partial failure”: payment succeeds but inventory reservation times out; define compensation and customer messaging.\n3) “Replay”: we must rebuild read models from an event log after a bug; define replay + idempotency strategy.\n4) “Return abuse”: high return rates; risk controls and reporting.\n\nNon-functional requirements:\n- Availability: 99.95% for checkout; other domains may degrade gracefully\n- Consistency: effectively-once processing for payment/inventory events; no double captures\n- Latency: checkout request < 400ms p95 excluding payment provider latency\n- Data: 1M SKUs; catalog updates 50k/day; 5M registered users\n- Security: least privilege, secrets management, PII separation\n- Compliance: audit trail for financial events and refunds; retention 7 years\n\nConstraints / preferences:\n- Zero-downtime deployments\n- Prefer asynchronous integration via events; avoid synchronous service-to-service chains where possible\n- Team: 8 engineers; ops maturity medium; keep operational complexity reasonable\n\nGovernance expectations:\n- Style selection must be evidence-based with veto rules\n- Tactics must be named (Bass/Clements/Kazman) and mapped to quality attributes\n- Buy vs build should name real options for messaging, search, payments, notifications\n- ADL rules must prevent direct DB coupling and enforce event schema/versioning discipline\n- FMEA should identify cascading failure paths across payment, inventory, shipping, comms',
  },
  {
    label: 'Streaming media pipeline',
    prompt:
      'Design a streaming media platform with an ingest → transcode → package → publish pipeline.\n\nFunctional requirements:\n- Creator uploads source video; system validates, stores, and triggers transcoding\n- Transcoding: multi-bitrate ladder generation; thumbnails; captions\n- DRM integration; tokenized playback URLs; geo-restrictions\n- CDN distribution with cache invalidation strategy\n- Playback: adaptive bitrate; session tracking\n- Analytics: QoE metrics (startup time, buffering ratio), per-title dashboards\n- Content moderation workflow: manual review + automated checks (basic)\n\nKey scenarios:\n1) “Ingest spike”: 5k uploads/hour; transcoding backlog must be controlled with priority rules.\n2) “Regional outage”: control plane region fails; publishing + playback should degrade predictably.\n3) “Hot title”: 100k concurrent streams; CDN hit ratio and origin protection are critical.\n4) “DRM failure”: DRM provider outage; define fallback policy and customer impact.\n\nNon-functional requirements:\n- Scale: 5M MAU, 100k concurrent streams; 3PB stored media over 18 months\n- Availability: playback 99.95%, publish 99.9%\n- Latency: publish-to-playback availability < 5 minutes p95 for standard content\n- Cost: compute must scale down aggressively; avoid idle transcoding fleets\n- Security: least privilege, secure media URLs, protect origin, WAF/DDOS\n- Observability: tracing across ingest jobs, transcode stages, publish workflow\n\nConstraints / preferences:\n- Strict separation between control plane and data plane\n- Prefer managed queueing where possible; explain trade-offs\n- Multi-region strategy must be explicit\n\nGovernance expectations:\n- Include FMEA with RPN scoring across pipeline stages and dependencies (DRM, CDN, storage)\n- ADL rules must enforce boundary between control/data planes and credential handling\n- Buy vs build should name real providers for transcoding, DRM, CDN, analytics pipeline',
  },
];

export function ChatView() {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    messages,
    streamingText,
    isStreaming,
    error,
    sendMessage,
    abort,
    reconnect,
    resetConversation,
  } = useConversation();
  const canReattach = useStore((s) => s.canReattach);
  const lastStageCompleted = useStore((s) => s.lastStageCompleted);

  /* Auto-scroll on new content */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  /* Auto-resize textarea */
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    const msg = input.trim();
    setInput('');
    await sendMessage(msg);
  };

  const handleExample = (example: string) => {
    if (isStreaming) return;
    setInput(example);
    queueMicrotask(() => textareaRef.current?.focus());
  };

  const handleReset = () => {
    resetConversation();
  };

  const hasContent = messages.length > 0 || !!streamingText;

  return (
    <div className="flex flex-col h-full" data-testid="chat-view">
      {/* ── Messages area ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {canReattach && (
          <div className="max-w-3xl mx-auto w-full px-4 pt-4" data-testid="reconnect-banner">
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3">
              <svg className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 2L1 14h14L8 2z" /><path d="M8 7v3M8 11.5v.5" />
              </svg>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-amber-900">Your session was interrupted</p>
                <p className="text-sm text-amber-800 mt-1">
                  The pipeline may still be running.
                  {lastStageCompleted ? ` Last completed stage: ${lastStageCompleted}.` : ''}
                </p>
              </div>
              <button
                type="button"
                className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 text-white px-3 py-1.5 text-xs font-semibold hover:bg-amber-700 transition-colors"
                onClick={reconnect}
              >
                Reconnect
              </button>
            </div>
          </div>
        )}
        {!hasContent ? (
          /* Welcome / empty state */
          <div className="relative flex flex-col items-center justify-center h-full px-4" data-testid="chat-empty">
            <div
              className="pointer-events-none absolute inset-0"
              aria-hidden="true"
            >
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(16,163,127,0.14)_1px,transparent_1px)] [background-size:18px_18px] opacity-35" />
              <div className="absolute inset-0 bg-gradient-to-b from-white via-white to-gray-50" />
            </div>

            <section className="relative max-w-3xl w-full" aria-label="Welcome">
              <div className="text-center space-y-6">
                <div className="w-14 h-14 mx-auto bg-accent/90 rounded-2xl flex items-center justify-center shadow-sm ring-1 ring-accent/30">
                  <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
                  </svg>
                </div>

                <div className="space-y-3">
                  <div>
                    <h1 className="text-3xl font-semibold text-gray-900 tracking-tight">Archon</h1>
                    <p className="text-[15px] text-gray-600 mt-2 leading-relaxed max-w-2xl mx-auto">
                      Describe your requirements once. Archon runs a structured architecture reasoning pipeline and returns
                      diagrams, decisions, and executable governance artifacts.
                    </p>
                  </div>

                  <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white/70 px-3 py-1 text-[11px] text-gray-600">
                    <span className="font-mono text-gray-500" aria-hidden="true">PIPELINE</span>
                    <span className="text-gray-300" aria-hidden="true">/</span>
                    <span>Staged reasoning, inspectable outputs</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-gray-700 mt-0.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M3.5 2.5h9v11h-9z" />
                        <path d="M5.5 5.5h5" />
                        <path d="M5.5 8h5" />
                        <path d="M5.5 10.5h3.5" />
                      </svg>
                      <p className="text-xs font-semibold text-gray-800">Executable governance</p>
                    </div>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      Produces Mark Richards ADL blocks and runnable rules (ArchUnit, PyTestArch, Semgrep).
                    </p>
                  </article>

                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-gray-700 mt-0.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M2.5 12.5h11" />
                        <path d="M4 12.5V9" />
                        <path d="M8 12.5V6.5" />
                        <path d="M12 12.5V4.5" />
                        <path d="M4 9l4-2.5L12 4.5" />
                      </svg>
                      <p className="text-xs font-semibold text-gray-800">Risk clarity</p>
                    </div>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      Weakness + FMEA analysis with RPN scoring and cascading failure visibility.
                    </p>
                  </article>

                  <article className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-gray-700 mt-0.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M2.5 12.5h11" />
                        <path d="M4 11V5" />
                        <path d="M8 11V3.5" />
                        <path d="M12 11V7" />
                      </svg>
                      <p className="text-xs font-semibold text-gray-800">Evidence-based style selection</p>
                    </div>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      Scores all eight Mark Richards styles with veto rules; no “default layered” shortcut.
                    </p>
                  </article>
                </div>

                <section aria-label="Example prompts" className="pt-1">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      <svg className="w-3.5 h-3.5 text-gray-500" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M3 4.5h10" />
                        <path d="M3 8h10" />
                        <path d="M3 11.5h6" />
                      </svg>
                      Try an example
                    </div>
                    <span className="text-[11px] text-gray-500">
                      Click to send
                    </span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2 text-left">
                    {EXAMPLES.map((ex) => (
                      <button
                        key={ex.label}
                        onClick={() => handleExample(ex.prompt)}
                        className="group border border-gray-200 rounded-xl px-4 py-3 text-[13px] text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 transition-colors text-left leading-relaxed"
                        data-testid="example-prompt"
                      >
                        <span className="inline-flex items-start gap-2">
                          <span className="font-mono text-[12px] text-gray-400 group-hover:text-gray-500" aria-hidden="true">
                            &gt;
                          </span>
                          <span className="font-medium text-gray-800">{ex.label}</span>
                        </span>
                        <div className="mt-1.5 text-[12px] text-gray-500">
                          Click to load a full requirements draft into the input.
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            </section>
          </div>
        ) : (
          /* Conversation */
          <div className="max-w-3xl mx-auto w-full px-4 py-6 space-y-6" data-testid="chat-messages">
            {/* Transcript */}
            {messages.map((m, idx) => {
              const key = m.id ?? `${m.role}-${idx}`;

              if (m.role === 'USER') {
                return (
                  <div className="flex gap-3" data-testid="user-message" key={key}>
                    <div className="w-7 h-7 shrink-0 rounded-full bg-gray-800 flex items-center justify-center mt-0.5">
                      <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 12c2.7 0 5-2.3 5-5s-2.3-5-5-5-5 2.3-5 5 2.3 5 5 5zm0 2c-3.3 0-10 1.7-10 5v2h20v-2c0-3.3-6.7-5-10-5z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-800 mb-1">You</p>
                      <p className="text-[15px] text-gray-700 leading-relaxed">{m.content}</p>
                    </div>
                  </div>
                );
              }

              return (
                <div className="flex gap-3" data-testid="assistant-message" key={key}>
                  <div className="w-7 h-7 shrink-0 rounded-full bg-accent flex items-center justify-center mt-0.5">
                    <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-gray-800 mb-1">Archon</p>
                    <MarkdownRenderer content={m.content} />
                  </div>
                </div>
              );
            })}

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-4 py-3" data-testid="chat-error">
                <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* In-flight assistant response */}
            {isStreaming && (
              <div className="flex gap-3" data-testid="assistant-message">
                <div className="w-7 h-7 shrink-0 rounded-full bg-accent flex items-center justify-center mt-0.5">
                  <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 21h18M3 10h18M12 3l9 7H3l9-7zM5 10v11m4-11v11m4-11v11m4-11v11" />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-gray-800 mb-1">Archon</p>
                  {streamingText ? (
                    <>
                      <MarkdownRenderer content={streamingText} />
                      <span className="inline-block w-1.5 h-4 bg-gray-800 animate-pulse align-text-bottom ml-0.5" />
                    </>
                  ) : (
                    <div className="flex items-center gap-1.5 py-2">
                      <div className="w-2 h-2 bg-accent rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-accent rounded-full animate-bounce [animation-delay:150ms]" />
                      <div className="w-2 h-2 bg-accent rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Input area ── */}
      <div className="border-t border-gray-100 bg-white px-4 pb-4 pt-3">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex items-end border border-gray-200 rounded-2xl shadow-sm focus-within:border-gray-300 focus-within:shadow-md transition-all bg-white">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your system requirements…"
              rows={1}
              className="flex-1 resize-none border-0 bg-transparent px-4 py-3.5 text-[15px] text-gray-800 placeholder:text-gray-400 focus:outline-none max-h-[200px]"
              data-testid="chat-input"
              disabled={isStreaming}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <div className="flex items-center gap-1.5 pr-2 pb-2">
              {isStreaming ? (
                <button
                  type="button"
                  onClick={abort}
                  className="p-2 rounded-lg bg-gray-800 text-white hover:bg-gray-700 transition-colors"
                  data-testid="chat-abort"
                  title="Stop generating"
                >
                  <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                    <rect x="3" y="3" width="10" height="10" rx="1" />
                  </svg>
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="p-2 rounded-lg bg-gray-800 text-white hover:bg-gray-700 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
                  data-testid="chat-submit"
                  title="Send message"
                >
                  <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 12V4M4 8l4-4 4 4" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between mt-2 px-1">
            <p className="text-[11px] text-gray-400">
              Archon may produce inaccurate designs. Verify critical decisions.
            </p>
            <button
              type="button"
              onClick={handleReset}
              disabled={isStreaming}
              className="text-[11px] text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
              data-testid="chat-reset"
            >
              New chat
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
