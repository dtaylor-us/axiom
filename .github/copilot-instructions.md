# Copilot instructions for Archon

Before generating any code in this repository, read ARCHITECTURE.md at the
workspace root. That file is the authoritative architecture governance document.

Every code suggestion must conform to the rules in ARCHITECTURE.md.
If a suggestion would violate any ASSERT or REQUIRE rule, do not make it.
Instead, explain which rule it would violate and suggest a compliant alternative.

Key rules to check on every generation:
- ddl-auto must always be "validate" — never create, update, or create-drop
- Never use RestTemplate — always WebClient
- Never put LLM calls in archon-api
- Never set open-in-view to true
- Never hardcode secrets
- Always add default values to new ArchitectureContext fields
- Always emit STAGE_START and STAGE_COMPLETE events in every pipeline stage

---

## CODE QUALITY STANDARDS

These rules apply to every file generated or modified, in every phase,
without exception. Do not consider any task complete until all rules
in this section are satisfied.

---

### RULE Q-1 — Code must be commented at the right level of abstraction

Comment why, not what. A comment that restates what the code does is
noise. A comment that explains why a decision was made is signal.

#### Java
- Every public class must have a Javadoc comment explaining its
  responsibility in one or two sentences. Include @author if the
  class is non-trivial.
- Every public method must have a Javadoc comment if its purpose
  is not immediately obvious from its name and signature alone.
  Include @param, @return, and @throws where relevant.
- Non-obvious logic blocks inside methods must have an inline comment
  explaining the reasoning. Examples: timeout values, retry counts,
  magic numbers, workarounds, and deliberate design decisions.
- Do not comment self-evident code:
    // Save the message  ← bad
    messageRepo.save(message);
- Do comment decisions that have context behind them:
    // Limit to 20 messages to avoid exceeding the LLM context window.
    // Increase this only if the model and token budget allow.
    getRecentMessages(id, 20)

#### Python
- Every module must have a module-level docstring explaining what
  it contains and its role in the system.
- Every class must have a class-level docstring.
- Every public function and method must have a docstring. Use the
  following format consistently:
    """
    One sentence summary.

    Longer explanation if needed.

    Args:
        param_name: description
    Returns:
        description
    Raises:
        ExceptionType: condition
    """
- Inline comments follow the same rule as Java: explain why, not what.

#### TypeScript / React
- Every exported function, hook, and component must have a JSDoc
  comment explaining its purpose and props/parameters.
- Complex state transitions, non-obvious hook dependencies, and
  workarounds must have inline comments.
- Do not add comments to JSX markup unless the structure is
  genuinely non-obvious.

---

### RULE Q-2 — Naming must be unambiguous and consistent

- Names must describe what a thing is or does, not how it is
  implemented. manager, helper, util, handler are almost always
  wrong. processor, validator, renderer, bridge are usually right.
- Boolean variables and functions must read as a yes/no question:
    isStreaming, hasToken, shouldReiterate — correct
    streaming, token, reiterate — incorrect
- Collections must be plural: stages, messages, rules — not stageList.
- Constants must be SCREAMING_SNAKE_CASE in Java and Python.
  TypeScript constants at module scope follow the same convention.
- Avoid abbreviations unless the abbreviation is universally
  understood in the domain: url, id, jwt, llm, sse are fine.
  msg, req, res, ctx are acceptable in short-lived local variables
  only — never in class fields, method signatures, or public APIs.

---

### RULE Q-3 — Functions and methods must do one thing

- A method that does more than one conceptual thing must be split.
  The test is: if you need the word "and" to describe what a method
  does, it should be two methods.
- Maximum line count guidance (not a hard limit, but a trigger
  for review): 30 lines for Python functions, 40 lines for Java
  methods, 60 lines for React components. If you exceed these,
  add a comment explaining why extraction was not appropriate,
  or extract.
- No method should have more than three levels of nesting.
  Extract inner logic into named helper methods instead.

---

### RULE Q-4 — Error handling must be explicit and informative

#### Java
- Never catch Exception or Throwable unless you are at a
  boundary (controller advice, top-level handler). Catch the
  most specific type available.
- Every catch block must either rethrow, log with context, or
  both. An empty catch block or a catch block with only a comment
  is never acceptable.
- Log messages must include relevant context:
    log.error("Failed to persist ADL rules conversation={}",
              conversationId, e)   ← correct
    log.error("Error", e)          ← never acceptable

#### Python
- Never use bare except:. Always catch a specific exception type.
- Log all caught exceptions with enough context to diagnose the
  failure in production without access to a debugger.
- Functions that are designed to be fault-tolerant (like
  MemoryStore methods) must document this in their docstring and
  log a WARNING, never silently swallow exceptions.

#### TypeScript
- API call functions must distinguish between network errors,
  HTTP errors, and parse errors. Do not treat all failures as
  a generic "something went wrong".
- Promises must be caught. No floating promises anywhere in
  the codebase. Use void operator with a comment only when a
  fire-and-forget pattern is genuinely intentional.

---

### RULE Q-5 — No magic numbers or strings

Any literal value that encodes a business rule, limit, or
configuration must be extracted to a named constant with a comment
explaining what it represents and why it has that value.

Examples of what must be extracted:
  Java:   private static final int MAX_HISTORY_MESSAGES = 20;
          // Limit context window sent to LLM — increase only if
          // token budget and model context length allow.

  Python: MAX_CLARIFYING_QUESTIONS = 8
          # More than 8 questions is noise. The LLM is instructed
          # to return at most 8; this is a defensive trim.

  TS:     const MAX_MESSAGE_LENGTH = 32_000
          // Spring Boot validation limit on ChatRequest.message.

---

### RULE Q-6 — Imports must be clean and ordered

#### Java
- No wildcard imports (import com.example.*).
- Remove all unused imports before submitting.
- Order: Java standard library, then third-party, then internal.

#### Python
- No star imports (from module import *) except in __init__.py
  re-exports where this is deliberate.
- Order: standard library, third-party, internal. Separated by
  blank lines. Use isort conventions.

#### TypeScript
- No unused imports.
- Order: React, third-party libraries, internal types, internal
  modules. Separated by blank lines.

---

### RULE Q-7 — No dead code

- Do not leave commented-out code in committed files. If code
  is removed, remove it entirely. Version control preserves history.
- Do not leave TODO comments that describe unimplemented
  functionality unless they are linked to a known future phase.
  Acceptable: // TODO Phase 6: replace with real identity provider
  Not acceptable: // TODO: fix this later

---

## TESTING REQUIREMENTS

These rules apply at the end of every phase and whenever new code
is generated. Do not consider a phase complete until all rules in
this section pass.

---

### RULE T-1 — Write tests alongside code, not after

Every new class, function, or endpoint generated in a phase must
have corresponding tests written in the same session, before moving
on. Never defer tests to a cleanup task.

If Copilot generates a class without tests, immediately follow up
with: "Now write the tests for that class following the testing
rules in copilot-instructions.md."

---

### RULE T-2 — Test quality standards

These rules apply to every test file in every language.

#### What every test must do
- Test one behaviour per test function. If the test name needs
  "and" in it, split it into two tests.
- Assert something specific about the output, return value, or
  side effect. A test that only asserts no exception was thrown
  is not a test — it is a placeholder.
- Use descriptive names that read as a sentence describing the
  behaviour under test:
      saveMessage_persistsRoleAndContent        ← correct
      run_trimsClarifyingQuestionsToEight       ← correct
      test1 / testMethod / shouldWork           ← never acceptable
- Arrange, Act, Assert structure. Blank lines between the three
  sections. No blank lines within a section.

#### What every test must never do
- Never mock the class under test. Only mock its dependencies.
- Never use real secrets, API keys, or external service calls.
  Use placeholder values ("test-key", "test-secret") or mocks.
- Never skip tests with @Disabled, @pytest.mark.skip, or
  similar unless accompanied by a comment referencing a known
  issue and the phase in which it will be resolved.
- Never use Thread.sleep() or asyncio.sleep() to handle timing
  in tests. Use proper async/await patterns or test doubles.

#### Language-specific conventions
Java:
  - Unit tests: @ExtendWith(MockitoExtension.class). Never start
    the Spring context for a test that only needs a single class.
  - Integration tests: @SpringBootTest with Testcontainers for
    PostgreSQL. Mock external HTTP calls with MockWebServer.
  - Name test classes {ClassName}Test for units,
    {ClassName}IntegrationTest for integration tests.

Python:
  - Use pytest with pytest-asyncio. Mark async tests with
    @pytest.mark.asyncio.
  - Mock LLM calls with unittest.mock.AsyncMock. Never make
    real LLM API calls in any test.
  - Place unit tests in tests/unit/, integration tests in
    tests/integration/. Shared fixtures in tests/conftest.py.

TypeScript:
  - Use Vitest with @testing-library/react for component tests.
  - Mock fetch and external APIs — never make real HTTP calls.
  - Test user-visible behaviour, not implementation details.
    Prefer queries by role, label, and text over test IDs.

---

### RULE T-3 — Coverage requirements

A coverage gate must pass before any phase is declared complete.
Coverage is a build gate, not a suggestion.

#### Spring Boot — JaCoCo
Minimum line coverage: 80% per package.
Excludes: main application class, domain model classes, DTOs,
and simple exception classes that contain no logic.

Run: mvn verify
Report: target/site/jacoco/index.html
The build fails automatically if coverage falls below threshold.

#### Python — pytest-cov
Minimum line coverage: 80%.
Excludes: app/prompts/ directory, conftest.py files.

Run: pytest --cov=app --cov-report=term-missing --cov-fail-under=80
Exits with code 1 if below threshold.

#### TypeScript — Vitest
Minimum line coverage: 80%.
Excludes: src/types/, src/main.tsx.

Run: npx vitest run --coverage
Fails if below threshold.

---

### RULE T-4 — End-of-phase checklist

Run every command below and confirm it passes before declaring
a phase complete. Do not move to the next phase with any
failing command.

#### Spring Boot (run if phase touches archon-api)
  mvn test                          # unit tests
  mvn verify                        # integration tests + coverage

#### Python (run if phase touches archon-agent)
  pytest tests/unit/ -v             # unit tests
  pytest tests/integration/ -v      # integration tests
  pytest --cov=app \
    --cov-report=term-missing \
    --cov-fail-under=80             # coverage gate

#### TypeScript (run if phase touches axiom-ui)
  npx vitest run                    # all tests
  npx vitest run --coverage         # coverage gate

If a command fails, fix all failures before proceeding.
Do not suppress failures by modifying coverage thresholds,
adding skip annotations, or excluding additional files from
coverage without an explicit justification comment.

---

### RULE T-5 — Fix test regressions before proceeding

When a new feature changes a count, shape, or contract that
existing tests assert, update those tests immediately — in the
same session, before running any other feature work.

Do not leave broken tests in the repository with a note saying
"will fix later". A red test suite blocks the next developer who
pulls the branch.

Common sources of regressions in this codebase:
- Adding or removing a pipeline stage changes ORDERED_STAGES
  length assertions in test_pipeline_reiteration.py and stage
  count assertions in StageProgress.test.tsx and
  useConversation.test.ts.
- Adding a new API endpoint changes route count assertions in
  integration tests.
- Adding a field to ArchitectureContext with no default value
  breaks any test that constructs the model explicitly.

---

### RULE T-6 — Integration tests must use Testcontainers for PostgreSQL

Never configure integration tests to use an in-memory database
(H2). All integration tests that touch repository or service
layers must start a real PostgreSQL instance via Testcontainers.

This ensures Flyway migrations are exercised and JSONB column
types behave identically in tests and production.

The base configuration lives in AbstractIntegrationTest.java.
Every integration test class must extend it.

---

### RULE T-7 — Pipeline stage additions require atomic updates across all layers

When adding a new pipeline stage, every location that encodes the
stage list must be updated in the same commit. A partial update
will break tests in a different layer and confuse downstream
consumers.

Checklist for adding a pipeline stage:

| File | What to update |
|------|----------------|
| `archon-agent/app/pipeline/graph.py` | Add stage name to `ORDERED_STAGES` |
| `archon-agent/app/pipeline/nodes.py` | Implement the stage node function |
| `archon-agent/app/tools/registry.py` | Register the tool used by the stage |
| `axiom-ui/src/types/api.ts` | Add stage name to `PIPELINE_STAGES` |
| `axiom-ui/src/components/StageProgress.tsx` | Add label to `STAGE_LABELS` |
| `axiom/ARCHITECTURE.md` | Add stage to PIPELINE DEFINITION STAGES list |
| `tests/unit/test_pipeline_reiteration.py` | Update `len(ORDERED_STAGES)` assertion |
| `tests/unit/test_pipeline_nodes.py` | Add mock and test for the new node |
| `src/test/StageProgress.test.tsx` | Update stage count assertion |
| `src/test/useConversation.test.ts` | Update stage count assertion |

The stage name must be identical (exact snake_case string) in every
location. A mismatch between the Python name and the TypeScript name
will cause the UI progress bar to silently skip the stage.

After adding a stage, run all three test suites before declaring
the work complete:
  pytest tests/unit/ -v
  npm test
  mvn test