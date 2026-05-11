// Workshop domain types — field names match the Java API DTOs exactly.

export interface WorkshopSessionSummary {
  sessionId: string;
  systemName: string;
  workshopPhase: string;
  turnCount: number;
  totalGaps: number;
  filledGaps: number;
  inProgressGaps?: number;
  gapCompletionPct: number;
  attributeCount: number;
  confirmedAttributeCount: number;
  isComplete: boolean;
  hasSufficientAttributes: boolean;
  readyForPipeline: boolean;
  openGaps: OpenGap[];
  createdAt: string;
  lastUpdated: string;
  generationCount?: number;
  attributesStale?: boolean;
}

export interface WorkshopMessage {
  messageId: string;
  turnNumber: number;
  userInput: string;
  agentResponse: string;
  workshopPhase: string;
  createdAt: string;
}

export interface OpenGap {
  gapId: string;
  category: string;
  description: string;
  priority: string;
  residualQuestion?: string;
  resolutionConfidence?: number;
}

export interface GapSummary {
  total: number;
  filled: number;
  completionPct: number;
  inProgressCount?: number;
  openGaps: OpenGap[];
}

export interface WorkshopTurnResponse {
  sessionId: string;
  turnNumber: number;
  workshopPhase: string;
  agentMessage: string;
  questionsAsked: string[];
  gapSummary: GapSummary;
  attributes: QualityAttribute[];
  isComplete: boolean;
  readyForPipeline: boolean;
  nonQaConcerns?: NonQaConcern[];
}

export interface NonQaConcern {
  name: string;
  description: string;
  category: string;
}

export interface QualityScenario {
  stimulus?: string;
  source?: string;
  environment?: string;
  artifact?: string;
  response?: string;
  responseMeasure?: string;
  completeness?: string;
}

/** Workshop scenario from GET /sessions/{id}/scenarios — camelCase from API. */
export interface WorkshopScenario {
  scenarioId: string;
  title: string;
  stimulus: string;
  source: string;
  environment: string;
  artifact: string;
  response: string;
  responseMeasure: string;
  exercisesAttributes: string[];
  evidenceQuote: string;
  derivedInTurn: number;
  completeness: string;
}

export interface ResolvedAnswer {
  question: string;
  answer: string;
  resolvedInTurn: number;
  evidenceQuote: string;
}

export interface QualityAttribute {
  attributeId: string;
  name: string;
  category: string;
  importance: string;
  confidence: string;
  description: string;
  scenarioCompleteness: string;
  openQuestions: string[];
  evidenceQuotes: string[];
  resolvedAnswers?: ResolvedAnswer[];
  questionsResolvedCount?: number;
  lastUpdateSummary?: string;
  lastUpdatedTurn?: number;
  firstGenerationPass?: number | null;
  lastGenerationPass?: number | null;
}

export interface GenerationReadinessDto {
  overallReadiness: 'insufficient' | 'partial' | 'adequate' | 'strong';
  confidenceNote: string;
  attributePreview: AttributePreviewDto[];
  highValueGaps: HighValueGapDto[];
  missingDomains: string[];
  canProduceUsefulOutput: boolean;
}

export interface AttributePreviewDto {
  name: string;
  confidence: 'confirmed' | 'inferred' | 'tentative';
  reason: string;
}

export interface HighValueGapDto {
  gapId: string;
  description: string;
  impact: string;
}

export interface WorkshopGenerationResponseDto {
  sessionId: string;
  generationCount: number;
  overallReadiness: string;
  confidenceNote: string;
  attributesGenerated: number;
  attributePreview: AttributePreviewDto[];
  highValueGaps: HighValueGapDto[];
  missingDomains: string[];
  generationSummary: string;
  attributes: QualityAttribute[];
  canContinueRefining: boolean;
  continuationPrompt: string;
  attributesStale: boolean;
}

export interface SummaryAttribute {
  name: string;
  importance: string;
  confidence: string;
  category: string;
  description: string;
  scenario: QualityScenario;
  evidence: string;
}

export interface AttributeSummary {
  systemDescription: string;
  qualityAttributes: SummaryAttribute[];
  openQuestions: string[];
  elicitationCompleteness: string;
  completenessRationale: string;
  readyForArchitecturePipeline: boolean;
  pipelineReadinessNotes: string;
}
