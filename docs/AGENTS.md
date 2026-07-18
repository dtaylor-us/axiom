# Axiom Agent Workflow Guide

## Standard Handoff Pattern

1. Claude designs the feature and writes the spec

2. Create a GitHub issue using the Copilot Agent template

3. Copilot implements and opens a PR
   — if a project is linked, Memoria context is injected at
     session start; new decisions are distilled at session close

4. Claude reviews the QA report

5. Merge when satisfied → deploy triggers automatically

## Agent Roles

## Agent 1 — Claude

Claude owns planning, requirements shaping, architecture reasoning, and review.
Use Claude to clarify intent, identify constraints, and decide whether a change
is ready for implementation.

## Agent 2 — Copilot

Copilot owns implementation from a scoped GitHub issue. It should follow
`ARCHITECTURE.md`, `ADL.md`, and `.github/copilot-instructions.md` before
generating code.

## Agent 3 — Codex

Codex owns repository-local implementation, review, debugging, and verification.
Use Codex when the task requires reading the working tree, editing files, running
tests, or producing a concrete patch.

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
