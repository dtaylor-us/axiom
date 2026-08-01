# Lens Pillar UI/UX QA Report

## Executive Summary

Lens is partially usable but not ready for a clean end-to-end release. The primary happy path can create a session, submit evidence, generate and answer gap questions, assess gaps, start a review, and initially render an Overview report. However, completed report restoration is broken, the ATAM tab crashes the React view, the Lens sidebar still shows Archon-oriented actions/history, duplicate gap questions are reproducible, and review pipeline progress is not observable in the UI. I found 7 issues: 3 HIGH, 3 MEDIUM, and 1 LOW. Known issues confirmed: session reload after report and duplicate gap questions. Archon sessions in Lens home was not reproduced.

## Environment

- Test date/time: 2026-06-27 15:52:27 CDT
- Browser used: Playwright Chrome, headed session
- axiom-ui: `http://localhost:3000` returned HTTP 200
- lens-api: `http://localhost:8083/actuator/health` returned `{"status":"UP"}`
- lens-agent: `http://localhost:8086/health` returned `{"status":"healthy","service":"lens-agent"}`
- Auth path: local Guest user via "Continue as Guest"
- Primary test session: `f070a706-2344-4187-885e-0c2d5c6d99d4`
- Secondary test session: `063daa29-4510-4f28-8d4f-e239471a9536`

## Happy Path Results

| Step | Result | Notes |
|------|--------|-------|
| Lens home page loads | PASS | Hero, CTA, three-step explainer, framework strip, and Recent reviews displayed. |
| Create session | PASS | CTA navigated through `/lens/new` to `/lens/sessions/{id}`. |
| Submit evidence | PASS | Evidence card showed `TEXT_DESCRIPTION`, source label, content, Delete button, and enabled gap generation. |
| Generate gap questions | PASS | Round 1 returned 8 questions. |
| Answer questions | PASS | Answered 3 questions, skipped 1, left remaining questions unanswered. |
| Assess gaps | PARTIAL | Summary appeared and session moved to `READY_FOR_REVIEW`, but literal `resolved` and `canProceed` fields were not visible. |
| Proceed to review | PASS | `READY_FOR_REVIEW` state showed evidence count, unresolved gap count, and Start review button. |
| Start review | PARTIAL | Review eventually completed, but the first click did not visibly transition; a second click was needed in observed flows. |
| Pipeline progress visible | FAIL | No `IN_REVIEW` stage progress list was observed; review jumped from ready/start to complete report. |
| Report renders | PARTIAL | Overview and Azure WAF initially rendered. ATAM tab crashed the UI, blocking reliable tab walkthrough. |
| Session reloads correctly | FAIL | Reload showed `COMPLETE` status but no report, plus an unexpected error message. |

## Known Issues Status

| Issue | Status | Severity | Notes |
|-------|--------|----------|-------|
| Archon sessions in Lens home | NOT REPRODUCED | N/A | Recent reviews showed Lens review rows only: `Untitled review COMPLETE` and `Untitled review GAP_ELICITATION`. |
| Session reload after report | CONFIRMED | HIGH | Reloading a completed session preserved `COMPLETE` status but rendered an error and no report. Opening from Recent reviews reproduced the same failure. |
| Duplicate gap questions | CONFIRMED | MEDIUM | Round 2 repeated Round 1 questions for performance testing and PostgreSQL/Redis backup. Cost and deployment questions were near-duplicates. |

## Gap Questions Observed

Round 1 returned 8 questions:

| Category | Question |
|---|---|
| RELIABILITY | What mechanisms are in place for handling service failures and ensuring high availability? |
| COST | What strategies are in place for monitoring and optimizing operational costs? |
| OPERATIONS | What is the deployment strategy for updates and how are they managed? |
| PERFORMANCE | What performance testing has been conducted to ensure the system can handle the expected peak load? |
| MODIFIABILITY | How is the system designed to accommodate future changes or scaling requirements? |
| INTEGRABILITY | What integration points exist with external systems, and how are they managed? |
| DATA | What data backup and recovery processes are in place for PostgreSQL and Redis? |
| GOVERNANCE | What governance policies are in place to ensure compliance and data protection? |

Round 2 also returned 8 questions. Duplicate or redundant pairs:

| Round 1 | Round 2 | Type |
|---|---|---|
| What performance testing has been conducted to ensure the system can handle the expected peak load? | What performance testing has been conducted to ensure the system can handle the expected peak load? | Exact duplicate |
| What data backup and recovery processes are in place for PostgreSQL and Redis? | What data backup and recovery processes are in place for PostgreSQL and Redis? | Exact duplicate |
| What strategies are in place for monitoring and optimizing operational costs? | What mechanisms are in place for cost monitoring and optimization? | Near duplicate |
| What is the deployment strategy for updates and how are they managed? | What is the strategy for managing and deploying updates to the microservices? | Near duplicate |

Questions also ask about known absent information, such as cost monitoring and RTO/RPO, even when evidence explicitly states those are not defined.

## New Issues Found

### HIGH: ATAM tab crashes the report view

- Steps to reproduce:
  1. Complete a Lens review.
  2. Click the `ATAM` report tab.
- Expected behaviour: ATAM content renders in a readable format.
- Actual behaviour: the page render tree becomes blank/empty and console shows: `Objects are not valid as a React child (found: object with keys {decision, affected_attribute, effect})`.
- Screenshot reference: `axiom-ui/lens-qa-screenshots/step-10-tab-atam.png`
- Severity: HIGH

### HIGH: Completed session reload does not restore report

- Steps to reproduce:
  1. Complete a review and view the report.
  2. Reload `/lens/sessions/{id}`.
  3. Navigate to `/lens` and reopen the completed session from Recent reviews.
- Expected behaviour: completed report appears immediately.
- Actual behaviour: status shows `COMPLETE`, but the report area is missing and the page displays `An unexpected error occurred. Please try again.`
- Screenshot references: `issue-02-session-reload-after-report.png`, `issue-02-recent-session-open.png`
- Severity: HIGH

### HIGH: Lens sidebar shows Archon chat actions and no Lens session history

- Steps to reproduce:
  1. Navigate to `/lens`.
  2. Inspect the left sidebar under the pillar navigation.
- Expected behaviour: Lens should show Lens-contextual actions, such as creating a new architecture review, and the History section should list Lens review sessions.
- Actual behaviour: the sidebar shows Archon/chat-oriented actions: `New chat`, `Home`, `Chat`, and `Workshop`. The History section says `No chats yet` even though Lens sessions exist in the main Recent reviews section.
- Screenshot reference: `issue-lens-sidebar-archon-actions.png`
- Severity: HIGH

### MEDIUM: Gap elicitation panel appears before evidence is submitted

- Steps to reproduce:
  1. Create a new Lens session.
  2. Observe the session page before adding evidence.
- Expected behaviour: no gap questions panel is visible yet.
- Actual behaviour: `Gap elicitation`, `Round 1 of 5`, and `Proceed anyway` are visible before evidence submission.
- Screenshot reference: `step-02-new-session.png`
- Severity: MEDIUM

### MEDIUM: Duplicate gap questions across rounds

- Steps to reproduce:
  1. Submit evidence.
  2. Generate gap questions.
  3. Click `Generate gap questions` again.
- Expected behaviour: new round should avoid duplicates and already-addressed questions.
- Actual behaviour: exact and near-duplicate questions appear in Round 2.
- Screenshot reference: `issue-03-duplicate-gap-questions.png`
- Severity: MEDIUM

### MEDIUM: Review pipeline progress is not observable

- Steps to reproduce:
  1. Move a session to `READY_FOR_REVIEW`.
  2. Click `Start review`.
- Expected behaviour: status transitions to `IN_REVIEW` and stage progress is visible.
- Actual behaviour: no progress stage list was observed; UI remained ready briefly and then report appeared.
- Screenshot reference: `step-08-ready-for-review.png`, `step-10-report-overview.png`
- Severity: MEDIUM

### LOW: Assessment panel omits expected structured fields

- Steps to reproduce:
  1. Submit answers.
  2. Click `Assess gaps`.
- Expected behaviour: assessment panel shows `resolved` and `canProceed` fields.
- Actual behaviour: summary text is visible, but the structured fields are not exposed.
- Screenshot reference: `step-07-gap-assessment.png`
- Severity: LOW

## Gap Elicitation UX Notes

- Round clarity: visible as `Round 1 of 5` or `Round 2 of 5`.
- Rationale visibility: rationale is collapsed behind a `Rationale` disclosure by default, not visible without extra click.
- Proceed clarity: `Proceed anyway` is visible early, but its consequence is not explained at the button location.
- Submit feedback: after submitting answers and assessing gaps, summary feedback appears and the session moves to review readiness.
- Refresh mid-elicitation: not separately tested. Completed-session reload is broken and should be fixed first because it affects persistence confidence.

## Report Tab Usability

- Overview: initially renders readable summary text, rating badge `NEEDS_REWORK`, and counts: Risks 10, Recommendations 10, Findings 13.
- Azure WAF: renders readable score cards rather than raw JSON. However, scores showed `0.0 / 5` and addressed/gaps/findings counts all showed zero despite the overview showing findings.
- ATAM: crashes the view with a React object-rendering error.
- SEI, Structural, Risks, Recommendations: not fully validated after the ATAM crash because completed-session reload/reopen fails to restore the report.
- Raw rendering: console includes an object-rendering failure; no literal `[object Object]` text was observed in the visible UI before the crash.

## Navigation and Cross-Pillar Checks

| Check | Result | Notes |
|---|---|---|
| Lens appears in pillar nav | PASS | Lens is visible in sidebar with Architecture Review Intelligence label. |
| Lens amber/orange badge | PASS | Lens badge appears amber/orange visually; exact pixel sampling was not performed. |
| SpecWeaver navigation | PASS | Clicking SpecWeaver navigated to `/specweaver` without visible error. |
| Archon navigation | PASS | Clicking Archon navigated to `/archon` without visible error. |
| Lens navigation | PASS | Clicking Lens returned to `/lens` without visible error. |
| Back/Lens home navigation | PASS | Navigating back to Lens home worked and session rows appeared in Recent reviews. |
| Multiple sessions | PARTIAL | Multiple Lens sessions appeared in Recent reviews. Completed sessions are not reliably reopenable because of the reload/report restoration bug. |
| Lens sidebar actions/history | FAIL | Sidebar still shows Archon/chat actions (`New chat`, `Chat`, `Workshop`) and History says `No chats yet` instead of listing Lens review sessions. |

## Severity Definitions

- CRITICAL: blocks the core workflow (cannot create session, cannot view report)
- HIGH: significantly degrades the experience (data lost on reload, wrong data shown)
- MEDIUM: confusing or incorrect but workaroundable
- LOW: cosmetic or minor UX friction

## Screenshots Index

| Screenshot | Description |
|---|---|
| `step-01-lens-home.png` | Lens home page with hero, CTA, explainer, Recent reviews, framework strip |
| `step-02-new-session.png` | New session page before evidence |
| `step-03-evidence-added.png` | Evidence card after adding architecture description |
| `step-04-gap-questions-round-1.png` | Gap questions Round 1 |
| `issue-03-duplicate-gap-questions.png` | Round 2 duplicate/redundant gap questions |
| `step-06-mixed-gap-answers.png` | Mixed answered, skipped, and unanswered gap question state |
| `step-07-gap-assessment.png` | Assessment summary and ready-for-review transition |
| `step-08-ready-for-review.png` | Ready-for-review state with Start review button |
| `step-10-report-overview.png` | Completed report Overview tab |
| `step-10-tab-azure-waf.png` | Azure WAF tab |
| `step-10-tab-atam.png` | ATAM tab crash evidence |
| `issue-02-session-reload-after-report.png` | Reloaded completed session with error/no report |
| `issue-02-recent-session-open.png` | Completed session opened from Recent reviews with same error |
| `issue-lens-sidebar-archon-actions.png` | Lens sidebar showing Archon/chat actions and missing Lens session history |
| `issue-start-review-no-transition-second-session.png` | Secondary session where Start review request returned but UI stayed ready |
| `step-12-pillar-nav.png` | Pillar navigation/sidebar |
| `step-13-multiple-sessions-list.png` | Lens home with multiple Recent review rows |

## Recommended Fix Priority

1. Fix report rendering for object fields in ATAM and other report tabs by normalizing nested objects before rendering React children.
2. Fix completed-session hydration so `/lens/sessions/{id}` fetches and renders the stored report on reload or Recent-review navigation.
3. Replace Archon/chat sidebar controls in Lens with Lens-specific actions and populate History from Lens review sessions.
4. Deduplicate gap questions across rounds and suppress questions already answered by explicit evidence, including known negative evidence such as "No defined RTO or RPO."
5. Add visible review pipeline progress and disable/relabel `Start review` while a review request is in flight.

## Terminal Summary

```text
Total steps tested: 13
Happy path: 6 PASS / 2 FAIL / 3 PARTIAL
Known issues confirmed: 2
New issues found: 7
Report saved to: axiom-ui/lens-qa-report.md
```
