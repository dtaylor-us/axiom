import { useMemo } from 'react';
import { useStore } from '../store/useStore';
import { useArchitecture } from './useArchitecture';
import { useGovernance } from './useGovernance';
import { useTactics } from './useTactics';
import { useBuyVsBuild } from './useBuyVsBuild';
import type {
  Component,
  Interaction,
  FmeaEntry,
  AdlRule,
  Weakness,
  BuyVsBuildDecision,
  TradeOffDecision,
  AdlDocument,
  ImprovementRecommendation,
  TacticRecommendation,
} from '../types/api';

// ---------------------------------------------------------------------------
// ADL field compatibility
// ---------------------------------------------------------------------------
// The Python archon-agent serialises AdlBlock with field "adl_id", but the
// TypeScript AdlRule interface (and older pipeline versions) uses "rule_id".
// This helper reads whichever key is present so the UI is resilient to both.
type RawAdlRule = AdlRule & Record<string, unknown>;

function resolveAdlId(r: RawAdlRule): string {
  return (r.rule_id || (r['adl_id'] as string) || '').trim();
}

function resolveAdlSubject(r: RawAdlRule): string {
  if (r.subject) return r.subject;
  const meta = r['metadata'] as Record<string, unknown> | undefined;
  return (meta?.['description'] as string) || '';
}

function resolveAdlStatement(r: RawAdlRule): string {
  if (r.statement) return r.statement;
  return (r['adl_source'] as string) || '';
}

function resolveAdlCategory(r: RawAdlRule): string {
  if (r.category) return r.category;
  return (r['characteristic_enforced'] as string) || '';
}

function resolveAdlRationale(r: RawAdlRule): string {
  if (r.rationale) return r.rationale;
  const meta = r['metadata'] as Record<string, unknown> | undefined;
  return (meta?.['prompt'] as string) || '';
}

function resolveAdlSource(r: RawAdlRule): string {
  return (r['adl_source'] as string) || '';
}

function resolveAdlEnforcement(r: RawAdlRule): string {
  return (r['enforcement_level'] as string) || r.validation_hint?.enforcement_level || 'soft';
}

// ---------------------------------------------------------------------------
// Public interface
// ---------------------------------------------------------------------------

export interface ArchDocData {
  systemTitle: string;
  systemDescription: string;
  conversationTitle: string;
  stakeholderConcerns: { role: string; concerns: string[] }[];
  glossaryTerms: { term: string; definition: string }[];
  sloTargets: { characteristic: string; target: string; tactic: string }[];

  componentDiagram: string | null;
  deploymentDiagram: string | null;
  components: Component[];
  fmeaByComponent: Record<string, FmeaEntry[]>;
  moduleAdlRules: AdlRule[];

  sequencePrimaryDiagram: string | null;
  sequenceErrorDiagram: string | null;
  interactions: Interaction[];
  scenarios: { stimulus: string; response: string; measures: string; characteristic: string }[];
  connectorAdlRules: AdlRule[];

  buyVsBuildDecisions: BuyVsBuildDecision[];
  buildSequence: { component: string; phase: number; reason: string; owner: string }[];
  allocationAdlRules: AdlRule[];

  adlDocument: AdlDocument | null;
  allAdlRules: AdlRule[];
  weaknesses: Weakness[];
  fmeaAll: FmeaEntry[];
  improvementRecommendations: ImprovementRecommendation[];
  tradeOffs: TradeOffDecision[];
  tactics: TacticRecommendation[];

  fullPackageMarkdown: string;
  overviewMarkdown: string;
  moduleViewMarkdown: string;
  ccViewMarkdown: string;
  allocationViewMarkdown: string;
  riskMarkdown: string;
  exportFilename: string;

  loading: boolean;
  error: string | null;
  hasData: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function slugifyTitle(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function getCurrentDate(): string {
  return new Date().toISOString().split('T')[0];
}

/** Derive meaningful system title from the architecture style and domain. */
function resolveSystemTitle(style: string, domain: string, conversationId: string): string {
  if (domain && domain.toLowerCase() !== 'unknown') return domain;
  if (style && style.toLowerCase() !== 'unknown') return `${style} System`;
  return conversationId ? `Architecture ${conversationId.slice(0, 8)}` : 'Architecture';
}

/** Map stakeholder roles to characteristics they care about. */
const ROLE_CHARACTERISTIC_PATTERNS: { role: string; patterns: string[] }[] = [
  { role: 'Development team', patterns: ['maintainability', 'testability', 'deployability', 'modularity', 'simplicity', 'agility'] },
  { role: 'Operations team', patterns: ['availability', 'recoverability', 'reliability', 'fault_tolerance', 'observability', 'operational'] },
  { role: 'Security team', patterns: ['security', 'auth', 'compliance', 'audit', 'encryption', 'confidentiality'] },
  { role: 'Product owners', patterns: ['scalability', 'performance', 'usability', 'functionality', 'business', 'cost', 'time_to_market'] },
  { role: 'Architects', patterns: ['extensibility', 'evolvability', 'interoperability', 'portability', 'elasticity'] },
];

function buildStakeholderConcerns(
  characteristics: string[],
): { role: string; concerns: string[] }[] {
  const roleMap = new Map<string, Set<string>>();
  ROLE_CHARACTERISTIC_PATTERNS.forEach(({ role, patterns }) => {
    characteristics.forEach((c) => {
      const lower = c.toLowerCase();
      if (patterns.some((p) => lower.includes(p))) {
        if (!roleMap.has(role)) roleMap.set(role, new Set());
        roleMap.get(role)!.add(c);
      }
    });
  });
  // Ensure every characteristic is assigned to at least Product owners
  const assigned = new Set(Array.from(roleMap.values()).flatMap((s) => Array.from(s)));
  characteristics.forEach((c) => {
    if (!assigned.has(c)) {
      if (!roleMap.has('Product owners')) roleMap.set('Product owners', new Set());
      roleMap.get('Product owners')!.add(c);
    }
  });
  return Array.from(roleMap.entries())
    .map(([role, concerns]) => ({ role, concerns: Array.from(concerns) }))
    .sort((a, b) => a.role.localeCompare(b.role));
}

/**
 * Extract SLO targets from tactics and trade-offs.
 * Tactics with measurable concreteApplication descriptions provide the targets.
 */
function buildSloTargets(
  tactics: TacticRecommendation[],
  tradeOffs: TradeOffDecision[],
): { characteristic: string; target: string; tactic: string }[] {
  const seen = new Set<string>();
  const targets: { characteristic: string; target: string; tactic: string }[] = [];

  // Extract measurable targets from tactic concrete applications
  tactics
    .filter((t) => t.priority === 'critical' && !t.alreadyAddressed)
    .forEach((t) => {
      const app = t.concreteApplication || '';
      // Look for patterns like "< 200ms", ">= 99.9%", "within 5 minutes"
      const hasTarget = /[\d.]+\s*(ms|seconds?|minutes?|hours?|%|rpm|rps|tps)/i.test(app);
      const key = `${t.characteristicName}:${t.tacticName}`;
      if (!seen.has(key) && (hasTarget || app.length > 20)) {
        seen.add(key);
        targets.push({
          characteristic: t.characteristicName,
          target: hasTarget ? app.replace(/\n/g, ' ').slice(0, 120) : 'See tactic implementation',
          tactic: t.tacticName,
        });
      }
    });

  // Fill from trade-offs where measurable context exists
  tradeOffs.forEach((to) => {
    (to.optimises_characteristics ?? []).forEach((c) => {
      const key = `tradeoff:${c}`;
      if (!seen.has(key)) {
        seen.add(key);
        targets.push({
          characteristic: c,
          target: to.acceptable_because || to.recommendation,
          tactic: `Trade-off: ${to.decision_id}`,
        });
      }
    });
  });

  return targets.slice(0, 15);
}

/**
 * Build QA scenarios from tactics instead of using interaction proxies.
 * Each critical tactic defines a real quality scenario.
 */
function buildQaScenarios(
  tactics: TacticRecommendation[],
  interactions: Interaction[],
): { stimulus: string; response: string; measures: string; characteristic: string }[] {
  const scenarios: { stimulus: string; response: string; measures: string; characteristic: string }[] = [];

  // Prefer tactic-derived scenarios for critical tactics
  const criticalTactics = tactics.filter((t) => t.priority === 'critical');
  criticalTactics.slice(0, 8).forEach((t) => {
    const app = t.concreteApplication || '';
    const examples = t.implementationExamples || [];
    // Extract a measurable target if present, otherwise use the application description
    const measureMatch = app.match(/([\d.]+\s*(ms|seconds?|minutes?|hours?|%|rpm|rps|tps)[^.]*\.?)/i);
    const measure = measureMatch?.[0] || (app.slice(0, 80) + (app.length > 80 ? '…' : ''));
    scenarios.push({
      characteristic: t.characteristicName,
      stimulus: `System receives load / event affecting **${t.characteristicName}**`,
      response: `Apply ${t.tacticName}: ${examples[0] || app.slice(0, 60)}`,
      measures: measure || 'Meets defined SLO threshold',
    });
  });

  // Fall back to interaction-based scenarios if tactics are sparse
  if (scenarios.length < 3) {
    interactions.slice(0, 5).forEach((i) => {
      scenarios.push({
        characteristic: 'runtime quality',
        stimulus: `${i.from} initiates ${i.protocol} call to ${i.to}`,
        response: `${i.to} processes request: ${i.purpose}`,
        measures: 'Completes within agreed SLA; circuit breaker engaged on failure',
      });
    });
  }

  return scenarios;
}

/**
 * Determine build sequence by sorting components with "build" recommendation first,
 * then "adopt", then "buy". Within each tier, sort by how many others depend on them.
 */
function buildConstructionSequence(
  components: Component[],
  buyVsBuildDecisions: BuyVsBuildDecision[],
  interactions: Interaction[],
): { component: string; phase: number; reason: string; owner: string }[] {
  // Determine recommendation per component
  const decisionMap = new Map<string, BuyVsBuildDecision>();
  buyVsBuildDecisions.forEach((d) => {
    decisionMap.set(d.componentName.toLowerCase(), d);
  });

  // Count how many outbound dependencies each component has
  const dependedOnCount = new Map<string, number>();
  components.forEach((c) => dependedOnCount.set(c.name, 0));
  interactions.forEach((i) => {
    const count = dependedOnCount.get(i.to) ?? 0;
    dependedOnCount.set(i.to, count + 1);
  });

  const result: { component: string; phase: number; reason: string; owner: string }[] = [];

  const getPhase = (c: Component): { phase: number; reason: string; owner: string } => {
    const rec = decisionMap.get(c.name.toLowerCase())?.recommendation;
    const ownership = c.ownership || '';
    if (ownership.includes('external') || rec === 'buy') {
      return { phase: 1, reason: 'External/purchased — configure and integrate first', owner: 'Vendor/Procurement' };
    }
    if (rec === 'adopt' || ownership.includes('adopted')) {
      return { phase: 1, reason: 'Adopted platform — provision and configure in foundation sprint', owner: 'Platform team' };
    }
    // High-dependency components (others depend on them) are phase 2
    const depCount = dependedOnCount.get(c.name) ?? 0;
    if (depCount >= 2) {
      return { phase: 2, reason: `Core dependency — ${depCount} other components rely on this`, owner: 'Internal team' };
    }
    return { phase: 3, reason: 'Feature component — build after foundation is stable', owner: 'Internal team' };
  };

  components.forEach((c) => {
    const { phase, reason, owner } = getPhase(c);
    result.push({ component: c.name, phase, reason, owner });
  });

  return result.sort((a, b) => a.phase - b.phase || a.component.localeCompare(b.component));
}

// ---------------------------------------------------------------------------
// Section builders
// ---------------------------------------------------------------------------

function buildOverviewMarkdown(
  systemTitle: string,
  architectureStyle: string,
  stakeholderConcerns: { role: string; concerns: string[] }[],
  glossary: { term: string; definition: string }[],
  sloTargets: { characteristic: string; target: string; tactic: string }[],
  governanceScore: number | null,
): string {
  const lines: string[] = [
    '# Architecture Documentation Package',
    `**System:** ${systemTitle}`,
    `**Generated:** ${getCurrentDate()}`,
    `**Architecture style:** ${architectureStyle}`,
    '',
    '## Purpose and Scope',
    `This document describes the architecture of **${systemTitle}** using the SEI Views-and-Beyond`,
    `framework. It covers the Module View (structural decomposition), Component & Connector View`,
    `(runtime behaviour), Allocation View (deployment and team assignments), and Risk & Decision Log.`,
    `Use this document to understand the system structure, make implementation decisions, and plan team work.`,
    '',
  ];

  if (governanceScore !== null) {
    lines.push(`> **Governance Score:** ${governanceScore}/100 — see Risk & Decisions for improvement recommendations.`, '');
  }

  lines.push('## Stakeholders and Concerns', '');
  lines.push('| Stakeholder | Concerns |');
  lines.push('|---|---|');
  if (stakeholderConcerns.length > 0) {
    stakeholderConcerns.forEach(({ role, concerns }) => {
      lines.push(`| ${role} | ${concerns.join(', ')} |`);
    });
  } else {
    lines.push('| Product owner | Core Service |');
  }

  lines.push('', '## Reading Guide', '');
  lines.push('| Stakeholder | Start here | Then read |');
  lines.push('|---|---|---|');
  lines.push('| Development team | Module View | C&C View, ADL rules |');
  lines.push('| Operations team | Allocation View | C&C View, Risk section |');
  lines.push('| Architects | Module View | C&C View, Variability |');
  lines.push('| Product owners | Overview | Rationale |');
  lines.push('| Security team | C&C View | Risk section |');

  if (sloTargets.length > 0) {
    lines.push('', '## Quality Objectives (SLO/SLA Targets)', '');
    lines.push('These targets are derived from architecture characteristics and must be met by the implementation.');
    lines.push('');
    lines.push('| Characteristic | Target / Obligation | Architecture Tactic |');
    lines.push('|---|---|---|');
    sloTargets.forEach(({ characteristic, target, tactic }) => {
      lines.push(`| ${characteristic} | ${target} | ${tactic} |`);
    });
  }

  if (glossary.length > 0) {
    lines.push('', '## Glossary', '');
    glossary.forEach(({ term, definition }) => {
      lines.push(`**${term}:** ${definition}`);
    });
  }

  return lines.join('\n');
}

function buildModuleViewMarkdown(
  componentDiagram: string | null,
  components: Component[],
  fmeaByComponent: Record<string, FmeaEntry[]>,
  tradeOffs: TradeOffDecision[],
  moduleAdlRules: RawAdlRule[],
  weaknesses: Weakness[],
  tactics: TacticRecommendation[],
  buyVsBuildDecisions: BuyVsBuildDecision[],
): string {
  const lines: string[] = [
    '# Module View',
    '',
    '## Primary Presentation',
  ];

  if (componentDiagram) {
    lines.push('```mermaid');
    lines.push(componentDiagram);
    lines.push('```');
  } else {
    lines.push('> Diagram not available — re-run analysis to generate Mermaid component diagram.');
  }

  if (components.length > 0) {
    lines.push('');
    lines.push('## Element Catalog');
    lines.push('');
    lines.push('| Element | Type | Responsibility | Technology | Ownership | Risks |');
    lines.push('|---|---|---|---|---|---|');
    components.forEach((c) => {
      const risks = fmeaByComponent[c.name]
        ?.slice(0, 2)
        .map((r) => r.failure_mode)
        .join('; ') || '—';
      const ownership = c.ownership || '—';
      lines.push(
        `| ${c.name} | ${c.type || '—'} | ${c.responsibility} | ${c.technology} | ${ownership} | ${risks} |`
      );
    });
  }

  // Implementation guidance per component
  const decisionMap = new Map<string, BuyVsBuildDecision>();
  buyVsBuildDecisions.forEach((d) => decisionMap.set(d.componentName.toLowerCase(), d));

  if (components.length > 0) {
    lines.push('');
    lines.push('## Component Implementation Guidance');
    lines.push('');
    lines.push('> Each entry describes how the component should be built, what patterns to apply, and acceptance criteria.');
    lines.push('');

    components.forEach((c) => {
      lines.push(`### ${c.name}`);
      lines.push('');
      lines.push(`**Technology:** ${c.technology}`);

      const decision = decisionMap.get(c.name.toLowerCase());
      if (decision) {
        const action = decision.recommendation === 'build'
          ? `Build internally — this is a core differentiator`
          : decision.recommendation === 'buy'
            ? `Procure **${decision.recommendedSolution}** — avoid custom implementation`
            : `Adopt **${decision.recommendedSolution}** — configure and integrate`;
        lines.push(`**Sourcing decision:** ${action}`);
        if (decision.rationale) lines.push(`**Why:** ${decision.rationale}`);
        if (decision.integrationEffort && decision.recommendation !== 'build') {
          lines.push(`**Integration effort:** ${decision.integrationEffort}`);
        }
        if (decision.vendorLockInRisk && decision.recommendation === 'buy') {
          lines.push(`**Vendor lock-in risk:** ${decision.vendorLockInRisk} — ${
            decision.vendorLockInRisk === 'high'
              ? 'define an abstraction layer to reduce coupling'
              : 'monitor for contractual risks'
          }`);
        }
      }

      // Find tactics relevant to this component
      const relevantTactics = tactics.filter(
        (t) => !t.alreadyAddressed && (
          t.concreteApplication?.toLowerCase().includes(c.name.toLowerCase()) ||
          (c.responsibility?.toLowerCase().includes(t.characteristicName?.toLowerCase() || ''))
        )
      ).slice(0, 3);

      if (relevantTactics.length > 0) {
        lines.push('');
        lines.push('**Architecture tactics to apply:**');
        relevantTactics.forEach((t) => {
          lines.push(`- **${t.tacticName}** (${t.characteristicName}): ${t.concreteApplication?.slice(0, 100) || t.description}`);
        });
      }

      lines.push('');
    });
  }

  if (tradeOffs.length > 0) {
    lines.push('## Variability Guide');
    lines.push('');
    lines.push('> This section documents key design decisions and when to reconsider them.');
    lines.push('');
    tradeOffs.forEach((t) => {
      lines.push(`### ${t.decision_id}: ${t.decision}`);
      lines.push('');
      lines.push(`**Chosen approach:** ${t.recommendation}`);
      if ((t.optimises_characteristics ?? []).length > 0) {
        lines.push(`**Optimises:** ${(t.optimises_characteristics ?? []).join(', ')}`);
      }
      if ((t.sacrifices_characteristics ?? []).length > 0) {
        lines.push(`**Trade-off (sacrifices):** ${(t.sacrifices_characteristics ?? []).join(', ')}`);
      }
      if (t.acceptable_because) lines.push(`**Why acceptable:** ${t.acceptable_because}`);
      if (t.context_dependency) lines.push(`**When to reconsider:** ${t.context_dependency}`);
      if ((t.options_considered ?? []).length > 0) {
        lines.push('**Alternatives rejected:**');
        (t.options_considered ?? []).forEach((o) => {
          lines.push(`- ~~${o.option}~~ — ${o.rejected_because}`);
        });
      }
      lines.push('');
    });
  }

  if (moduleAdlRules.length > 0) {
    lines.push('## Module ADL Constraints');
    lines.push('');
    lines.push('> These rules govern structural decomposition and must be enforced by fitness functions.');
    lines.push('');
    moduleAdlRules.forEach((r) => {
      const id = resolveAdlId(r);
      const subject = resolveAdlSubject(r);
      const enforcement = resolveAdlEnforcement(r);
      lines.push(`### [${id}] ${subject}`);
      lines.push(`**Enforcement:** ${enforcement === 'hard' ? '🔴 Hard (CI must fail on violation)' : '🟡 Soft (warning only)'}`);
      lines.push('');
    });
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((w) => {
      lines.push(`- **${w.title}** (Severity ${w.severity}/10): ${w.description}`);
    });
    lines.push('');
  }

  return lines.join('\n');
}

function buildCCViewMarkdown(
  sequenceDiagram: string | null,
  interactions: Interaction[],
  scenarios: { stimulus: string; response: string; measures: string; characteristic: string }[],
  connectorAdlRules: RawAdlRule[],
  fmeaAll: FmeaEntry[],
  sloTargets: { characteristic: string; target: string; tactic: string }[],
): string {
  const lines: string[] = [
    '# Component & Connector View',
    '',
    '## Primary Presentation',
  ];

  if (sequenceDiagram) {
    lines.push('```mermaid');
    lines.push(sequenceDiagram);
    lines.push('```');
  } else {
    lines.push('> Sequence diagram not available — re-run analysis to generate.');
  }

  if (interactions.length > 0) {
    lines.push('');
    lines.push('## Runtime Element Catalog');
    lines.push('');
    lines.push('| Connector | From | To | Protocol | Purpose | Failure Mode |');
    lines.push('|---|---|---|---|---|---|');
    interactions.forEach((i) => {
      const failureMode = fmeaAll
        .filter((f) => f.component === i.from || f.component === i.to)
        .map((f) => f.failure_mode)
        .slice(0, 1)
        .join('; ') || '—';
      lines.push(`| ${i.from}→${i.to} | ${i.from} | ${i.to} | \`${i.protocol}\` | ${i.purpose} | ${failureMode} |`);
    });
  }

  if (sloTargets.length > 0) {
    lines.push('');
    lines.push('## Service Level Objectives');
    lines.push('');
    lines.push('> These SLOs must be measured and monitored in production. Implement observability before go-live.');
    lines.push('');
    lines.push('| Characteristic | SLO Target | Architecture Tactic |');
    lines.push('|---|---|---|');
    sloTargets.forEach(({ characteristic, target, tactic }) => {
      lines.push(`| ${characteristic} | ${target} | ${tactic} |`);
    });
  }

  if (scenarios.length > 0) {
    lines.push('');
    lines.push('## Quality Attribute Scenarios');
    lines.push('');
    lines.push('> These scenarios define testable acceptance criteria. Each must be validated before production release.');
    lines.push('');
    scenarios.forEach((s, idx) => {
      lines.push(`### Scenario ${idx + 1}: ${s.characteristic}`);
      lines.push(`- **Stimulus:** ${s.stimulus}`);
      lines.push(`- **Response:** ${s.response}`);
      lines.push(`- **Measures:** ${s.measures}`);
      lines.push('');
    });
  }

  if (connectorAdlRules.length > 0) {
    lines.push('## Connector ADL Constraints');
    lines.push('');
    lines.push('> These rules govern runtime communication protocols and must pass in CI.');
    lines.push('');
    connectorAdlRules.forEach((r) => {
      const id = resolveAdlId(r);
      const subject = resolveAdlSubject(r);
      const statement = resolveAdlStatement(r);
      const enforcement = resolveAdlEnforcement(r);
      lines.push(`### [${id}] ${subject}`);
      lines.push(`**Enforcement:** ${enforcement === 'hard' ? '🔴 Hard' : '🟡 Soft'}`);
      if (statement) {
        lines.push('');
        lines.push('```adl');
        lines.push(statement);
        lines.push('```');
      }
      lines.push('');
    });
  }

  if (fmeaAll.length > 0) {
    lines.push('## Risk Analysis (FMEA)');
    lines.push('');
    lines.push('| ID | Failure Mode | Component | Severity | Occurrence | Detection | RPN | Recommended Action |');
    lines.push('|---|---|---|---|---|---|---|---|');
    [...fmeaAll]
      .sort((a, b) => b.rpn - a.rpn)
      .slice(0, 10)
      .forEach((e) => {
        lines.push(`| ${e.id} | ${e.failure_mode} | ${e.component} | ${e.severity} | ${e.occurrence} | ${e.detection} | **${e.rpn}** | ${e.recommended_action} |`);
      });
  }

  return lines.join('\n');
}

function buildAllocationViewMarkdown(
  deploymentDiagram: string | null,
  buyVsBuildDecisions: BuyVsBuildDecision[],
  components: Component[],
  allocationAdlRules: RawAdlRule[],
  weaknesses: Weakness[],
  buildSequence: { component: string; phase: number; reason: string; owner: string }[],
): string {
  const lines: string[] = [
    '# Allocation View',
    '',
    '## Deployment View',
  ];

  if (deploymentDiagram) {
    lines.push('```mermaid');
    lines.push(deploymentDiagram);
    lines.push('```');
  } else if (components.length > 0) {
    lines.push('');
    lines.push('| Component | Type | Deployment Target | Ownership |');
    lines.push('|---|---|---|---|');
    components.forEach((c) => {
      const ownership = c.ownership || '—';
      const deployTarget = ownership === 'bought-saas' ? 'bought-saas'
        : ownership === 'adopted-platform' ? 'adopted-platform'
          : 'enterprise-built';
      lines.push(`| ${c.name} | ${c.type || '—'} | ${deployTarget} | ${ownership} |`);
    });
  }

  // Work assignment with deduplication
  const seenComponents = new Set<string>();
  const uniqueDecisions = buyVsBuildDecisions.filter((d) => {
    const key = d.componentName.toLowerCase();
    if (seenComponents.has(key)) return false;
    seenComponents.add(key);
    return true;
  });

  if (uniqueDecisions.length > 0) {
    lines.push('');
    lines.push('## Work Assignment');
    lines.push('');
    lines.push('| Component | Owner | Decision | Solution | Differentiator | Lock-in Risk |');
    lines.push('|---|---|---|---|---|---|');
    uniqueDecisions.forEach((d) => {
      const owner = d.recommendation === 'build'
        ? 'Internal team'
        : d.recommendation === 'buy'
          ? 'Vendor/Procurement'
          : 'Platform team';
      const differentiator = d.isCoreeDifferentiator ? '✅ Core' : '—';
      lines.push(
        `| ${d.componentName} | ${owner} | ${d.recommendation} | ${d.recommendedSolution || '—'} | ${differentiator} | ${d.vendorLockInRisk || '—'} |`
      );
    });
  }

  // Build sequence / sprint planning
  if (buildSequence.length > 0) {
    lines.push('');
    lines.push('## Build Sequence');
    lines.push('');
    lines.push('> Recommended construction order to minimise blocked work. Phase 1 enables Phase 2; Phase 2 enables Phase 3.');
    lines.push('');

    const phases = [1, 2, 3];
    phases.forEach((phase) => {
      const phaseItems = buildSequence.filter((s) => s.phase === phase);
      if (phaseItems.length === 0) return;
      const phaseName = phase === 1 ? 'Foundation (Configure & Integrate External Services)'
        : phase === 2 ? 'Core Services (Build High-Dependency Components)'
          : 'Feature Services (Build Remaining Components)';
      lines.push(`### Phase ${phase}: ${phaseName}`);
      lines.push('');
      phaseItems.forEach((s) => {
        lines.push(`- **${s.component}** — ${s.reason} *(${s.owner})*`);
      });
      lines.push('');
    });
  }

  // Team formation guidance
  if (uniqueDecisions.length > 0) {
    const buildCount = uniqueDecisions.filter((d) => d.recommendation === 'build').length;
    const buyCount = uniqueDecisions.filter((d) => d.recommendation === 'buy').length;
    const adoptCount = uniqueDecisions.filter((d) => d.recommendation === 'adopt').length;

    lines.push('## Team Formation Guidance');
    lines.push('');
    lines.push('Based on the sourcing decisions above:');
    lines.push('');
    if (buildCount > 0) {
      lines.push(`- **${buildCount} component(s) to build**: Assign to internal engineering squads. Recommend cross-functional squads (frontend + backend + QA) owning each service end-to-end.`);
    }
    if (buyCount > 0) {
      lines.push(`- **${buyCount} component(s) to buy**: Assign procurement/vendor selection to Technical Lead + Procurement. Plan integration tasks for internal team.`);
    }
    if (adoptCount > 0) {
      lines.push(`- **${adoptCount} component(s) to adopt**: Assign to Platform/Infrastructure team for provisioning and configuration. Internal teams own the integration layer.`);
    }
    lines.push('');
  }

  if (allocationAdlRules.length > 0) {
    lines.push('## Deployment ADL Constraints');
    lines.push('');
    allocationAdlRules.forEach((r) => {
      const id = resolveAdlId(r);
      const subject = resolveAdlSubject(r);
      const enforcement = resolveAdlEnforcement(r);
      lines.push(`- **[${id}] ${subject}** (${enforcement === 'hard' ? '🔴 Hard' : '🟡 Soft'})`);
    });
    lines.push('');
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((w) => {
      lines.push(`- **${w.title}** (Severity ${w.severity}/10): ${w.mitigation}`);
    });
    lines.push('');
  }

  return lines.join('\n');
}

function buildRiskMarkdown(
  allAdlRules: RawAdlRule[],
  weaknesses: Weakness[],
  fmeaAll: FmeaEntry[],
  improvementRecommendations: ImprovementRecommendation[],
  tactics: TacticRecommendation[],
): string {
  const lines: string[] = ['# Risk and Decision Log', ''];

  // Architecture Decision Records
  if (allAdlRules.length > 0) {
    lines.push('## Architecture Decision Records');
    lines.push('');
    lines.push('> ADRs capture key architectural decisions, their context, and consequences. Each maps to a fitness function.');
    lines.push('');
    allAdlRules.forEach((r) => {
      const id = resolveAdlId(r);
      const subject = resolveAdlSubject(r);
      const statement = resolveAdlStatement(r);
      const category = resolveAdlCategory(r);
      const rationale = resolveAdlRationale(r);
      const enforcement = resolveAdlEnforcement(r);
      const adlSource = resolveAdlSource(r);

      lines.push(`### ADR-${id || 'unknown'}: ${subject || 'Architecture Constraint'}`);
      lines.push('');
      lines.push(`**Status:** Accepted`);
      lines.push(`**Category:** ${category || 'General'}`);
      lines.push(`**Enforcement:** ${enforcement === 'hard' ? '🔴 Hard (CI must fail)' : '🟡 Soft (warning)'}`);
      lines.push('');

      lines.push('#### Context');
      if (rationale) {
        lines.push(rationale);
      } else {
        lines.push(`This constraint enforces the \`${category || 'architecture'}\` quality characteristic across the codebase.`);
      }
      lines.push('');

      lines.push('#### Decision');
      if (statement) {
        lines.push(statement);
      } else {
        lines.push(`Apply constraint as defined in ADL rule ${id}.`);
      }
      lines.push('');

      if (adlSource) {
        lines.push('#### Fitness Function');
        lines.push('```adl');
        lines.push(adlSource);
        lines.push('```');
        lines.push('');
      }

      const optimises = (r.optimises_characteristics ?? []) as string[];
      if (optimises.length > 0) {
        lines.push('#### Consequences');
        lines.push(`Enforcing this rule protects: ${optimises.join(', ')}.`);
        lines.push(`Violation risk: degraded ${optimises[0]} with potential for cascading failures.`);
        lines.push('');
      }
    });
  }

  // Unified risk register
  const risksMap = new Map<string, { severity: number; entry: string }>();

  weaknesses.forEach((w) => {
    risksMap.set(w.id, {
      severity: w.severity,
      entry: `| ${w.id} | ${w.title} | ${w.component_affected} | ${w.severity}/10 | Weakness | ${w.mitigation} |`,
    });
  });

  fmeaAll.forEach((f) => {
    const severity = Math.min(10, Math.round(f.rpn / 10));
    risksMap.set(f.id, {
      severity,
      entry: `| ${f.id} | ${f.failure_mode} | ${f.component} | ${severity}/10 | FMEA (RPN ${f.rpn}) | ${f.recommended_action} |`,
    });
  });

  if (risksMap.size > 0) {
    lines.push('## Risk Register');
    lines.push('');
    lines.push('| ID | Risk | Component | Severity | Type | Mitigation |');
    lines.push('|---|---|---|---|---|---|');
    Array.from(risksMap.values())
      .sort((a, b) => b.severity - a.severity)
      .forEach(({ entry }) => lines.push(entry));
    lines.push('');
  }

  // Architecture fitness functions checklist
  if (allAdlRules.length > 0) {
    lines.push('## Architecture Fitness Functions Checklist');
    lines.push('');
    lines.push('> Use this checklist during sprint reviews and before release to validate architectural integrity.');
    lines.push('');
    allAdlRules.forEach((r) => {
      const id = resolveAdlId(r);
      const subject = resolveAdlSubject(r);
      const enforcement = resolveAdlEnforcement(r);
      const category = resolveAdlCategory(r);
      const requires = (r['metadata'] as Record<string, unknown> | undefined)?.['requires'] as string || r.validation_hint?.type || '';
      lines.push(`- [ ] **[${id}] ${subject}** — ${enforcement === 'hard' ? '🔴 Hard / CI' : '🟡 Soft'} · ${category}${requires ? ` · Tooling: \`${requires}\`` : ''}`);
    });
    lines.push('');
  }

  // Unaddressed critical tactics
  const criticalUnaddressed = tactics.filter((t) => t.priority === 'critical' && !t.alreadyAddressed);
  if (criticalUnaddressed.length > 0) {
    lines.push('## Critical Tactics Not Yet Implemented');
    lines.push('');
    lines.push('> These tactics must be implemented before production readiness. Assign to sprint backlog immediately.');
    lines.push('');
    lines.push('| Tactic | Characteristic | Effort | Application |');
    lines.push('|---|---|---|---|');
    criticalUnaddressed.slice(0, 10).forEach((t) => {
      lines.push(`| ${t.tacticName} | ${t.characteristicName} | ${t.effort} | ${(t.concreteApplication || t.description).slice(0, 80)} |`);
    });
    lines.push('');
  }

  // Improvement roadmap
  if (improvementRecommendations.length > 0) {
    lines.push('## Improvement Roadmap');
    lines.push('');
    improvementRecommendations.forEach((r) => {
      lines.push(`### [${r.priority}] ${r.area}`);
      lines.push(r.recommendation);
      if (r.requires_reiteration) {
        lines.push('');
        lines.push('> ⚠️ *Requires architecture reiteration before this can be resolved.*');
      }
      lines.push('');
    });
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const EMPTY_DOC: ArchDocData = {
  systemTitle: 'Architecture',
  systemDescription: '',
  conversationTitle: '',
  stakeholderConcerns: [],
  glossaryTerms: [],
  sloTargets: [],
  componentDiagram: null,
  deploymentDiagram: null,
  components: [],
  fmeaByComponent: {},
  moduleAdlRules: [],
  sequencePrimaryDiagram: null,
  sequenceErrorDiagram: null,
  interactions: [],
  scenarios: [],
  connectorAdlRules: [],
  buyVsBuildDecisions: [],
  buildSequence: [],
  allocationAdlRules: [],
  adlDocument: null,
  allAdlRules: [],
  weaknesses: [],
  fmeaAll: [],
  improvementRecommendations: [],
  tradeOffs: [],
  tactics: [],
  fullPackageMarkdown: '',
  overviewMarkdown: '',
  moduleViewMarkdown: '',
  ccViewMarkdown: '',
  allocationViewMarkdown: '',
  riskMarkdown: '',
  exportFilename: `architecture-docs-${getCurrentDate()}.md`,
  loading: false,
  error: null,
  hasData: false,
};

export function useArchDoc(): ArchDocData {
  const { architecture, loading: archLoading, error: archError } = useArchitecture();
  const {
    tradeOffs: allTradeOffs,
    adl,
    weaknesses: allWeaknesses,
    fmea,
    governanceReport,
    loading: govLoading,
    error: govError,
  } = useGovernance();
  const { tactics, loading: tacticsLoading, error: tacticsError } = useTactics();
  const { summary: buyVsBuildSummary, loading: bbLoading, error: bbError } = useBuyVsBuild();
  const conversationId = useStore((s) => s.conversationId);

  return useMemo(() => {
    const loading = archLoading || govLoading || tacticsLoading || bbLoading;
    const error = archError || govError || tacticsError || bbError || null;

    if (!architecture || !adl || !allWeaknesses || !buyVsBuildSummary) {
      return {
        ...EMPTY_DOC,
        exportFilename: `architecture-docs-${slugifyTitle(conversationId || 'architecture')}-${getCurrentDate()}.md`,
        loading,
        error,
      };
    }

    // --- ADL rule categorisation ---
    const allAdlRules = (adl.rules || []) as RawAdlRule[];

    const moduleAdlRules = allAdlRules.filter((r) => {
      const cat = resolveAdlCategory(r).toLowerCase();
      return ['layer', 'module', 'package', 'decomposition', 'dependency', 'maintainability', 'modularity'].some((k) => cat.includes(k));
    });
    const connectorAdlRules = allAdlRules.filter((r) => {
      const cat = resolveAdlCategory(r).toLowerCase();
      return ['connector', 'interface', 'protocol', 'communication', 'service', 'api', 'performance', 'security'].some((k) => cat.includes(k));
    });
    const allocationAdlRules = allAdlRules.filter((r) => {
      const cat = resolveAdlCategory(r).toLowerCase();
      return ['deploy', 'environment', 'infrastructure', 'hosting', 'cloud', 'reliability', 'availability'].some((k) => cat.includes(k));
    });

    // --- FMEA by component ---
    const fmeaByComponent: Record<string, FmeaEntry[]> = {};
    fmea.forEach((entry) => {
      if (!fmeaByComponent[entry.component]) fmeaByComponent[entry.component] = [];
      fmeaByComponent[entry.component].push(entry);
    });

    // --- Stakeholder concerns from tactic characteristic names ---
    const characteristicNames = [
      ...new Set([
        ...tactics.map((t) => t.characteristicName).filter(Boolean),
        ...allTradeOffs.flatMap((to) => [...(to.optimises_characteristics ?? []), ...(to.sacrifices_characteristics ?? [])]),
      ]),
    ];
    const stakeholderConcerns = buildStakeholderConcerns(characteristicNames);

    // --- Glossary from components ---
    const glossaryTerms = (architecture.components || []).map((c) => ({
      term: c.name,
      definition: c.responsibility,
    }));

    // --- SLO targets ---
    const sloTargets = buildSloTargets(tactics, allTradeOffs);

    // --- QA scenarios from tactics ---
    const scenarios = buildQaScenarios(tactics, architecture.interactions || []);

    // --- Build sequence ---
    const buyVsBuildDecisions = buyVsBuildSummary?.decisions || [];
    const buildSequence = buildConstructionSequence(
      architecture.components || [],
      buyVsBuildDecisions,
      architecture.interactions || [],
    );

    // --- System title / description ---
    const systemTitle = resolveSystemTitle(
      architecture.style || 'Unknown',
      (architecture as unknown as Record<string, string>).domain || '',
      conversationId || '',
    );
    const systemDescription = 'System architecture as defined through design conversation.';

    // --- Markdown sections ---
    const overviewMarkdown = buildOverviewMarkdown(
      systemTitle,
      architecture.style || 'Unknown',
      stakeholderConcerns,
      glossaryTerms,
      sloTargets,
      governanceReport?.governanceScore ?? null,
    );

    const moduleViewMarkdown = buildModuleViewMarkdown(
      architecture.componentDiagram || null,
      architecture.components || [],
      fmeaByComponent,
      allTradeOffs,
      moduleAdlRules,
      allWeaknesses?.weaknesses || [],
      tactics,
      buyVsBuildDecisions,
    );

    const ccViewMarkdown = buildCCViewMarkdown(
      architecture.sequenceDiagram || null,
      architecture.interactions || [],
      scenarios,
      connectorAdlRules,
      fmea,
      sloTargets,
    );

    const allocationViewMarkdown = buildAllocationViewMarkdown(
      null,
      buyVsBuildDecisions,
      architecture.components || [],
      allocationAdlRules,
      allWeaknesses?.weaknesses || [],
      buildSequence,
    );

    const riskMarkdown = buildRiskMarkdown(
      allAdlRules,
      allWeaknesses?.weaknesses || [],
      fmea,
      governanceReport?.improvementRecommendations || [],
      tactics,
    );

    const fullPackageMarkdown = [
      overviewMarkdown,
      '---',
      moduleViewMarkdown,
      '---',
      ccViewMarkdown,
      '---',
      allocationViewMarkdown,
      '---',
      riskMarkdown,
    ].join('\n\n');

    return {
      systemTitle,
      systemDescription,
      conversationTitle: conversationId || 'Architecture',
      stakeholderConcerns,
      glossaryTerms,
      sloTargets,
      componentDiagram: architecture.componentDiagram || null,
      deploymentDiagram: null,
      components: architecture.components || [],
      fmeaByComponent,
      moduleAdlRules: moduleAdlRules as AdlRule[],
      sequencePrimaryDiagram: architecture.sequenceDiagram || null,
      sequenceErrorDiagram: null,
      interactions: architecture.interactions || [],
      scenarios,
      connectorAdlRules: connectorAdlRules as AdlRule[],
      buyVsBuildDecisions,
      buildSequence,
      allocationAdlRules: allocationAdlRules as AdlRule[],
      adlDocument: adl,
      allAdlRules: allAdlRules as AdlRule[],
      weaknesses: allWeaknesses?.weaknesses || [],
      fmeaAll: fmea,
      improvementRecommendations: governanceReport?.improvementRecommendations || [],
      tradeOffs: allTradeOffs,
      tactics,
      fullPackageMarkdown,
      overviewMarkdown,
      moduleViewMarkdown,
      ccViewMarkdown,
      allocationViewMarkdown,
      riskMarkdown,
      exportFilename: `architecture-docs-${slugifyTitle(conversationId || 'architecture')}-${getCurrentDate()}.md`,
      loading,
      error,
      hasData: (architecture.components?.length || 0) > 0,
    };
  }, [
    architecture, adl, allWeaknesses, fmea, allTradeOffs, governanceReport,
    buyVsBuildSummary, conversationId, tactics,
    archLoading, govLoading, tacticsLoading, bbLoading,
    archError, govError, tacticsError, bbError,
  ]);
}
