/* ── Pipeline stage names ─────────────────────────── */

export const PIPELINE_STAGES = [
  'requirement_parsing',
  'requirement_challenge',
  'scenario_modeling',
  'characteristic_inference',
  'tactics_recommendation',
  'conflict_analysis',
  'architecture_generation',
  'buy_vs_build_analysis',
  'diagram_generation',
  'trade_off_analysis',
  'adl_generation',
  'weakness_analysis',
  'fmea_analysis',
  'architecture_review',
] as const;

export type StageName = (typeof PIPELINE_STAGES)[number];

export type StageStatus = 'pending' | 'running' | 'complete' | 'error' | 'aborted';

export interface StageState {
  name: StageName;
  status: StageStatus;
  payload?: Record<string, unknown>;
}

/* ── SSE / Agent event types ─────────────────────── */

export type EventType =
  | 'CHUNK'
  | 'STAGE_START'
  | 'STAGE_COMPLETE'
  | 'TOOL_CALL'
  | 'COMPLETE'
  | 'RE_ITERATE'
  | 'RUN_CREATED'
  | 'ERROR';

export interface AgentEvent {
  type: EventType;
  stage?: string;
  content?: string;
  conversationId?: string;
  payload?: Record<string, unknown>;
}

export interface PipelineRunStatusDto {
  runId: string;
  conversationId: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'COMPLETED_WITH_GAPS';
  lastStageCompleted?: string | null;
  startedAt: string;
  completedAt?: string | null;
  governanceScore?: number | null;
  governanceConfidence?: string | null;
  hasGaps?: boolean | null;
  gapSummary?: string | null;
  errorStage?: string | null;
  errorMessage?: string | null;
  eventCount: number;
}

/* ── Auth ─────────────────────────────────────────── */

export interface AuthTokenResponse {
  token: string;
  email?: string;
}

/* ── Architecture output ─────────────────────────── */

export interface Component {
  name: string;
  responsibility: string;
  technology: string;
}

export interface Interaction {
  from: string;
  to: string;
  protocol: string;
  purpose: string;
}

export interface ArchitectureOutput {
  conversationId: string;
  style: string;
  components: Component[];
  interactions: Interaction[];
  componentDiagram: string;
  sequenceDiagram: string;
  overrideApplied?: boolean;
  overrideWarning?: string;
}

/* ── Diagrams ─────────────────────────────────────── */

export interface DiagramDto {
  diagramId: string;
  type: string;
  title: string;
  description: string;
  mermaidSource: string;
  characteristicAddressed: string;
}

export interface DiagramCollectionDto {
  diagrams: DiagramDto[];
  diagramCount: number;
  diagramTypes: string[];
}

/* ── Governance: Trade-offs ──────────────────────── */

export interface TradeOffDecision {
  decision_id: string;
  decision: string;
  recommendation: string;
  context_dependency: string;
  confidence: string;
  confidence_reason?: string;
  optimises_characteristics: string[];
  sacrifices_characteristics: string[];
  options_considered?: { option: string; rejected_because: string }[];
  acceptable_because?: string;
}

/* ── Governance: ADL ─────────────────────────────── */

export interface AdlValidationHint {
  type: string;
  test_type?: string;
  pseudo_code?: string;
  enforcement_level?: string;
}

export interface AdlRule {
  rule_id: string;
  category: string;
  subject: string;
  statement: string;
  rationale?: string;
  validation_hint?: AdlValidationHint;
  optimises_characteristics?: string[];
}

export interface AdlDocument {
  document: string;
  rules: AdlRule[];
}

/* ── Governance: Weaknesses ──────────────────────── */

export interface Weakness {
  id: string;
  title: string;
  description: string;
  severity: number;
  likelihood?: number;
  category?: string;
  component_affected: string;
  mitigation: string;
  effort_to_fix?: string;
  early_warning_signals?: string[];
  linked_characteristic?: string;
}

export interface WeaknessReport {
  weaknesses: Weakness[];
  summary: string;
}

/* ── Governance: FMEA ────────────────────────────── */

export interface FmeaEntry {
  id: string;
  failure_mode: string;
  component: string;
  severity: number;
  occurrence: number;
  detection: number;
  rpn: number;
  recommended_action: string;
}

/* ── Tactics ─────────────────────────────────────── */

/**
 * A single tactic recommendation from the Bass/Clements/Kazman catalog
 * (Software Architecture in Practice, 4th ed., SEI/Addison-Wesley 2021).
 */
export interface TacticRecommendation {
  id: string;
  tacticId: string;
  tacticName: string;
  characteristicName: string;
  category: string;
  description: string;
  concreteApplication: string;
  implementationExamples: string[];
  alreadyAddressed: boolean;
  addressEvidence: string;
  effort: 'low' | 'medium' | 'high';
  priority: 'critical' | 'recommended' | 'optional';
  createdAt: string;
}

export interface TacticsSummary {
  totalTactics: number;
  criticalCount: number;
  alreadyAddressedCount: number;
  newTacticsCount: number;
  perCharacteristic: Record<string, number>;
  summary: string;
  topCriticalTactics: string[];
}

/* ── Buy vs Build ───────────────────────────────── */

export interface BuyVsBuildDecision {
  componentName: string;
  recommendation: 'build' | 'buy' | 'adopt';
  rationale: string;
  alternativesConsidered: string[];
  recommendedSolution: string;
  estimatedBuildCost: string;
  vendorLockInRisk: 'low' | 'medium' | 'high';
  integrationEffort: 'low' | 'medium' | 'high';
  conflictsWithUserPreference: boolean;
  conflictExplanation: string;
  isCoreeDifferentiator: boolean;
}

export interface BuyVsBuildSummary {
  summaryText: string;
  totalDecisions: number;
  buildCount: number;
  buyCount: number;
  adoptCount: number;
  conflictCount: number;
  decisions: BuyVsBuildDecision[];
}

export interface ArchitectureOverride {
  type: 'pinned' | 'candidate_set' | 'rejection' | 'none';
  styles: string[];
  rawInstruction: string;
  overrideWarning: string;
  overrideApplied: boolean;
}

/* ── Governance: Report ──────────────────────────── */

export interface GovernanceScoreBreakdown {
  requirement_coverage: number;
  architectural_soundness: number;
  risk_mitigation: number;
  governance_completeness: number;
  total: number;
  justification: string;
}

export interface ImprovementRecommendation {
  area: string;
  recommendation: string;
  priority: 'low' | 'medium' | 'high';
  requires_reiteration: boolean;
}

export interface GovernanceReport {
  id: string;
  conversationId: string;
  iteration: number;
  governanceScore: number | null;
  governanceScoreConfidence: 'high' | 'partial' | 'low' | 'unavailable';
  reviewCompletedFully: boolean;
  failedReviewNodes: string[];
  requirementCoverage: number;
  architecturalSoundness: number;
  riskMitigation: number;
  governanceCompleteness: number;
  justification: string;
  shouldReiterate: boolean;
  reviewFindings: Record<string, unknown>;
  improvementRecommendations: ImprovementRecommendation[];
  createdAt: string;
}

/* ── Chat request ────────────────────────────────── */

export type ChatRole = 'USER' | 'ASSISTANT' | 'SYSTEM';

export interface ChatMessage {
  id?: string;
  role: ChatRole;
  content: string;
  createdAt?: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ChatRequest {
  message: string;
  conversationId?: string;
}
