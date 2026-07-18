# Axiom — AI Agent Workflow Guide

This document describes the multi-agent development workflow used on the
Axiom platform. Three agents cover the full development lifecycle:
Claude for architecture and planning, Copilot for async implementation,
and Codex for interactive local work.

---

## Agent Roles

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude (Architect Agent)                                        │
│  Platform planning · cross-service decisions · debugging        │
│  GitHub MCP · Kubernetes MCP · session continuity               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ writes structured spec / issue
           ┌───────────────┴───────────────┐
           │                               │
┌──────────▼───────────┐       ┌───────────▼──────────┐
│  Copilot Agent       │       │  Codex CLI           │
│  GitHub cloud        │       │  Local terminal      │
│  Async background    │       │  Interactive         │
│  Opens PRs           │       │  You commit          │
│  Has Playwright      │       │  Same prompts work   │
│  Has Azure (OIDC)    │       │  Uses OpenAI key     │
└──────────────────────┘       └──────────────────────┘
```

---

## Agent 1 — Claude (Architect Agent)

**Where:** claude.ai or Claude Desktop

**Role:** System-wide reasoning, architecture decisions, cross-pillar
coordination, deployment debugging, QA report analysis, and session
handoffs. Claude writes the structured specs and prompts that the
other agents execute.

**Tools available:**
- GitHub MCP — reads and writes files directly to the repo
- Kubernetes MCP — `kubectl get`, `kubectl logs`, `kubectl describe`
- Web search — for current Azure/library documentation

**When to use Claude:**
- Planning a new feature or pillar
- Debugging a deployment failure
- Reviewing a QA report and deciding next action
- Writing a prompt for Copilot or Codex to execute
- Any decision that touches more than one service
- Architecture governance (ADL rules, fitness functions)

**How to start a session effectively:**

Always give Claude the current state at the start of a session:

```
Current state:
- lens-api is in CrashLoopBackOff — pgcrypto not allow-listed
- lens-agent is Running
- fix/lens-db branch has the migration fix

Task: debug lens-api crash and get it Running
```

Claude will read the relevant files via GitHub MCP, check pod logs
via Kubernetes MCP, and fix or guide the fix.

**Session handoff:**

At the end of each session ask Claude to write a session summary:

```
Summarise this session for the memory document:
1. State at start
2. What was attempted
3. What succeeded
4. What is still broken and likely cause
5. Next three actions in priority order
Format as a dated entry for SESSIONS.md
```

---

## Agent 2 — Copilot Coding Agent

**Where:** GitHub Issues → automatically creates a PR

**Role:** Async background implementation. You assign an issue to
`@copilot`, it reads the repo, writes the code, and opens a PR.
You review and merge.

**Built-in capabilities (no configuration needed):**
- Full repo read/write access
- Playwright browser automation
- GitHub API access

**Azure access (requires copilot environment setup):**
- OIDC login via `copilot-agent.yml` workflow
- `az` CLI — query pods, Key Vault, PostgreSQL, ACR
- `kubectl` — check pod status and logs

**When to use Copilot:**
- Implementing a well-specified service or component
- Writing a test suite for an existing service
- Running a Playwright UI QA session against the deployed app
- Any task you want done in the background while you work on something else
- Tasks that should produce a PR for review

**How to create a Copilot agent task:**

1. Go to `github.com/dtaylor-us/axiom` → Issues → New Issue
2. Select **"Copilot Agent Task — Implementation"** or
   **"Copilot Agent Task — QA/Testing"** template
3. Fill in the structured form
4. In the Assignees field, type `copilot` and select it
5. Submit — the agent starts automatically

**Issue quality matters.** A vague issue produces vague code.
The templates enforce the right structure. The most important fields:

- **Files to read first** — always list the reference implementation
  files (e.g. `specweaver-api/src/.../SessionService.java`) so the
  agent follows existing patterns
- **Acceptance criteria** — be explicit: `mvn verify passes`,
  `no stub implementations remain`, `coverage >= 80%`
- **Hard rules** — repeat any ADL rules that are critical for this task

**Reviewing a Copilot PR:**

Copilot opens a PR automatically. Review it like any other PR:
- Check the deviation summary table in the issue
- Run `mvn verify` or `pytest` locally if the changes are significant
- Ask Claude to review the PR by sharing the diff here

**Asking Copilot to revise:**

Comment on the PR or issue:
```
@copilot The GapElicitationService.generateNextRound() still returns
Mono.empty(). Please implement it following the pattern in
specweaver-api/src/.../DistillationService.java
```

**Playwright QA sessions:**

Create a QA issue with the URL and workflow to test:

```markdown
## Task
Run a full Playwright QA session against:
https://axiom-dev.eastus2.cloudapp.azure.com/lens

## Test the following workflow
1. Navigate to /lens — verify Lens home page loads with amber colour
2. Click "New architecture review"
3. Submit this evidence: [paste evidence text]
4. Click "Generate gap questions" — verify questions appear
5. Answer 3 questions, skip 1
6. Click "Assess gaps"
7. Click "Proceed anyway"
8. Click "Start review"
9. Wait for COMPLETE status
10. Verify report renders all tabs

## Report
Screenshot each step. Report any failures with the element
selector and expected vs actual content.
```

---

## Agent 3 — Codex CLI

**Where:** Terminal, local machine

**Role:** Interactive local implementation. Same prompts as Copilot
but runs locally, edits files directly, and you control the commit.
Use when Copilot quota is exhausted or you want faster iteration.

**Setup:**

```bash
# Install
npm install -g @openai/codex

# Set API key (pull from Key Vault to stay consistent)
export OPENAI_API_KEY="$(az keyvault secret show \
  --vault-name kv-axiom-dev-bpxn \
  --name openai-api-key \
  --query value -o tsv)"

# Run from repo root
cd /Users/derektaylor/projects/architecture-ai-assistant/ai-architect
codex
```

**When to use Codex:**
- Copilot monthly quota is running low
- You want to see file changes before committing
- Smaller focused tasks that don't need a PR
- Rapid iteration on a specific file or service
- Interactive debugging — you can guide it mid-session

**How to use Codex:**

Paste the same structured prompts used for Copilot issues directly
into the Codex terminal. The format is identical — Codex reads the
same `copilot-instructions.md` and `ARCHITECTURE.md` if you tell it to.

Start every Codex session with:
```
Read .github/copilot-instructions.md, ARCHITECTURE.md, and ADL.md
before making any changes.
```

Then paste the task description.

**After Codex finishes:**

```bash
# Review what changed
git diff --stat
git diff

# Run verification
mvn verify           # for Java services
pytest --cov=app     # for Python agents
npx vitest run       # for UI

# Commit if satisfied
git add .
git commit -m "feat(lens): implement ReviewSessionService"
git push origin main
```

---

## Memoria — Project Memory Layer

Memoria is not an agent in the Claude/Copilot/Codex sense. It is a
platform pillar that provides persistent project context to the other
three pillars. It runs automatically when a project is linked.

**What Memoria does:**
- At session start: retrieves ACTIVE DECISION and REQUIREMENT entries
  for the linked project and injects them into the pillar's LLM context
- At session close: triggers distillation of the session, extracting
  facts, decisions, and risks into the project memory store
- On demand: provides the ADR register for the project — a chronological
  record of architecture decisions with full lineage

**How to use Memoria from Claude:**
When planning work for a project, ask Claude to retrieve the current
memory context:
  "What decisions and requirements are in the Memoria store for
   the e-commerce redesign project?"

Claude can use the GitHub MCP and Kubernetes MCP to inspect the
project memory directly via the memoria-api endpoints.

---

## Token Conservation Strategy

| Situation | Use |
|-----------|-----|
| Planning, debugging, architecture | Claude |
| Copilot quota available, async task | Copilot agent |
| Copilot quota low, local task | Codex |
| UI QA against deployed app | Copilot (Playwright built in) |
| Deployment debugging | Claude (Kubernetes MCP) |
| Repo file changes | Claude (GitHub MCP) |

**Copilot quota resets monthly.** When it runs low:
- Switch implementation work to Codex
- Save Copilot for Playwright QA (harder to replicate in Codex)
- Save Claude for planning and debugging (has context from previous sessions)

---

## Standard Handoff Pattern

The cleanest workflow for a new feature:

```
1. Claude designs the feature and writes the spec
   → produces a structured GitHub issue body

2. Create a GitHub issue using the Copilot Agent template
   → paste the spec from Claude into the task description field
   → assign to @copilot

3. Copilot implements and opens a PR
   → review the PR
   → ask Copilot to revise if needed
   → if a project is linked, Memoria context is injected at session start;
      new decisions are distilled at session close

4. Claude reviews the QA report (if generated)
   → identifies any remaining issues
   → writes fixes directly via GitHub MCP or
      writes a follow-up Codex/Copilot prompt

5. Merge when satisfied
   → deploy triggers automatically via GitHub Actions
```

---

## Agent Setup Reference

### Copilot Agent — prerequisites

- [ ] GitHub Copilot subscription with coding agent enabled
  (repo Settings → Copilot → enable coding agent)
- [ ] `copilot` GitHub environment created with secrets:
  - `AZURE_CLIENT_ID` — `dc0c7e55-8c32-432e-8c5c-1429c56c006c`
  - `AZURE_TENANT_ID`
  - `AZURE_SUBSCRIPTION_ID`
  - `AZURE_RESOURCE_GROUP` — `rg-axiom-dev`
  - `AKS_CLUSTER_NAME` — `aks-axiom-dev`
  - `KEY_VAULT_NAME` — `kv-axiom-dev-bpxn`
- [ ] Federated credential added to `sp-axiom-github`:
  ```bash
  az ad app federated-credential create \
    --id dc0c7e55-8c32-432e-8c5c-1429c56c006c \
    --parameters '{
      "name": "axiom-copilot-environment",
      "issuer": "https://token.actions.githubusercontent.com",
      "subject": "repo:dtaylor-us/axiom:environment:copilot",
      "audiences": ["api://AzureADTokenExchange"]
    }'
  ```

### Claude Desktop — MCP servers

Config file: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-e", "GITHUB_HOST",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your PAT>"
      }
    },
    "kubernetes": {
      "command": "/Users/derektaylor/.nvm/versions/node/v22.22.3/bin/node",
      "args": [
        "/Users/derektaylor/.nvm/versions/node/v22.22.3/lib/node_modules/mcp-server-kubernetes/dist/index.js"
      ],
      "env": {
        "KUBECONFIG": "/Users/derektaylor/.kube/config"
      }
    }
  }
}
```

**Note:** The Kubernetes MCP must use the full Node path.
The wrapper script fails due to ES module incompatibility with
Claude Desktop's bundled Node version.

### Codex CLI — setup

```bash
npm install -g @openai/codex

# Add to ~/.zshrc
export OPENAI_API_KEY="sk-..."
```

---

## Files Added for Agent Support

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Agent behaviour rules, ADL checklist, platform topology |
| `.github/workflows/copilot-agent.yml` | Fires on issue assignment, logs in to Azure, provides platform context |
| `.github/ISSUE_TEMPLATE/copilot-agent-task.yml` | Structured implementation task template |
| `.github/ISSUE_TEMPLATE/copilot-agent-qa.yml` | Structured QA task template |
| `docs/AGENTS.md` | This file — agent workflow guide |

---

## Troubleshooting

**Copilot agent doesn't start after assignment**
- Verify coding agent is enabled: repo Settings → Copilot
- Check the issue was assigned to the `copilot` user (not a person)
- Check the workflow ran: Actions tab → Copilot Agent — Implementation

**Copilot agent produces stub implementations**
- The issue description lacked enough detail
- Add "Files to read first" pointing to a reference implementation
- Add "No stub implementations" to the acceptance criteria explicitly

**Codex doesn't follow ADL rules**
- Start the session with: `Read .github/copilot-instructions.md first`
- Paste the relevant ADL rules into the prompt directly

**Claude loses context between sessions**
- Ask Claude to write a session summary at the end of every session
- Start the next session by describing the current state explicitly
- Claude has memory of previous sessions but it may not be complete

**Kubernetes MCP disconnects**
- Confirm the full Node path is used in the config (not the wrapper)
- Run `kubectl config current-context` to confirm kubeconfig is valid
- Restart Claude Desktop with Cmd+Q (not just close the window)
