# Lens Agent QA Verification Report

Date: 2026-06-27
Branch: `lens`
Service under test: `http://localhost:8086`
Raw captures: `/private/tmp/lens_agent_verification_outputs`

## Setup

- Confirmed current branch: `lens`
- Ran `git pull --ff-only`: already up to date
- Verified service with targeted `curl` calls against `POST /gaps/generate`, `POST /gaps/assess`, and `POST /review`
- All endpoint responses in this verification run were parseable JSON

## Part 1: Regression Verification

| Finding | Result | Evidence |
| --- | --- | --- |
| Finding 1: `/review` returned 500 for all scenarios | PASS | Insurance Claims `/review` returned HTTP 200 in 40.30s. Response was valid JSON with `sessionId`, `overallRating`, `risks`, `recommendations`, and `completedStages`. |
| Finding 2: `/gaps/assess` lacked evidence context | PASS | `/gaps/assess` with evidence plus answers covering scope, components, deployment, security, and reliability returned `resolved=true`, `canProceed=true`, `remainingCount=0`. Summary explicitly said all required areas were covered. |
| Finding 3: answer correlation was fragile | PASS | `/gaps/assess` with answers only in the `answers` array returned `resolved=true`, `canProceed=true`, `remainingCount=0`. This indicates answer-array correlation is working. |
| Finding 4: questions had no stable IDs | PASS | `/gaps/generate` returned 8 questions and every question had a non-empty UUID-like `id` field. |
| Finding 5: inconsistent response contracts | PASS | `/gaps/generate` returned an array of objects; `/gaps/assess` returned `resolved`, `canProceed`, `remainingCount`, `unresolvableGaps`, `summary`; `/review` returned `sessionId`, `overallRating`, `risks`, `recommendations`, `completedStages`, and `insufficientInfoFindings`. |
| Finding 6: `/review` 500 had no structured error body | FAIL | Deliberately malformed `/review` request with empty evidence and no `system_description` returned HTTP 200 with a normal review report, not a JSON error object with `error` and `detail`. It no longer returns plain `Internal Server Error`, but it also does not validate the malformed request. |

Regression summary: **5 PASS, 1 FAIL**

## Part 2: Report Content Quality

Scenarios evaluated:

- Scenario A: Healthcare AI Triage
- Scenario B: IoT Telemetry Platform

| Section | Quality | Notes |
| --- | --- | --- |
| Azure WAF Scorecard | Acceptable | Both reports scored all five pillars. Healthcare scores were plausible, especially `security=0` and `reliability=1`. IoT scores were directionally useful but too harsh in places: `operational_excellence=0` despite dashboards, and `performance_efficiency=0` despite partial throughput testing evidence. Gaps were mostly scenario-specific. |
| ATAM Analysis | Acceptable | Both reports included quality attribute scenarios, sensitivity points, tradeoffs, and risks with severity. IoT ATAM was specific and useful. Healthcare ATAM included generic or unsupported details, such as Kubernetes health checks and REST communication, which were not in the evidence. |
| SEI Analysis | Acceptable | Both reports assessed all five attributes and populated `tactics_present` and `tactics_missing`. Ratings were mostly plausible, but there were inconsistencies: Healthcare `modifiability=ADEQUATE` seemed overstated from thin evidence, and IoT security was `ADEQUATE` in SEI while Azure WAF security was `0`. |
| Risk Register | Acceptable | Risks were architecture-specific enough to be useful and counts were within the `<=20` cap. Severity was usually sensible, such as Healthcare PHI protection as `CRITICAL` and IoT peak throughput as `CRITICAL`. Some risks were generic or partly hallucinated, such as healthcare synchronous REST latency. |
| Recommendations | Good | Recommendations were specific, actionable, included `priority`, `effort`, and `addresses_risk`, and stayed within the `<=15` cap. Top recommendations mapped well to the top risks. Some lower-priority recommendations were generic, but still usable. |
| Executive Summary | Good | Both summaries had plausible `NEEDS_REWORK` ratings, mentioned top risks and recommendations, and called out insufficient information areas. They were readable and useful for technical leadership. |

## Scenario A: Healthcare AI Triage Details

- Overall rating: `NEEDS_REWORK`
- Azure WAF scores: reliability `1`, security `0`, cost `0`, operational excellence `0`, performance `0`
- SEI ratings: modifiability `ADEQUATE`, performance `NO_EVIDENCE`, availability `NO_EVIDENCE`, security `NO_EVIDENCE`, integrability `NO_EVIDENCE`
- Risks: 16
- Recommendations: 15
- Insufficient information findings: 2

Strengths:

- Correctly identified PHI protection before model calls as a critical issue.
- Correctly treated planned Azure AD authentication as insufficient implementation evidence.
- Executive summary clearly explained the need for rework.

Concerns:

- ATAM introduced architecture details not present in evidence, including Kubernetes health checks and REST communication.
- Several lower-priority risks were generic and not tightly tied to the healthcare workflow.
- Security recommendations should include model data handling, PHI redaction, audit retention, and clinical governance more prominently.

## Scenario B: IoT Telemetry Platform Details

- Overall rating: `NEEDS_REWORK`
- Azure WAF scores: reliability `3`, security `0`, cost `0`, operational excellence `0`, performance `0`
- SEI ratings: modifiability `ADEQUATE`, performance `WEAK`, availability `WEAK`, security `ADEQUATE`, integrability `ADEQUATE`
- Risks: 10
- Recommendations: 10
- Insufficient information findings: 2

Strengths:

- Correctly identified unvalidated 250k messages/sec throughput as a major risk.
- Correctly raised poison-message handling, telemetry retention, partitioning, and cost controls.
- Recommendations were concrete and tied to IoT/Azure implementation choices.

Concerns:

- Azure WAF scores under-credit partial evidence. Dashboards and failure metrics should probably prevent operational excellence from scoring `0`.
- WAF security `0` conflicts with SEI security `ADEQUATE`; device certificates provide at least partial identity evidence.
- Recommendation to use JMeter or Gatling for MQTT/IoT load testing is somewhat generic; IoT-specific tooling or Event Hubs/IoT Hub scale validation guidance would be stronger.

## Part 3: Edge Cases

| Edge Case | Result | Evidence |
| --- | --- | --- |
| Minimal evidence: `"A web application."` | PARTIAL FAIL | Pipeline completed with HTTP 200 and `overallRating=NEEDS_REWORK`, but `insufficientInfoFindings` was empty and the executive summary said there were no significant limitations due to insufficient information. The report also hallucinated complex service-to-service interactions, database bottlenecks, Kubernetes recovery, and microservices tradeoffs. |
| Max rounds forced proceed | PASS | `/gaps/assess` with `round=5`, `max_rounds=5`, and three unanswered questions returned `canProceed=true`, `resolved=false`, `remainingCount=3`, and populated all three `unresolvableGaps`. |
| Rich evidence with all gap questions answered | PASS | `/review` returned HTTP 200 with `security=4`, `reliability=4`, `cost_optimisation=4`, `operational_excellence=5`, `performance_efficiency=4`, no insufficient information findings, and fewer risks than weaker scenarios. The report reflected described authentication and resilience details. |

## New Issues Discovered

1. **Malformed `/review` requests are accepted as normal reviews.**
   Empty evidence and missing `system_description` returned HTTP 200 with a full report instead of a structured validation error. This fails the explicit regression criterion for Finding 6.

2. **Minimal evidence does not produce insufficient-information findings.**
   The minimal `"A web application."` scenario produced no `insufficientInfoFindings`, and the executive summary claimed there were no significant limitations. This is misleading and should be treated as a report-quality defect.

3. **The review pipeline still hallucinates details under sparse evidence.**
   Minimal evidence produced claims about broad user bases, complex service-to-service interactions, database bottlenecks, Kubernetes recovery, and microservices tradeoffs. Healthcare ATAM also introduced Kubernetes and REST details not present in evidence.

4. **Cross-framework scoring can be inconsistent.**
   IoT security scored `0` in Azure WAF but `ADEQUATE` in SEI due to device certificates. The difference should be explained or normalized.

5. **Partial evidence is sometimes scored as no evidence.**
   IoT operational excellence and performance were scored `0` despite dashboards and partial load test results. These should likely be low-but-nonzero scores.

## Overall Readiness Assessment

**NEEDS FIXES BEFORE INTEGRATION**

The major blocking regression for `/review` returning HTTP 500 appears resolved, and the endpoint contracts are now mostly stable. However, malformed input validation and sparse-evidence handling still need fixes before integration testing. The generated reports are useful for realistic scenarios, but the pipeline must stop treating minimal or malformed input as enough context for a confident review.

---

## Retest After Fixes

Retest date: 2026-06-27
Raw captures: `/private/tmp/lens_agent_retest_outputs`

The service was retested after the reported fixes. The route code now includes `/review` request validation with a minimum combined evidence threshold of 50 characters.

### Retest Results

| Area | Result | Evidence |
| --- | --- | --- |
| Malformed `/review` request | PASS | Empty evidence and no `system_description` returned HTTP 400 in 0.01s with JSON `{ "error": "Invalid review request", "detail": "...Received 0 characters." }`. |
| Minimal evidence: `"A web application."` | PASS | Returned HTTP 400 in 0.01s with JSON `{ "error": "Invalid review request", "detail": "...Received 36 characters." }`. This prevents the previous hallucinated review. |
| Healthcare AI Triage report | PASS | Returned HTTP 200 in 31.00s. Report had scenario-specific WAF, ATAM, SEI, risks, recommendations, executive summary, and 2 insufficient-information findings. Previous unsupported Kubernetes/REST ATAM details were not observed in this retest. |
| IoT Telemetry report | PASS WITH NOTES | Returned HTTP 200 in 33.48s. Partial evidence is now credited: security `1`, operational excellence `1`, performance efficiency `1`. Report includes scenario-specific risks and recommendations. Reliability still scored `0` despite operational dashboards and device/certificate evidence still results in broad security gaps. |
| Rich evidence with all gap questions answered | FAIL | Returned HTTP 200 twice, but both responses had empty `azureWafScorecard`, empty `atamAnalysis`, empty `seiAnalysis`, zero risks, zero recommendations, and multiple `pipelineGaps` such as `azure_waf_analysis: LLM call failed`, `atam_analysis: LLM call failed`, `sei_analysis: LLM call failed`, `structural_analysis: LLM call failed`, `recommendation_generation: LLM call failed`, and `executive_summary: LLM call failed`. |

### Updated Content Quality Notes

- Healthcare content quality improved from **Acceptable** to **Good/Acceptable**. The report is more grounded in the submitted evidence and no longer invents Kubernetes health checks or REST communication in ATAM.
- IoT content quality improved from **Acceptable** to **Acceptable+**. The earlier all-zero scoring for operational excellence and performance was corrected to low-but-nonzero scores. Security also now credits device certificates.
- Sparse evidence handling is fixed by rejecting requests before the review pipeline runs.
- The rich answered scenario regressed or exposed a new reliability defect: the endpoint can return HTTP 200 with a structurally valid but substantively empty report after internal LLM-stage failures.

### Remaining Issues After Retest

1. **Valid rich reviews can return HTTP 200 with empty analysis sections.**
   The rich answered architecture produced a report with no WAF scorecard, no ATAM analysis, no SEI analysis, no risks, and no recommendations. This should not be treated as a successful review response.

2. **Supporting-stage LLM failures are surfaced only as report gaps, not as request failure.**
   Because the endpoint still returns HTTP 200, API consumers may treat an incomplete report as successful unless they inspect `pipelineGaps`.

3. **Review pipeline may not be incorporating `gap_answers` into analysis prompts.**
   The rich answered test supplied answers in `gap_answers`, but the resulting report did not reflect them because upstream LLM stages failed. This should be checked once stage failures are resolved.

4. **IoT reliability scoring may still under-credit partial evidence.**
   The report noted dashboards for message ingress and function failures under operational excellence, but reliability remained `0` with an additional insufficient-information finding for reliability.

### Updated Readiness Assessment

**NEEDS FIXES BEFORE INTEGRATION**

The previously failing malformed/minimal evidence path is fixed. Report quality improved for Healthcare and IoT. However, the rich valid architecture case returning HTTP 200 with empty analysis sections is a serious integration risk. The service should either retry/recover failed LLM stages or return a structured non-2xx/error state when required report sections cannot be generated.

---

## Retest 2 After Latest Fix

Retest date: 2026-06-27
Raw captures: `/private/tmp/lens_agent_retest2_outputs`

The service was retested again after the latest fix. This pass focused on the previous remaining issue: valid review requests returning HTTP 200 with empty analysis sections after internal LLM-stage failures.

### Retest 2 Results

| Area | Result | Evidence |
| --- | --- | --- |
| Malformed `/review` request | PASS | Empty evidence returned HTTP 400 in 0.02s with structured JSON `error: Invalid review request`. |
| Minimal evidence: `"A web application."` | PASS | Minimal evidence returned HTTP 400 in 0.01s with structured JSON `error: Invalid review request`. |
| Rich evidence with all gap questions answered | PARTIAL PASS / FAIL | The previous bad behavior is fixed: the service no longer returns HTTP 200 with empty analysis sections. It now returns HTTP 503 with structured JSON `error: Review incomplete`, `detail`, `pipeline_gaps`, and `completed_stages`. However, this valid rich request still did not produce a successful review. |
| Healthcare AI Triage report | FAIL | Returned HTTP 503 in 85.13s with `Review incomplete`. Pipeline gaps included `azure_waf_analysis: LLM call failed`, `atam_analysis: LLM call failed`, `sei_analysis: LLM call failed`, `structural_analysis: LLM call failed`, `recommendation_generation: LLM call failed`, and `executive_summary: LLM call failed`. |
| IoT Telemetry report | FAIL | Returned HTTP 503 in 85.59s with the same set of LLM-stage pipeline failures. |

### Retest 2 Assessment

The latest fix correctly prevents incomplete reports from being presented as successful HTTP 200 responses. That is a meaningful contract improvement. API consumers can now reliably distinguish incomplete review generation from successful report generation.

However, all valid full-review scenarios in this retest returned HTTP 503 after roughly 85-88 seconds. This means the service is currently unable to complete the core `/review` workflow under the tested conditions. The error response is well structured, but the product behavior is still not integration-ready because no full report was generated for rich, healthcare, or IoT scenarios.

### Remaining Issues After Retest 2

1. **Valid full-review requests return HTTP 503.**
   The service now fails safely, but the core review workflow is unavailable for the tested scenarios.

2. **Most LLM-backed analysis stages fail together.**
   The repeated pipeline gaps indicate a systemic provider/timeout/rate-limit issue rather than an isolated stage failure.

3. **Full-review latency before failure is high.**
   Valid requests took 85-88 seconds before returning 503. This may be acceptable for an async job model, but it is expensive and awkward for a synchronous API call.

### Final Readiness Assessment

**NOT READY**

The response contract is now safer than before: malformed/minimal requests return 400, and incomplete reviews return structured 503 instead of misleading HTTP 200 empty reports. But the full `/review` workflow failed for every valid scenario in this retest, so the service is not ready for integration testing until the LLM-stage failures are resolved or the endpoint is moved to a reliable async/retry-backed execution model.

---

## Retest 3 After Credit Limit Resolution

Retest date: 2026-06-27
Raw captures: `/private/tmp/lens_agent_retest3_outputs`

The previous Retest 2 failures were caused by OpenAI `429 insufficient_quota` errors in the uvicorn logs. After the credit-limit issue was resolved, the same validation and full-review scenarios were rerun.

### Retest 3 Results

| Area | Result | Evidence |
| --- | --- | --- |
| Malformed `/review` request | PASS | Empty evidence returned HTTP 400 in 0.01s with structured JSON `error: Invalid review request`. |
| Minimal evidence: `"A web application."` | PASS | Minimal evidence returned HTTP 400 in 0.01s with structured JSON `error: Invalid review request`. |
| Rich evidence with all gap questions answered | PASS | Returned HTTP 200 in 41.21s with no `pipelineGaps`, WAF scores populated, ATAM/SEI populated, 12 risks, 12 recommendations, and 0 insufficient-information findings. |
| Healthcare AI Triage report | PASS | Returned HTTP 200 in 41.22s with no `pipelineGaps`, populated report sections, 20 risks, 15 recommendations, and 2 insufficient-information findings. |
| IoT Telemetry report | PASS WITH NOTES | Returned HTTP 200 in 33.79s with no `pipelineGaps`, populated report sections, 11 risks, 11 recommendations, and 4 insufficient-information findings. |

### Retest 3 Section Checks

Rich answered scenario:

- WAF scores: reliability `4`, security `3`, cost optimisation `3`, operational excellence `4`, performance efficiency `3`
- SEI ratings: modifiability `ADEQUATE`, performance `ADEQUATE`, availability `STRONG`, security `ADEQUATE`, integrability `ADEQUATE`
- ATAM content: 5 quality attribute scenarios, 2 sensitivity points, 2 tradeoffs
- Top risks: data protection at rest, threat detection, dependency failure isolation
- Top recommendations: implement data encryption at rest, integrate Azure Security Center, implement circuit breakers

Healthcare scenario:

- WAF scores: reliability `0`, security `1`, cost optimisation `0`, operational excellence `0`, performance efficiency `0`
- Insufficient information findings correctly include PHI protection before model calls and clinical workflow availability targets
- Top risks and recommendations are scenario-specific and actionable

IoT scenario:

- WAF scores: reliability `0`, security `1`, cost optimisation `0`, operational excellence `1`, performance efficiency `1`
- Partial evidence is credited for device certificates, dashboards, and partial throughput testing
- Remaining note: reliability still scores `0`, and the report adds broad security/reliability insufficient-information findings in addition to the supplied data/cost gaps

### Final Readiness Assessment After Retest 3

**READY FOR INTEGRATION TESTING**

The blocking provider/quota issue is resolved, the core `/review` workflow now completes successfully for all valid retest scenarios, malformed and sparse requests fail fast with structured 400 responses, and incomplete reports are no longer presented as successful HTTP 200 responses. Remaining observations are content-quality tuning items rather than integration blockers.
