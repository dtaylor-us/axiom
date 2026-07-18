# Copilot Coding Agent Instructions

## AGENT MODE — READ THIS FIRST

When operating as a coding agent (triggered from a GitHub issue):

1. **Read before writing** — always read the files listed in the issue
   under "Files to read first" before touching any code
2. **Scope discipline** — only change what the issue asks for
3. **Branch** — create a branch named `copilot/issue-{number}-{short-description}`
4. **PR** — open a PR targeting `main` with the issue number in the title
5. **Deviation summary** — fill in the deviation summary table in the
   issue before closing it
6. **Never merge** — open the PR and stop; do not merge it yourself

When Copilot quota is exhausted, the same prompts work identically
in Codex CLI (`codex` in terminal from repo root).

---

## Output Discipline
- Do not emit full diffs unless explicitly requested.
- Summarize file changes in bullets.
- Do not paste full logs.
- For failures, include only:
  - failing command
  - failing test or step
  - likely cause
  - proposed fix

## Validation Discipline
- During implementation, run the smallest targeted test possible.
- Do not repeat full `mvn verify` loops during iteration.
- Run full verification only once before final response.

## Session Discipline
- Keep work scoped to the requested milestone.
- Recommend a new session before starting unrelated docs, tests, refactors, or cleanup.

---

## MANDATORY PRE-GENERATION CHECKS

Before writing any code, verify the change does not violate:

**ADL rules** — run mentally against every suggestion:
- ADL-001: Two services per pillar maximum (API + agent only)
- ADL-023: No JWT in localStorage or sessionStorage
- ADL-071: JWT validation in axiom-api only — never in pillar services
- ADL-xxx: No LLM calls in API services — agents only
- ADL-xxx: No PostgreSQL access in agent services — APIs only
- ADL-xxx: No cross-pillar shared libraries or in-process calls

If a suggestion violates any ADL rule, refuse it, name the rule,
and offer a compliant alternative.

---

## ALWAYS — every file generated or modified
- [ ] ddl-auto: validate — never create/update/create-drop
- [ ] No RestTemplate — always WebClient
- [ ] No hardcoded secrets — always environment variables
- [ ] No magic numbers — extract to named constants with comments
- [ ] No wildcard imports
- [ ] No dead code or commented-out blocks
- [ ] No bare `except:` in Python / no `catch(Exception)` in Java
  unless at a boundary handler
- [ ] Tests written in the same session as the code
- [ ] Coverage gate: `mvn verify` / `pytest --cov-fail-under=80` /
  `npx vitest run --coverage`
- [ ] No stub implementations — no `return []`, `return {}`, `pass`,
  `Mono.empty()`, `raise NotImplementedError` in production code

---

## PLATFORM TOPOLOGY (quick reference)

| Service            | Port | Stack                   | Status |
|--------------------|------|-------------------------|--------|
| axiom-ui           | 3000 | React 18 + Vite         | Active |
| axiom-api          | 8080 | Spring Boot WebFlux     | Active |
| archon-api         | 8081 | Spring Boot             | Active |
| archon-agent       | 8001 | FastAPI + LangGraph     | Active |
| specweaver-api     | 8082 | Spring Boot             | Active |
| specweaver-agent   | 8085 | FastAPI + LangGraph     | Active |
| lens-api           | 8083 | Spring Boot             | Active |
| lens-agent         | 8086 | FastAPI + LangGraph     | Active |

All external traffic enters through axiom-api.
Each pillar owns its own PostgreSQL database.
See ARCHITECTURE.md for full topology and constraints.

---

## LENS-SPECIFIC RULES

- Gap elicitation never blocks the user from proceeding.
- After `MAX_ROUNDS = 5`, `canProceed` is always `True`.
- Unresolved gaps become `INSUFFICIENT_INFORMATION` findings.
- Risk register is capped at `MAX_RISKS = 20`.
- Recommendations are capped at `MAX_RECOMMENDATIONS = 15`.
- `azure_waf_analysis` evaluates evidence coverage for the five Azure WAF
  pillars only: Reliability, Security, Cost, Operational Excellence,
  Performance Efficiency.
- Do not assume compliance. Missing evidence is a gap, not a pass.
- Do not reference specific Azure services or products in the assessment.

---

## PIPELINE STAGE ADDITIONS — Lens checklist

Adding a Lens stage requires updating all of these in the same change:

| File | What to update |
|------|----------------|
| `lens-agent/app/pipeline/graph.py` | Add to `ORDERED_STAGES` |
| `lens-agent/app/pipeline/nodes.py` | Implement the stage node |
| `lens-agent/app/tools/` | Add supporting tool files |
| `axiom-ui/src/components/StageProgress.tsx` | Add the Lens stage label |
| `ARCHITECTURE.md` | Update the Lens pipeline definition |
| `ADL.md` | Update governance rules if policy changes |
| `tests/unit/test_pipeline_graph.py` | Update stage count and sequencing |

---

## SECRETPROVIDERCLASS CHANGES

When adding a Key Vault secret:
1. Add via `az keyvault secret set`
2. Add to `objects` array in Helm SecretProviderClass template
3. Add to `secretObjects.data` array in the same template
4. Add to `.env.example` with a comment
5. YAML must use spaces — never tabs

---

## AGENT PATTERNS — reference implementations

When implementing a new Spring Boot service, follow the existing pattern:
- **API service**: `specweaver-api` — SessionService, EvidenceService,
  controllers, WebClient-based agent client
- **Agent service**: `specweaver-agent` — LangGraph pipeline, tool modules,
  LLM client wrapper, FastAPI routes

When implementing a new React page, follow:
- **Pillar home page**: `axiom-ui/src/views/specweaver/SpecWeaverHomePage.tsx`
- **Session page**: `axiom-ui/src/views/specweaver/SpecWeaverSessionPage.tsx`
- **API client**: `axiom-ui/src/api/specweaver.ts`

---

## END OF SESSION

Produce this table before closing:

| Check | Result | Note |
|-------|--------|------|
| ADL rules verified | PASS / VIOLATION | name the rule if violated |
| Tests written | PASS / DEFERRED | reason if deferred |
| Coverage gate | PASS / SKIP / FAIL | |
| No hardcoded secrets | PASS / VIOLATION | |
| No dead code | PASS / VIOLATION | |
| No stub implementations | PASS / VIOLATION | |
| PR opened | YES / NO | PR number if yes |
