import type { StageState } from '../types/api';
import { PIPELINE_STAGES } from '../types/api';

const STAGE_LABELS: Record<string, string> = {
  requirement_parsing: 'Requirement Parsing',
  requirement_challenge: 'Requirement Challenge',
  scenario_modeling: 'Scenario Modeling',
  characteristic_inference: 'Characteristic Inference',
  tactics_recommendation: 'Tactics Recommendation',
  conflict_analysis: 'Conflict Analysis',
  architecture_generation: 'Architecture Generation',
  buy_vs_build_analysis: 'Evaluating build vs buy decisions',
  diagram_generation: 'Diagram Generation',
  trade_off_analysis: 'Trade-off Analysis',
  adl_generation: 'ADL Generation',
  weakness_analysis: 'Weakness Analysis',
  fmea_analysis: 'FMEA Analysis',
  architecture_review: 'Architecture Review',
};

function StatusIcon({ status }: { status: string }) {
  const base = 'w-3.5 h-3.5 shrink-0';
  switch (status) {
    case 'complete':
      return (
        <svg className={`${base} text-emerald-400`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 8l3.5 3.5L13 5" />
        </svg>
      );
    case 'running':
      return (
        <svg className={`${base} text-accent animate-spin`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="8" cy="8" r="6" strokeOpacity="0.25" />
          <path d="M8 2a6 6 0 0 1 6 6" />
        </svg>
      );
    case 'error':
      return (
        <svg className={`${base} text-red-400`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      );
    case 'aborted':
      return (
        <svg className={`${base} text-gray-500`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M4 8h8" />
        </svg>
      );
    default: // pending
      return (
        <svg className={`${base} text-gray-600`} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="8" cy="8" r="4" />
        </svg>
      );
  }
}

function statusSymbol(status: string): string {
  switch (status) {
    case 'complete':
      return '✓';
    case 'running':
      return '⟳';
    case 'error':
      return '✗';
    case 'aborted':
      return '–';
    default:
      return '○';
  }
}

function rowTextColor(status: string): string {
  switch (status) {
    case 'complete': return 'text-gray-400';
    case 'running':  return 'text-gray-100 font-medium';
    case 'error':    return 'text-red-400';
    case 'aborted':  return 'text-gray-600';
    default:         return 'text-gray-600';
  }
}

interface StageProgressProps {
  stages: StageState[];
}

export function StageProgress({ stages }: StageProgressProps) {
  const stageMap = new Map(stages.map((s) => [s.name, s]));

  return (
    <div className="space-y-0.5" data-testid="stage-progress">
      {PIPELINE_STAGES.map((name) => {
        const stage = stageMap.get(name);
        const status = stage?.status ?? 'pending';
        return (
          <div
            key={name}
            className={`flex items-center gap-2 px-3 py-1 rounded-md text-[12px] transition-colors ${rowTextColor(status)} ${status === 'running' ? 'bg-accent/10' : ''}`}
            data-testid={`stage-${name}`}
            data-status={status}
          >
            <span className="sr-only">{statusSymbol(status)}</span>
            <StatusIcon status={status} />
            <span className="truncate leading-tight">{STAGE_LABELS[name] ?? name}</span>
          </div>
        );
      })}
    </div>
  );
}
