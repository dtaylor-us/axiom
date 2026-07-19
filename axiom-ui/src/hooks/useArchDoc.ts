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
  TacticRecommendation,
  TradeOffDecision,
  AdlDocument,
  ImprovementRecommendation,
} from '../types/api';

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
  moduleAdlRules: AdlRule[];

  sequencePrimaryDiagram: string | null;
  sequenceErrorDiagram: string | null;
  interactions: Interaction[];
  scenarios: { stimulus: string; response: string; measures: string }[];
  connectorAdlRules: AdlRule[];

  buyVsBuildDecisions: BuyVsBuildDecision[];
  allocationAdlRules: AdlRule[];

  adlDocument: AdlDocument | null;
  allAdlRules: AdlRule[];
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

function buildOverviewMarkdown(
  systemTitle: string,
  systemDescription: string,
  characteristics: { characteristic: string; concern: string }[],
  glossary: { term: string; definition: string }[],
  architectureStyle: string,
  conversationTitle: string,
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

  // Build stakeholder concerns table
  const concernsByRole: Record<string, string[]> = {};
  characteristics.forEach(({ characteristic, concern }) => {
    // Infer role from concern context
    const role = concern.includes('recovery') || concern.includes('failover')
      ? 'Operations team'
      : concern.includes('security') || concern.includes('attack')
        ? 'Security team'
        : concern.includes('requirement') || concern.includes('specification')
          ? 'Development team'
          : 'Product owner';
    if (!concernsByRole[role]) concernsByRole[role] = [];
    concernsByRole[role].push(characteristic);
  });

  Object.entries(concernsByRole).forEach(([role, concerns]) => {
    lines.push(`| ${role} | ${concerns.join(', ')} |`);
  });

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
  moduleAdlRules: AdlRule[],
  weaknesses: Weakness[],
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
  } else if (components.length > 0) {
    lines.push('## Element Catalog');
    lines.push('');
    lines.push('| Element | Type | Responsibility | Technology | Risks |');
    lines.push('|---|---|---|---|---|');
    components.forEach((c) => {
      const risks = fmeaByComponent[c.name]
        ?.slice(0, 2)
        .map((r) => r.failure_mode)
        .join('; ') || '—';
      lines.push(
        `| ${c.name} | ${c.type || '—'} | ${c.responsibility} | ${c.technology} | ${risks} |`
      );
    });
  } else {
    lines.push('No component diagram available');
  }

  if (components.length > 0) {
    lines.push('');
    lines.push('## Element Catalog');
    lines.push('');
    lines.push('| Element | Type | Responsibility | Technology | Risks |');
    lines.push('|---|---|---|---|---|');
    components.forEach((c) => {
      const risks = fmeaByComponent[c.name]
        ?.slice(0, 2)
        .map((r) => r.failure_mode)
        .join('; ') || '—';
      lines.push(
        `| ${c.name} | ${c.type || '—'} | ${c.responsibility} | ${c.technology} | ${risks} |`
      );
    });
  }

  if (tradeOffs.length > 0) {
    lines.push('');
    lines.push('## Variability Guide');
    lines.push('');
    tradeOffs.forEach((t) => {
      lines.push(`**Decision:** ${t.decision}`);
      lines.push(`**Choice made:** ${t.recommendation}`);
      if ((t.sacrifices_characteristics ?? []).length > 0) {
        lines.push(`**Alternatives:** ${(t.sacrifices_characteristics ?? []).join(', ')}`);
      }
      lines.push(`**Rationale:** ${t.context_dependency}`);
      lines.push('');
    });
  }

  if (moduleAdlRules.length > 0) {
    lines.push('## Rationale');
    lines.push('');
    moduleAdlRules.forEach((r) => {
      lines.push(`### [${r.rule_id}] ${r.subject}`);
      lines.push(r.statement);
      if (r.rationale) lines.push(`*${r.rationale}*`);
      lines.push('');
    });
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((w) => {
      lines.push(`- **${w.title}** (Severity ${w.severity}/10): ${w.description}`);
    });
  }

  return lines.join('\n');
}

function buildCCViewMarkdown(
  sequenceDiagram: string | null,
  interactions: Interaction[],
  scenarios: { stimulus: string; response: string; measures: string }[],
  connectorAdlRules: AdlRule[],
  tradeOffs: TradeOffDecision[],
  fmeaAll: FmeaEntry[],
  weaknesses: Weakness[],
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

  if (interactions.length > 0) {
    lines.push('');
    lines.push('## Runtime Element Catalog');
    lines.push('');
    lines.push('| Connector | From | To | Protocol | Failure Mode |');
    lines.push('|---|---|---|---|---|');
    interactions.forEach((i) => {
      const failureMode = fmeaAll
        .filter((f) => f.component === i.from || f.component === i.to)
        .map((f) => f.failure_mode)
        .slice(0, 1)
        .join('; ') || '—';
      lines.push(`| ${i.from}→${i.to} | ${i.from} | ${i.to} | ${i.protocol} | ${failureMode} |`);
    });
  }

  if (scenarios.length > 0) {
    lines.push('');
    lines.push('## Quality Attribute Utility Tree');
    lines.push('');
    scenarios.forEach((s, idx) => {
      lines.push(`### Scenario ${idx + 1}`);
      lines.push(`**Stimulus:** ${s.stimulus}`);
      lines.push(`**Response:** ${s.response}`);
      lines.push(`**Measures:** ${s.measures}`);
      lines.push('');
    });
  }

  if (connectorAdlRules.length > 0) {
    lines.push('## Rationale');
    lines.push('');
    connectorAdlRules.forEach((r) => {
      lines.push(`### [${r.rule_id}] ${r.subject}`);
      lines.push(r.statement);
      if (r.rationale) lines.push(`*${r.rationale}*`);
      lines.push('');
    });
  }

  if (fmeaAll.length > 0) {
    lines.push('## Risk Analysis');
    lines.push('');
    lines.push('| ID | Failure Mode | Component | RPN |');
    lines.push('|---|---|---|---|');
    fmeaAll
      .sort((a, b) => b.rpn - a.rpn)
      .slice(0, 10)
      .forEach((e) => {
        lines.push(`| ${e.id} | ${e.failure_mode} | ${e.component} | ${e.rpn} |`);
      });
  }

  return lines.join('\n');
}

function buildAllocationViewMarkdown(
  deploymentDiagram: string | null,
  buyVsBuildDecisions: BuyVsBuildDecision[],
  components: Component[],
  allocationAdlRules: AdlRule[],
  weaknesses: Weakness[],
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
    lines.push('| Component | Type | Deployment Target |');
    lines.push('|---|---|---|');
    components.forEach((c) => {
      lines.push(`| ${c.name} | ${c.type || '—'} | ${c.ownership || '—'} |`);
    });
  } else {
    lines.push('No deployment diagram available');
  }

  if (buyVsBuildDecisions.length > 0) {
    lines.push('');
    lines.push('## Work Assignment');
    lines.push('');
    lines.push('| Component | Owner | Type | Solution |');
    lines.push('|---|---|---|---|');
    buyVsBuildDecisions.forEach((d) => {
      const owner =
        d.recommendation === 'build'
          ? 'Internal team'
          : d.recommendation === 'buy'
            ? 'Vendor/Procurement'
            : 'Platform team';
      lines.push(
        `| ${d.componentName} | ${owner} | ${d.recommendation} | ${d.recommendedSolution} |`
      );
    });
  }

  if (allocationAdlRules.length > 0) {
    lines.push('');
    lines.push('## Rationale');
    lines.push('');
    allocationAdlRules.forEach((r) => {
      lines.push(`### [${r.rule_id}] ${r.subject}`);
      lines.push(r.statement);
      if (r.rationale) lines.push(`*${r.rationale}*`);
      lines.push('');
    });
  }

  if (weaknesses.length > 0) {
    lines.push('## Risk Summary');
    lines.push('');
    weaknesses.slice(0, 5).forEach((w) => {
      lines.push(`- **${w.title}** (Severity ${w.severity}/10): ${w.mitigation}`);
    });
  }

  return lines.join('\n');
}

function buildRiskMarkdown(
  allAdlRules: AdlRule[],
  weaknesses: Weakness[],
  fmeaAll: FmeaEntry[],
  improvementRecommendations: ImprovementRecommendation[],
): string {
  const lines: string[] = ['# Risk and Decision Log', ''];

  if (allAdlRules.length > 0) {
    lines.push('## Architecture Decision Records');
    lines.push('');
    allAdlRules.forEach((r) => {
      lines.push(`### ADR-${r.rule_id}: ${r.subject}`);
      lines.push('');
      lines.push(`**Status:** Accepted`);
      lines.push(`**Category:** ${r.category}`);
      lines.push('');
      lines.push('#### Context');
      if (r.rationale) lines.push(r.rationale);
      lines.push('');
      lines.push('#### Decision');
      lines.push(r.statement);
      lines.push('');
      if (r.validation_hint?.type) {
        lines.push('#### Consequences');
        lines.push(`Enforcement: ${r.validation_hint.enforcement_level || 'standard'}`);
        lines.push('');
      }
    });
  }

  // Build unified risk register
  const risksMap = new Map<string, { severity: number; entry: string }>();

  weaknesses.forEach((w) => {
    risksMap.set(w.id, {
      severity: w.severity,
      entry: `| ${w.id} | ${w.title} | ${w.component_affected} | ${w.severity} | Weakness | ${w.mitigation} |`,
    });
  });

  fmeaAll.forEach((f) => {
    const severity = Math.min(10, Math.round(f.rpn / 10));
    risksMap.set(f.id, {
      severity,
      entry: `| ${f.id} | ${f.failure_mode} | ${f.component} | ${severity} | FMEA | ${f.recommended_action} |`,
    });
  });

  if (risksMap.size > 0) {
    lines.push('## Risk Register');
    lines.push('');
    lines.push('| ID | Risk | Component | Severity | Type | Mitigation |');
    lines.push('|---|---|---|---|---|---|');
    Array.from(risksMap.values())
      .sort((a, b) => b.severity - a.severity)
      .forEach(({ entry }) => {
        lines.push(entry);
      });
  }

  if (improvementRecommendations.length > 0) {
    lines.push('');
    lines.push('## Improvement Roadmap');
    lines.push('');
    improvementRecommendations.forEach((r) => {
      lines.push(`### [${r.priority}] ${r.area}`);
      lines.push(r.recommendation);
      if (r.requires_reiteration) {
        lines.push('*Requires reiteration*');
      }
      lines.push('');
    });
  }

  return lines.join('\n');
}

export function useArchDoc(): ArchDocData {
  const conversationTitle = useStore((s) => s.conversationTitle);
  const { architecture, loading: archLoading, error: archError } = useArchitecture();
  const {
    tradeOffs,
    adl,
    weaknesses,
    fmea,
    governanceReport,
    loading: govLoading,
    error: govError,
  } = useGovernance();
  const { tactics, loading: tacticsLoading, error: tacticsError } = useTactics();
  const { summary: buyVsBuildSummary, loading: bbLoading, error: bbError } = useBuyVsBuild();

  const archDocData = useMemo(() => {
    const loading = archLoading || govLoading || tacticsLoading || bbLoading;
    const error = archError || govError || tacticsError || bbError;

    if (!architecture || !adl || !weaknesses || !buyVsBuildSummary) {
      return {
        systemTitle: 'Architecture',
        systemDescription: 'Architecture documentation generated from analysis.',
        conversationTitle: conversationTitle || 'Architecture',
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
        buyVsBuildDecisions: [],
        allocationAdlRules: [],
        adlDocument: null,
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
        exportFilename: `architecture-docs-${slugifyTitle(conversationTitle || 'architecture')}-${getCurrentDate()}.md`,
        loading,
        error: error || null,
        hasData: false,
      };
    }

    // Extract rules by category
    const allAdlRules = adl.rules || [];
    const moduleAdlRules = allAdlRules.filter((r) =>
      ['layer', 'module', 'package', 'decomposition', 'dependency'].some((cat) =>
        (r.category || '').toLowerCase().includes(cat)
      )
    );
    const connectorAdlRules = allAdlRules.filter((r) =>
      ['connector', 'interface', 'protocol', 'communication', 'service', 'api'].some((cat) =>
        (r.category || '').toLowerCase().includes(cat)
      )
    );
    const allocationAdlRules = allAdlRules.filter((r) =>
      ['deploy', 'environment', 'infrastructure', 'hosting', 'cloud'].some((cat) =>
        (r.category || '').toLowerCase().includes(cat)
      )
    );

    // Build FMEA map
    const fmeaByComponent: Record<string, FmeaEntry[]> = {};
    fmea.forEach((entry) => {
      if (!fmeaByComponent[entry.component]) {
        fmeaByComponent[entry.component] = [];
      }
      fmeaByComponent[entry.component].push(entry);
    });

    // Build stakeholder concerns from characteristics
    const stakeholderConcerns = architecture?.interactions
      ? architecture.interactions.map((i) => ({
        characteristic: i.from,
        concern: i.purpose,
      }))
      : [];

    // Build glossary from components
    const glossaryTerms = (architecture?.components || []).map((c) => ({
      term: c.name,
      definition: c.responsibility,
    }));

    // Extract scenarios (placeholder - using interactions as proxy)
    const scenarios = (architecture?.interactions || []).map((i) => ({
      stimulus: `${i.from} initiates`,
      response: `${i.to} receives via ${i.protocol}`,
      measures: 'On demand',
    }));

    // Build markdown sections
    const overviewMarkdown = buildOverviewMarkdown(
      architecture?.style || 'Unknown',
      'System architecture as defined through design conversation.',
      stakeholderConcerns,
      glossaryTerms,
      architecture?.style || 'Unknown',
      conversationTitle || 'Architecture'
    );

    const moduleViewMarkdown = buildModuleViewMarkdown(
      architecture?.componentDiagram || null,
      architecture?.components || [],
      fmeaByComponent,
      tradeOffs,
      moduleAdlRules,
      weaknesses?.weaknesses || []
    );

    const ccViewMarkdown = buildCCViewMarkdown(
      architecture?.sequenceDiagram || null,
      architecture?.interactions || [],
      scenarios,
      connectorAdlRules,
      tradeOffs,
      fmea,
      weaknesses?.weaknesses || []
    );

    const allocationViewMarkdown = buildAllocationViewMarkdown(
      null,
      buyVsBuildSummary?.decisions || [],
      architecture?.components || [],
      allocationAdlRules,
      weaknesses?.weaknesses || []
    );

    const riskMarkdown = buildRiskMarkdown(
      allAdlRules,
      weaknesses?.weaknesses || [],
      fmea,
      governanceReport?.improvementRecommendations || []
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
      systemTitle: architecture?.style || 'Architecture',
      systemDescription: 'System architecture as defined through design conversation.',
      conversationTitle: conversationTitle || 'Architecture',
      stakeholderConcerns,
      glossaryTerms,
      componentDiagram: architecture?.componentDiagram || null,
      deploymentDiagram: null,
      components: architecture?.components || [],
      fmeaByComponent,
      moduleAdlRules,
      sequencePrimaryDiagram: architecture?.sequenceDiagram || null,
      sequenceErrorDiagram: null,
      interactions: architecture?.interactions || [],
      scenarios,
      connectorAdlRules,
      buyVsBuildDecisions: buyVsBuildSummary?.decisions || [],
      allocationAdlRules,
      adlDocument: adl,
      allAdlRules,
      weaknesses: weaknesses?.weaknesses || [],
      fmeaAll: fmea,
      improvementRecommendations: governanceReport?.improvementRecommendations || [],
      tradeOffs,
      fullPackageMarkdown,
      overviewMarkdown,
      moduleViewMarkdown,
      ccViewMarkdown,
      allocationViewMarkdown,
      riskMarkdown,
      exportFilename: `architecture-docs-${slugifyTitle(conversationTitle || 'architecture')}-${getCurrentDate()}.md`,
      loading,
      error: error || null,
      hasData: (architecture?.components?.length || 0) > 0,
    };
  }, [
    architecture,
    adl,
    weaknesses,
    fmea,
    tradeOffs,
    governanceReport,
    buyVsBuildSummary,
    conversationTitle,
    archLoading,
    govLoading,
    tacticsLoading,
    bbLoading,
    archError,
    govError,
    tacticsError,
    bbError,
    tactics,
  ]);

  return archDocData;
}
