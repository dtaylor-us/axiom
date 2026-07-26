import { useEffect, useMemo, useState } from 'react';
import { getDiagramByType } from '../api/architecture';
import { listSessions } from '../api/sessions';
import { useStore } from '../store/useStore';
import { useArchitecture } from './useArchitecture';
import { useGovernance } from './useGovernance';
import { useTactics } from './useTactics';
import { useBuyVsBuild } from './useBuyVsBuild';
import type {
  AdlDocument,
  AdlRule,
  BuyVsBuildDecision,
  Component,
  FmeaEntry,
  ImprovementRecommendation,
  Interaction,
  TacticRecommendation,
  TradeOffDecision,
  Weakness,
} from '../types/api';

type SloTarget = { characteristic: string; target: string; tactic: string };
type QaScenario = { stimulus: string; response: string; measures: string; characteristic: string };

const STYLE_DEFAULTS: Record<string, string[]> = {
  microservices: ['scalability', 'deployability', 'maintainability', 'reliability'],
  eventdriven: ['scalability', 'availability', 'performance', 'reliability'],
  layered: ['maintainability', 'testability', 'modularity'],
  serviceoriented: ['interoperability', 'scalability', 'reusability'],
  serverless: ['scalability', 'cost', 'availability'],
  monolith: ['simplicity', 'maintainability', 'deployability'],
};

const STYLE_IMPLIED_SLOS: Record<string, SloTarget[]> = {
  microservices: [
    { characteristic: 'Availability', target: '>= 99.9% per service', tactic: 'Define per-service SLA' },
    { characteristic: 'Latency', target: 'p99 < 500ms', tactic: 'Set gateway timeout policy' },
  ],
  eventdriven: [
    { characteristic: 'Throughput', target: 'Define events/sec target', tactic: 'Capacity plan message broker' },
    { characteristic: 'Availability', target: '>= 99.9% broker uptime', tactic: 'Message broker redundancy' },
  ],
};

const CORE_COMPONENT_KEYWORDS = [
  'gateway',
  'broker',
  'database',
  'cache',
  'auth',
  'identity',
  'store',
  'registry',
];

export type RawAdlRule = AdlRule & Record<string, unknown>;

export interface ArchDocData {
  systemTitle: string;
  systemDescription: string;
  conversationTitle: string;
  stakeholderConcerns: { characteristic: string; concern: string }[];
  glossaryTerms: { term: string; definition: string }[];

  componentDiagram: string | null;
  deploymentDiagram: string | null;
  components: Component[];
  fmeaByComponent: Record<string, FmeaEntry[]>;
  moduleAdlRules: RawAdlRule[];

  sequencePrimaryDiagram: string | null;
  sequenceErrorDiagram: string | null;
  interactions: Interaction[];
  scenarios: QaScenario[];
  connectorAdlRules: RawAdlRule[];
  sloTargets: SloTarget[];

  buyVsBuildDecisions: BuyVsBuildDecision[];
  allocationAdlRules: RawAdlRule[];

  adlDocument: AdlDocument | null;
  allAdlRules: RawAdlRule[];
  weaknesses: Weakness[];
  fmeaAll: FmeaEntry[];
  improvementRecommendations: ImprovementRecommendation[];
  tradeOffs: TradeOffDecision[];

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

function slugifyTitle(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function getCurrentDate(): string {
  const now = new Date();
  return now.toISOString().split('T')[0];
}

function normaliseComponentName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+(service|component|module|system|layer|api|gateway)$/, '')
    .replace(/[^a-z0-9]/g, '');
}

function getStyleKey(style: string): string {
  return (style || '').toLowerCase().replace(/[^a-z]/g, '');
}

function findStyleDefaults(architectureStyle: string): string[] {
  const styleKey = getStyleKey(architectureStyle);
  return Object.entries(STYLE_DEFAULTS).find(([key]) => styleKey.includes(key))?.[1] ?? [];
}

function cleanString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

export function resolveAdlSubject(r: RawAdlRule): string {
  const subject = cleanString(r.subject);
  if (subject) return subject;
  const title = cleanString(r.title);
  if (title) return title;
  const constraint = cleanString(r.constraint);
  if (constraint) return constraint;
  const statement = cleanString(r.statement);
  if (statement) return statement.split('.').slice(0, 1).join('.');
  return 'Architecture Constraint';
}

export function resolveAdlRationale(r: RawAdlRule): string {
  return cleanString(r.rationale) || cleanString(r.justification);
}

export function resolveAdlCategory(r: RawAdlRule): string {
  return cleanString(r.category) || cleanString(r.characteristic_enforced) || 'general';
}

export function resolveAdlEnforcement(r: RawAdlRule): string {
  return cleanString(r.enforcement_level) || cleanString(r.validation_hint?.enforcement_level) || 'soft';
}

export function resolveAdlId(r: RawAdlRule, index?: number): string {
  const id = cleanString(r.rule_id) || cleanString(r.adl_id);
  if (id) return id;
  const subject = resolveAdlSubject(r);
  if (subject.length > 3) {
    const stable = subject.slice(0, 6).toUpperCase().replace(/[^A-Z0-9]/g, '-');
    return stable || (index !== undefined ? `ADL-${String(index + 1).padStart(3, '0')}` : 'ADL-???');
  }
  return index !== undefined ? `ADL-${String(index + 1).padStart(3, '0')}` : 'ADL-???';
}

function resolveSystemTitle(style: string, conversationTitle: string): string {
  const title = cleanString(conversationTitle);
  if (title && title.toLowerCase() !== 'new conversation') {
    return title;
  }
  const trimmedStyle = cleanString(style);
  if (trimmedStyle && trimmedStyle.toLowerCase() !== 'unknown') {
    return `${trimmedStyle} System`;
  }
  return 'Architecture Analysis';
}

function extractAdlRules(adl: AdlDocument | null): RawAdlRule[] {
  if (!adl) return [];
  const adlWithBlocks = adl as AdlDocument & { adl_blocks?: RawAdlRule[]; rules?: RawAdlRule[] };
  const rules = Array.isArray(adlWithBlocks.rules) ? adlWithBlocks.rules : [];
  const blocks = Array.isArray(adlWithBlocks.adl_blocks) ? adlWithBlocks.adl_blocks : [];
  if (rules.length > 0) return rules;
  return blocks;
}

function buildStakeholderConcerns(characteristics: string[]): { characteristic: string; concern: string }[] {
  const unique = Array.from(new Set(characteristics.map((c) => c.trim()).filter((c) => c.length > 2)));
  return unique.map((characteristic) => ({
    characteristic,
    concern: `${characteristic} requirements are satisfied consistently.`,
  }));
}

function extractMeasureFromText(text: string): string {
  const match = text.match(/([<>]=?\s*\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds?|minutes?|hours?|%|rps|rpm|qps))/i);
  return match?.[1] ?? '';
}

function buildSloTargets(
  tactics: TacticRecommendation[],
  tradeOffs: TradeOffDecision[],
  architectureStyle: string,
): SloTarget[] {
  const targets: SloTarget[] = [];

  tactics
    .filter((t) => t.priority === 'critical')
    .forEach((t) => {
      const measure = extractMeasureFromText(t.concreteApplication || '');
      if (!measure) return;
      targets.push({
        characteristic: t.characteristicName || 'Quality',
        target: measure,
        tactic: t.tacticName || 'Tactic',
      });
    });

  if (targets.length === 0 && tradeOffs.length > 0) {
    tradeOffs.slice(0, 5).forEach((decision) => {
      if (!decision.acceptable_because || decision.acceptable_because.length <= 10) return;
      (decision.optimises_characteristics ?? []).slice(0, 1).forEach((characteristic) => {
        targets.push({
          characteristic: characteristic || 'Quality',
          target: decision.acceptable_because || '',
          tactic: `Trade-off ${decision.decision_id}`,
        });
      });
    });
  }

  if (targets.length === 0) {
    const styleKey = getStyleKey(architectureStyle);
    const implied = Object.entries(STYLE_IMPLIED_SLOS).find(([key]) => styleKey.includes(key))?.[1] ?? [];
    implied.forEach((item) => {
      targets.push({
        characteristic: item.characteristic,
        tactic: item.tactic,
        target: `[Placeholder - define actual target] ${item.target}`,
      });
    });
  }

  return targets.slice(0, 8);
}

function buildQaScenarios(
  tactics: TacticRecommendation[],
  interactions: Interaction[],
  components: Component[],
): QaScenario[] {
  const scenarios: QaScenario[] = [];
  const criticalTactics = tactics.filter((t) => t.priority === 'critical');

  criticalTactics.slice(0, 8).forEach((tactic) => {
    const application = tactic.concreteApplication || '';
    const targetComponent = components.find((component) =>
      application.toLowerCase().includes(component.name.toLowerCase()) ||
      component.responsibility.toLowerCase().includes((tactic.characteristicName || '').toLowerCase()),
    );

    const componentRef = targetComponent?.name || 'the system';
    const measure = extractMeasureFromText(application);
    const example = tactic.implementationExamples[0] || application.slice(0, 120);

    scenarios.push({
      characteristic: tactic.characteristicName || 'Quality',
      stimulus: `A user request or load event arrives at ${componentRef}.`,
      response: `${componentRef} applies ${tactic.tacticName}: ${example}`,
      measures: measure || `${tactic.characteristicName || 'Quality'} SLO is met`,
    });
  });

  if (scenarios.length === 0) {
    interactions.slice(0, 5).forEach((interaction) => {
      scenarios.push({
        characteristic: interaction.purpose || 'Runtime quality',
        stimulus: `Traffic reaches ${interaction.from}.`,
        response: `${interaction.from} calls ${interaction.to} over ${interaction.protocol || 'runtime protocol'}.`,
        measures: 'Measurable target to be defined',
      });
    });
  }

  return scenarios;
}

function buildConstructionSequence(
  components: Component[],
  interactions: Interaction[],
  buyVsBuildDecisions: BuyVsBuildDecision[],
): { component: string; phase: number; owner: string; reason: string }[] {
  const dependencyCountByNormalisedName = new Map<string, number>();
  interactions.forEach((interaction) => {
    const toKey = normaliseComponentName(interaction.to);
    dependencyCountByNormalisedName.set(toKey, (dependencyCountByNormalisedName.get(toKey) ?? 0) + 1);
  });

  const decisionMap = new Map<string, BuyVsBuildDecision>();
  buyVsBuildDecisions.forEach((decision) => {
    decisionMap.set(normaliseComponentName(decision.componentName), decision);
  });

  const getPhase = (component: Component): { phase: number; owner: string; reason: string } => {
    const decision = decisionMap.get(normaliseComponentName(component.name));
    const recommendation = decision?.recommendation;
    const ownership = (component.ownership || '').toLowerCase();
    const type = (component.type || '').toLowerCase();
    const dependedOnCount = dependencyCountByNormalisedName.get(normaliseComponentName(component.name)) ?? 0;

    if (recommendation === 'buy' || ownership.includes('bought-saas')) {
      return {
        phase: 1,
        reason: 'Purchased capability - configure and integrate first.',
        owner: 'Vendor/Procurement',
      };
    }
    if (recommendation === 'adopt' || ownership.includes('adopted-platform') || type.includes('infrastructure')) {
      return {
        phase: 1,
        reason: 'Adopted platform - provision in foundation sprint.',
        owner: 'Platform team',
      };
    }
    if (dependedOnCount >= 2) {
      return {
        phase: 2,
        reason: `Core dependency - ${dependedOnCount} components rely on this.`,
        owner: 'Internal team',
      };
    }

    const lowerName = component.name.toLowerCase();
    const lowerResponsibility = component.responsibility.toLowerCase();
    if (CORE_COMPONENT_KEYWORDS.some((keyword) => lowerName.includes(keyword) || lowerResponsibility.includes(keyword))) {
      return {
        phase: 2,
        reason: 'Infrastructure component - typically a core dependency.',
        owner: 'Internal team',
      };
    }

    return {
      phase: 3,
      reason: 'Feature component - build after foundation is stable.',
      owner: 'Internal team',
    };
  };

  return components.map((component) => ({
    component: component.name,
    ...getPhase(component),
  }));
}

function buildOverviewMarkdown(
  systemTitle: string,
  systemDescription: string,
  characteristics: { characteristic: string; concern: string }[],
  glossary: { term: string; definition: string }[],
  architectureStyle: string,
): string {
  const lines: string[] = [
    '# Architecture Documentation Package',
    `**System:** ${systemTitle}`,
    `**Generated:** ${getCurrentDate()}`,
    `**Architecture style:** ${architectureStyle}`,
    '',
    '## Purpose and Scope',
    systemDescription,
    '',
    '## Stakeholders and Concerns',
    '',
    '| Stakeholder | Concerns |',
    '|---|---|',
  ];

  const concernsByRole: Record<string, string[]> = {};
  characteristics.forEach(({ characteristic, concern }) => {
    const lowerConcern = concern.toLowerCase();
    const role = lowerConcern.includes('recovery') || lowerConcern.includes('failover')
      ? 'Operations team'
      : lowerConcern.includes('security') || lowerConcern.includes('attack')
        ? 'Security team'
        : lowerConcern.includes('requirement') || lowerConcern.includes('specification')
          ? 'Development team'
          : 'Product owner';
    if (!concernsByRole[role]) concernsByRole[role] = [];
    concernsByRole[role].push(characteristic);
  });

  if (Object.keys(concernsByRole).length === 0) {
    lines.push('| Product owner | Architecture characteristics require definition |');
  } else {
    Object.entries(concernsByRole).forEach(([role, concerns]) => {
      lines.push(`| ${role} | ${Array.from(new Set(concerns)).join(', ')} |`);
    });
  }

  lines.push('', '## Reading Guide', '');
  lines.push('| Stakeholder | Start here | Then read |');
  lines.push('|---|---|---|');
  lines.push('| Development team | Module View | C&C View, ADL rules |');
  lines.push('| Operations team | Allocation View | C&C View, Risk section |');
  lines.push('| Architects | Module View | C&C View, Variability |');
  lines.push('| Product owners | Overview | Rationale |');
  lines.push('| Security team | C&C View | Risk section |');

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
  buyVsBuildDecisions: BuyVsBuildDecision[],
): string {
  const decisionMap = new Map<string, BuyVsBuildDecision>();
  buyVsBuildDecisions.forEach((decision) => {
    decisionMap.set(normaliseComponentName(decision.componentName), decision);
  });

  const lines: string[] = [
    '# Module View',
    '',
    '## Primary Presentation',
  ];

  if (componentDiagram) {
    lines.push('```mermaid');
    lines.push(componentDiagram);
    lines.push('```');
  } else if (components.length === 0) {
    lines.push('No component diagram available');
  }

  if (components.length > 0) {
    lines.push('');
    lines.push('## Element Catalog');
    lines.push('');
    lines.push('| Element | Type | Responsibility | Technology | Ownership | Risks |');
    lines.push('|---|---|---|---|---|---|');

    components.forEach((component) => {
      const decision = decisionMap.get(normaliseComponentName(component.name));
      const technology = component.technology &&
        component.technology.toLowerCase() !== 'various' &&
        component.technology.toLowerCase() !== 'tbd'
        ? component.technology
        : decision?.recommendedSolution || '—';
      const risks = fmeaByComponent[component.name]
        ?.slice(0, 2)
        .map((risk) => risk.failure_mode)
        .join('; ') || '—';
      const ownership = component.ownership || '—';
      lines.push(
        `| ${component.name} | ${component.type || '—'} | ${component.responsibility} | ${technology} | ${ownership} | ${risks} |`,
      );
    });
  }

  if (tradeOffs.length > 0) {
    lines.push('');
    lines.push('## Variability Guide');
    lines.push('');
    tradeOffs.forEach((tradeOff) => {
      lines.push(`**Decision:** ${tradeOff.decision}`);
      lines.push(`**Choice made:** ${tradeOff.recommendation}`);
      if ((tradeOff.sacrifices_characteristics ?? []).length > 0) {
        lines.push(`**Alternatives:** ${(tradeOff.sacrifices_characteristics ?? []).join(', ')}`);
      }
      lines.push(`**Rationale:** ${tradeOff.context_dependency}`);
      lines.push('');
    });
  }

  if (moduleAdlRules.length > 0) {
    lines.push('## Rationale');
    lines.push('');
    moduleAdlRules.forEach((rule, index) => {
      lines.push(`### [${resolveAdlId(rule, index)}] ${resolveAdlSubject(rule)}`);
      lines.push(cleanString(rule.statement) || 'No statement available.');
      const rationale = resolveAdlRationale(rule);
      if (rationale) lines.push(`*${rationale}*`);
      lines.push('');
    });
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((weakness) => {
      lines.push(`- **${weakness.title}** (Severity ${weakness.severity}/10): ${weakness.description}`);
    });
  }

  return lines.join('\n');
}

function buildCCViewMarkdown(
  sequenceDiagram: string | null,
  interactions: Interaction[],
  scenarios: QaScenario[],
  sloTargets: SloTarget[],
  connectorAdlRules: RawAdlRule[],
  fmeaAll: FmeaEntry[],
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
    lines.push('No sequence diagram available');
  }

  lines.push('');
  lines.push('## Runtime Element Catalog');
  lines.push('');
  if (interactions.length > 0) {
    lines.push('| Connector | From | To | Protocol | Failure Mode |');
    lines.push('|---|---|---|---|---|');
    interactions.forEach((interaction) => {
      const failureMode = fmeaAll
        .filter((entry) => entry.component === interaction.from || entry.component === interaction.to)
        .map((entry) => entry.failure_mode)
        .slice(0, 1)
        .join('; ') || '—';
      lines.push(
        `| ${interaction.from}->${interaction.to} | ${interaction.from} | ${interaction.to} | ${interaction.protocol || '—'} | ${failureMode} |`,
      );
    });
  } else {
    lines.push(
      '> Interaction data not available. Re-run the analysis to generate the component connector view. Check that the diagram_generation stage completed.',
    );
  }

  lines.push('');
  lines.push('## Quality Objectives (SLO Targets)');
  lines.push('');
  if (sloTargets.length > 0) {
    lines.push('| Characteristic | Target | Source |');
    lines.push('|---|---|---|');
    sloTargets.forEach((target) => {
      lines.push(`| ${target.characteristic} | ${target.target} | ${target.tactic} |`);
    });
  } else {
    lines.push('> SLO target data not available for this analysis run.');
  }

  if (scenarios.length > 0) {
    lines.push('');
    lines.push('## Quality Attribute Utility Tree');
    lines.push('');
    scenarios.forEach((scenario, index) => {
      lines.push(`### Scenario ${index + 1}`);
      lines.push(`**Characteristic:** ${scenario.characteristic}`);
      lines.push(`**Stimulus:** ${scenario.stimulus}`);
      lines.push(`**Response:** ${scenario.response}`);
      lines.push(`**Measures:** ${scenario.measures}`);
      lines.push('');
    });
  }

  if (connectorAdlRules.length > 0) {
    lines.push('## Rationale');
    lines.push('');
    connectorAdlRules.forEach((rule, index) => {
      lines.push(`### [${resolveAdlId(rule, index)}] ${resolveAdlSubject(rule)}`);
      lines.push(cleanString(rule.statement) || 'No statement available.');
      const rationale = resolveAdlRationale(rule);
      if (rationale) lines.push(`*${rationale}*`);
      lines.push('');
    });
  }

  lines.push('## Risk Analysis');
  lines.push('');
  if (fmeaAll.length > 0) {
    lines.push('| ID | Failure Mode | Component | RPN |');
    lines.push('|---|---|---|---|');
    fmeaAll
      .slice()
      .sort((a, b) => b.rpn - a.rpn)
      .slice(0, 10)
      .forEach((entry) => {
        lines.push(`| ${entry.id} | ${entry.failure_mode} | ${entry.component} | ${entry.rpn} |`);
      });
  } else {
    lines.push('> FMEA data not available for this analysis run.');
  }

  return lines.join('\n');
}

function buildAllocationViewMarkdown(
  deploymentDiagram: string | null,
  buyVsBuildDecisions: BuyVsBuildDecision[],
  components: Component[],
  interactions: Interaction[],
  allocationAdlRules: RawAdlRule[],
  weaknesses: Weakness[],
): string {
  const seenComponents = new Set<string>();
  const uniqueDecisions = buyVsBuildDecisions.filter((decision) => {
    const key = normaliseComponentName(decision.componentName);
    if (seenComponents.has(key)) return false;
    seenComponents.add(key);
    return true;
  });

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
    lines.push('| Component | Type | Deployment Target |');
    lines.push('|---|---|---|');
    components.forEach((component) => {
      lines.push(`| ${component.name} | ${component.type || '—'} | ${component.ownership || '—'} |`);
    });
  } else {
    lines.push('No deployment diagram available');
  }

  if (uniqueDecisions.length > 0) {
    lines.push('');
    lines.push('## Work Assignment');
    lines.push('');
    lines.push('| Component | Owner | Type | Solution |');
    lines.push('|---|---|---|---|');
    uniqueDecisions.forEach((decision) => {
      const owner =
        decision.recommendation === 'build'
          ? 'Internal team'
          : decision.recommendation === 'buy'
            ? 'Vendor/Procurement'
            : 'Platform team';
      lines.push(
        `| ${decision.componentName} | ${owner} | ${decision.recommendation} | ${decision.recommendedSolution} |`,
      );
    });
  }

  const constructionSequence = buildConstructionSequence(components, interactions, uniqueDecisions);
  if (constructionSequence.length > 0) {
    lines.push('');
    lines.push('## Build Sequence');
    lines.push('');
    lines.push('| Phase | Component | Owner | Rationale |');
    lines.push('|---|---|---|---|');
    constructionSequence
      .slice()
      .sort((a, b) => a.phase - b.phase || a.component.localeCompare(b.component))
      .forEach((step) => {
        lines.push(`| ${step.phase} | ${step.component} | ${step.owner} | ${step.reason} |`);
      });
  }

  if (allocationAdlRules.length > 0) {
    lines.push('');
    lines.push('## Rationale');
    lines.push('');
    allocationAdlRules.forEach((rule, index) => {
      lines.push(`### [${resolveAdlId(rule, index)}] ${resolveAdlSubject(rule)}`);
      lines.push(cleanString(rule.statement) || 'No statement available.');
      const rationale = resolveAdlRationale(rule);
      if (rationale) lines.push(`*${rationale}*`);
      lines.push('');
    });
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((weakness) => {
      lines.push(`- **${weakness.title}** (Severity ${weakness.severity}/10): ${weakness.mitigation}`);
    });
  }

  return lines.join('\n');
}

function buildRiskMarkdown(
  allAdlRules: RawAdlRule[],
  weaknesses: Weakness[],
  fmeaAll: FmeaEntry[],
  improvementRecommendations: ImprovementRecommendation[],
): string {
  const lines: string[] = ['# Risk and Decision Log', ''];

  if (allAdlRules.length > 0) {
    lines.push('## Architecture Decision Records');
    lines.push('');
    allAdlRules.forEach((rule, index) => {
      lines.push(`### ADR-${resolveAdlId(rule, index)}: ${resolveAdlSubject(rule)}`);
      lines.push('');
      lines.push('**Status:** Accepted');
      lines.push(`**Category:** ${resolveAdlCategory(rule)}`);
      lines.push(`**Enforcement:** ${resolveAdlEnforcement(rule)}`);
      lines.push('');
      lines.push('#### Context');
      lines.push(resolveAdlRationale(rule) || 'Context not provided.');
      lines.push('');
      lines.push('#### Decision');
      lines.push(cleanString(rule.statement) || 'No decision statement provided.');
      lines.push('');
    });
  }

  const risksMap = new Map<string, { severity: number; entry: string }>();
  weaknesses.forEach((weakness) => {
    risksMap.set(weakness.id, {
      severity: weakness.severity,
      entry: `| ${weakness.id} | ${weakness.title} | ${weakness.component_affected} | ${weakness.severity} | Weakness | ${weakness.mitigation} |`,
    });
  });

  fmeaAll.forEach((entry) => {
    const severity = Math.min(10, Math.round(entry.rpn / 10));
    risksMap.set(entry.id, {
      severity,
      entry: `| ${entry.id} | ${entry.failure_mode} | ${entry.component} | ${severity} | FMEA | ${entry.recommended_action} |`,
    });
  });

  lines.push('## Risk Register');
  lines.push('');
  if (risksMap.size > 0) {
    lines.push('| ID | Risk | Component | Severity | Type | Mitigation |');
    lines.push('|---|---|---|---|---|---|');
    Array.from(risksMap.values())
      .sort((a, b) => b.severity - a.severity)
      .forEach(({ entry }) => lines.push(entry));
  } else {
    lines.push(
      '> Risk data not available. Ensure the weakness_analysis and fmea_analysis stages completed successfully. Re-run the analysis if stages show `completed_with_gaps`.',
    );
    lines.push('');
  }

  if (improvementRecommendations.length > 0) {
    lines.push('');
    lines.push('## Improvement Roadmap');
    lines.push('');
    improvementRecommendations.forEach((recommendation) => {
      lines.push(`### [${recommendation.priority}] ${recommendation.area}`);
      lines.push(recommendation.recommendation);
      if (recommendation.requires_reiteration) {
        lines.push('*Requires reiteration*');
      }
      lines.push('');
    });
  }

  return lines.join('\n');
}

export function useArchDoc(): ArchDocData {
  const token = useStore((s) => s.token);
  const conversationId = useStore((s) => s.conversationId);
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

  const [conversationTitle, setConversationTitle] = useState('');
  const [deploymentDiagram, setDeploymentDiagram] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!token || !conversationId) {
      setConversationTitle('');
      return;
    }
    listSessions(token)
      .then((sessions) => {
        if (cancelled) return;
        const current = sessions.find((session) => session.id === conversationId);
        setConversationTitle(current?.title || '');
      })
      .catch(() => {
        if (!cancelled) setConversationTitle('');
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, token]);

  useEffect(() => {
    let cancelled = false;
    if (!token || !conversationId) {
      setDeploymentDiagram(null);
      return;
    }
    getDiagramByType(conversationId, 'deployment', token)
      .then((diagram) => {
        if (!cancelled) {
          setDeploymentDiagram(diagram);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDeploymentDiagram(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, token]);

  const archDocData = useMemo<ArchDocData>(() => {
    const loading = archLoading || govLoading || tacticsLoading || bbLoading;
    const error = archError || govError || tacticsError || bbError;

    if (!architecture) {
      return {
        systemTitle: 'Architecture Analysis',
        systemDescription: 'Architecture documentation generated from analysis.',
        conversationTitle: conversationTitle || 'Architecture Analysis',
        stakeholderConcerns: [],
        glossaryTerms: [],
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
        sloTargets: [],
        buyVsBuildDecisions: [],
        allocationAdlRules: [],
        adlDocument: adl,
        allAdlRules: [],
        weaknesses: [],
        fmeaAll: [],
        improvementRecommendations: [],
        tradeOffs: [],
        fullPackageMarkdown: '',
        overviewMarkdown: '',
        moduleViewMarkdown: '',
        ccViewMarkdown: '',
        allocationViewMarkdown: '',
        riskMarkdown: '',
        exportFilename: `architecture-docs-${slugifyTitle('architecture-analysis')}-${getCurrentDate()}.md`,
        loading,
        error: error || null,
        hasData: false,
      };
    }

    const allAdlRules = extractAdlRules(adl);
    const moduleAdlRules = allAdlRules.filter((rule) =>
      ['layer', 'module', 'package', 'decomposition', 'dependency'].some((cat) =>
        resolveAdlCategory(rule).toLowerCase().includes(cat),
      ),
    );
    const connectorAdlRules = allAdlRules.filter((rule) =>
      ['connector', 'interface', 'protocol', 'communication', 'service', 'api'].some((cat) =>
        resolveAdlCategory(rule).toLowerCase().includes(cat),
      ),
    );
    const allocationAdlRules = allAdlRules.filter((rule) =>
      ['deploy', 'environment', 'infrastructure', 'hosting', 'cloud'].some((cat) =>
        resolveAdlCategory(rule).toLowerCase().includes(cat),
      ),
    );

    const fmeaByComponent: Record<string, FmeaEntry[]> = {};
    fmea.forEach((entry) => {
      if (!fmeaByComponent[entry.component]) {
        fmeaByComponent[entry.component] = [];
      }
      fmeaByComponent[entry.component].push(entry);
    });

    const characteristicsFromTactics = tactics.map((t) => t.characteristicName).filter(Boolean);
    const characteristicsFromTradeOffs = allTradeOffs.flatMap((tradeOff) => [
      ...(tradeOff.optimises_characteristics ?? []),
      ...(tradeOff.sacrifices_characteristics ?? []),
    ]);
    const characteristicsFromAdl = allAdlRules.map((rule) => resolveAdlCategory(rule)).filter(Boolean);
    const characteristicsFromFmea = fmea.length > 0 ? ['reliability', 'availability'] : [];

    const characteristicNames = Array.from(
      new Set([
        ...characteristicsFromTactics,
        ...characteristicsFromTradeOffs,
        ...characteristicsFromAdl,
        ...characteristicsFromFmea,
      ]),
    ).filter((characteristic) => characteristic.length > 2);

    const fallbackCharacteristics = findStyleDefaults(architecture.style);
    const stakeholderConcerns = buildStakeholderConcerns(
      characteristicNames.length > 0 ? characteristicNames : fallbackCharacteristics,
    );

    const componentGlossary = (architecture.components || [])
      .filter((component) => component.responsibility.length > 40)
      .map((component) => ({
        term: component.name,
        definition: component.responsibility.slice(0, 200),
      }));

    const adlGlossary = allAdlRules
      .filter((rule) => {
        const subject = resolveAdlSubject(rule);
        return subject.length > 10 && subject.length < 100;
      })
      .slice(0, 6)
      .map((rule) => ({
        term: resolveAdlSubject(rule),
        definition: resolveAdlRationale(rule) || resolveAdlCategory(rule),
      }));

    const glossaryTerms = [...componentGlossary, ...adlGlossary].filter((entry, index, items) => {
      const key = entry.term.toLowerCase().trim();
      return key.length > 0 && items.findIndex((candidate) => candidate.term.toLowerCase().trim() === key) === index;
    });

    const scenarios = buildQaScenarios(
      tactics,
      architecture.interactions || [],
      architecture.components || [],
    );

    const sloTargets = buildSloTargets(tactics, allTradeOffs, architecture.style || '');
    const systemTitle = resolveSystemTitle(architecture.style || 'Unknown', conversationTitle);

    const overviewMarkdown = buildOverviewMarkdown(
      systemTitle,
      'System architecture as defined through design conversation.',
      stakeholderConcerns,
      glossaryTerms,
      architecture.style || 'Unknown',
    );

    const moduleViewMarkdown = buildModuleViewMarkdown(
      architecture.componentDiagram || null,
      architecture.components || [],
      fmeaByComponent,
      allTradeOffs,
      moduleAdlRules,
      allWeaknesses?.weaknesses || [],
      buyVsBuildSummary?.decisions || [],
    );

    const ccViewMarkdown = buildCCViewMarkdown(
      architecture.sequenceDiagram || null,
      architecture.interactions || [],
      scenarios,
      sloTargets,
      connectorAdlRules,
      fmea,
    );

    const allocationViewMarkdown = buildAllocationViewMarkdown(
      deploymentDiagram,
      buyVsBuildSummary?.decisions || [],
      architecture.components || [],
      architecture.interactions || [],
      allocationAdlRules,
      allWeaknesses?.weaknesses || [],
    );

    const riskMarkdown = buildRiskMarkdown(
      allAdlRules,
      allWeaknesses?.weaknesses || [],
      fmea,
      governanceReport?.improvementRecommendations || [],
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
      systemDescription: 'System architecture as defined through design conversation.',
      conversationTitle: conversationTitle || systemTitle,
      stakeholderConcerns,
      glossaryTerms,
      componentDiagram: architecture.componentDiagram || null,
      deploymentDiagram,
      components: architecture.components || [],
      fmeaByComponent,
      moduleAdlRules,
      sequencePrimaryDiagram: architecture.sequenceDiagram || null,
      sequenceErrorDiagram: null,
      interactions: architecture.interactions || [],
      scenarios,
      connectorAdlRules,
      sloTargets,
      buyVsBuildDecisions: buyVsBuildSummary?.decisions || [],
      allocationAdlRules,
      adlDocument: adl,
      allAdlRules,
      weaknesses: allWeaknesses?.weaknesses || [],
      fmeaAll: fmea,
      improvementRecommendations: governanceReport?.improvementRecommendations || [],
      tradeOffs: allTradeOffs,
      fullPackageMarkdown,
      overviewMarkdown,
      moduleViewMarkdown,
      ccViewMarkdown,
      allocationViewMarkdown,
      riskMarkdown,
      exportFilename: `architecture-docs-${slugifyTitle(systemTitle)}-${getCurrentDate()}.md`,
      loading,
      error: error || null,
      hasData: (architecture.components?.length || 0) > 0,
    };
  }, [
    adl,
    allTradeOffs,
    allWeaknesses,
    archError,
    archLoading,
    architecture,
    bbError,
    bbLoading,
    buyVsBuildSummary,
    conversationTitle,
    deploymentDiagram,
    fmea,
    govError,
    govLoading,
    governanceReport,
    tactics,
    tacticsError,
    tacticsLoading,
  ]);

  return archDocData;
}
