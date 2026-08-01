# Lens Agent API QA Report

Date: 2026-06-27
Service under test: `http://localhost:8086`
Route source reviewed: `lens-agent/app/api/routes.py`

## Endpoint Summary

`routes.py` exposes three POST endpoints:

- `POST /gaps/generate`: accepts `session_id`, `evidence`, `previous_questions`, `answers`, and `round`; returns a list of clarifying gap questions.
- `POST /gaps/assess`: accepts `session_id`, `questions`, `answers`, `round`, and `max_rounds`; returns a gap resolution assessment.
- `POST /review`: accepts `session_id`, `system_description`, `evidence`, `gap_questions`, `gap_answers`, and `insufficient_info_gaps`; returns a streamed review report.

Health check was also verified with:

```sh
curl -sS http://localhost:8086/health
```

Result: `200 {"status":"healthy","service":"lens-agent"}`

## Test Method

I designed five architecture scenarios and called each route-defined endpoint with `curl` for every scenario. Raw payloads and responses were captured under `/private/tmp/lens_agent_qa_outputs`.

Example command shape:

```sh
curl -sS -w '\n__HTTP_STATUS__:%{http_code}\n' \
  --max-time 240 \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary @- \
  http://localhost:8086/review
```

## Scenarios

1. **Insurance Claims Modernization**
   Cloud-native AKS and event-driven claims platform using Front Door, API Management, Service Bus, Cosmos DB, Blob Storage, managed identity, OpenTelemetry, and blue-green deployment. Known gaps included DR region, RTO/RPO, and service-to-service authentication.

2. **Legacy ERP Integration Hub**
   Node.js REST API on App Service writes directly to ERP SQL Server over VPN and synchronously calls SaaS vendor APIs. Known gaps included failure isolation, retry/circuit breaker design, schema versioning, fallback mode, and runbooks.

3. **IoT Telemetry Platform**
   MQTT ingestion through IoT Hub, Stream Analytics, Event Hubs, Functions, ADLS Gen2, and Synapse serverless. Known gaps included peak throughput validation, partitioning, backpressure, poison-message handling, retention, and cost controls.

4. **Healthcare AI Triage Assistant**
   FastAPI clinical workflow that stores PHI, calls an LLM endpoint for summarization and triage suggestions, and requires clinician review. Known gaps included PHI redaction, model data handling, encryption detail, audit retention, override workflow, incident response, and availability.

5. **E-commerce Flash Sale Checkout**
   React storefront, API Management, Container Apps checkout APIs, PostgreSQL inventory reservations, third-party payment gateway, CDN/Redis caching, Service Bus fulfillment, and HTTP concurrency autoscaling. Known gaps included idempotency, oversell prevention, callback verification, load test evidence, and cost guardrails.

## Results Matrix

| Scenario | `/gaps/generate` | `/gaps/assess` | `/review` |
| --- | ---: | ---: | ---: |
| Insurance Claims Modernization | 200 in 5.37s | 200 in 1.76s | 500 in 43.83s |
| Legacy ERP Integration Hub | 200 in 6.60s | 200 in 1.53s | 500 in 51.61s |
| IoT Telemetry Platform | 200 in 7.32s | 200 in 1.69s | 500 in 47.88s |
| Healthcare AI Triage Assistant | 200 in 5.01s | 200 in 1.63s | 500 in 41.17s |
| E-commerce Flash Sale Checkout | 200 in 4.05s | 200 in 2.90s | 500 in 33.47s |

## Response Quality Evaluation

### `POST /gaps/generate`

Overall quality: **Good, with some overreach.**

Strengths:

- Returned HTTP 200 for all five scenarios.
- Returned the expected maximum of eight questions in each scenario.
- Questions were generally specific, architecture-aware, and mapped well to risk areas such as security, reliability, performance, cost, operations, data, modifiability, and integrability.
- The endpoint identified important known gaps, for example service-to-service authentication in the claims scenario, synchronous dependency failure handling in the ERP scenario, PHI protection in the healthcare scenario, and payment gateway failure handling in the flash-sale scenario.

Concerns:

- Some questions asked for topics that were partly evidenced. In the claims scenario, the response asked for broader monitoring beyond OpenTelemetry, which is useful but should acknowledge that tracing is already present.
- Some questions felt generic instead of scenario-critical. For example, questions about external integration documentation appeared even when the scenario's most severe gap was explicit consistency or availability risk.
- The endpoint returns bare question objects without stable IDs, which makes downstream answer correlation harder unless the caller adds IDs.

### `POST /gaps/assess`

Overall quality: **Mixed. HTTP behavior is stable, but assessment context is incomplete.**

Strengths:

- Returned HTTP 200 for all five scenarios.
- Correctly blocked progression when critical unanswered questions remained.
- In the healthcare scenario, the assessment correctly called out security and reliability gaps as blockers.
- In the claims scenario, it correctly focused on missing service-to-service authentication.

Concerns:

- The route only receives `questions` and `answers`, not the original architecture evidence. As a result, several assessments incorrectly reported missing "system purpose and scope", "primary components and responsibilities", and "deployment or infrastructure detail" even though those were present in the scenario evidence submitted to `/gaps/generate` and `/review`.
- The `answers` list is not fully used by the current implementation unless matching questions also carry embedded `answer` fields or `answered=true`. This makes the contract easy to misuse.
- `unresolvableGaps` is inconsistent. Some responses returned broad coverage-area labels such as `system purpose and scope`; others returned categories such as `SECURITY` or `RELIABILITY`. Consumers would have to normalize this field themselves.
- The endpoint can be overly strict before `max_rounds`, returning `canProceed=false` even when enough baseline evidence exists outside the Q&A payload.

### `POST /review`

Overall quality: **Failing.**

All five review calls returned:

```text
Internal Server Error
__HTTP_STATUS__:500
```

The failures occurred after substantial latency, between 33.47s and 51.61s, which suggests the pipeline performed some model work before failing. No structured error body was returned to the caller.

Impact:

- The main review workflow is unusable through the public API.
- Callers receive no actionable diagnostic detail.
- Because the route streams `str(final_context.review_report)` as `application/x-ndjson`, even a successful response would likely not be valid JSON or valid newline-delimited JSON. The API should stream JSON serialization or return a normal JSON response.

## Key Findings

1. **Critical: `/review` returns HTTP 500 for every tested scenario.**
   This blocks the primary lens-agent workflow. The endpoint should return a valid review report or a structured error response. The current plain `Internal Server Error` body gives no caller-visible cause.

2. **High: `/gaps/assess` lacks architecture evidence context.**
   The endpoint evaluates minimum coverage areas but receives only questions and answers. This caused false negatives about missing scope, components, and deployment details when those details were present in the evidence.

3. **Medium: `/gaps/assess` answer correlation is fragile.**
   The implementation builds Q&A pairs mostly from fields embedded on question objects. A caller that sends answers only through the `answers` array may not get the intended answer text into the prompt.

4. **Medium: `/gaps/generate` needs stable question IDs.**
   Generated questions should include stable IDs so `/gaps/assess` and `/review` can correlate answers without client-side ID injection.

5. **Medium: Response contracts are inconsistent.**
   `/gaps/generate` returns a raw array, `/gaps/assess` returns camelCase fields with some snake_case prompt internals, and `/review` advertises NDJSON but returns a Python string representation if successful.

## Recommendations

1. Fix `/review` first and add an integration test that posts a minimal valid scenario and asserts a non-500 structured response.
2. Change `/review` to return JSON through `JSONResponse` or stream actual JSON lines with `json.dumps`.
3. Include `evidence` and/or a compact architecture summary in `/gaps/assess` so coverage decisions account for the full review context.
4. Update `_build_qa_pairs` in `gap_assessor.py` to join `answers[].question_id` to `questions[].id` and include the answer text from the `answers` array.
5. Add `id` to each generated gap question and document the request/response contracts for all three endpoints.
6. Add contract tests covering:
   - all endpoints return valid JSON on success;
   - `/gaps/generate` returns no more than eight questions;
   - `/gaps/assess` respects `max_rounds` fail-open behavior;
   - `/review` includes `sessionId`, `overallRating`, `risks`, `recommendations`, `completedStages`, and `insufficientInfoFindings`.

## Overall Assessment

The gap generation endpoint is useful enough to support an elicitation workflow. The assessment endpoint is promising but under-contextualized, which leads to misleading "missing coverage" judgments. The review endpoint is currently not production-usable because it returned HTTP 500 for every tested architecture scenario.
