import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StageProgress } from '../components/StageProgress';
import type { StageState, StageName } from '../types/api';
import { PIPELINE_STAGES } from '../types/api';

function makeStages(overrides: Partial<Record<StageName, string>> = {}): StageState[] {
  return (PIPELINE_STAGES as readonly StageName[]).map((name) => ({
    name,
    status: (overrides[name] ?? 'pending') as StageState['status'],
  }));
}

describe('StageProgress', () => {
  it('renders_allStages', () => {
    render(<StageProgress stages={makeStages()} />);
    const container = screen.getByTestId('stage-progress');
    expect(container.children).toHaveLength(14);
  });

  it('displaysPendingIcon_forPendingStages', () => {
    render(<StageProgress stages={makeStages()} />);
    const stage = screen.getByTestId('stage-requirement_parsing');
    expect(stage).toHaveAttribute('data-status', 'pending');
    expect(stage.textContent).toContain('○');
  });

  it('displaysRunningIcon_forRunningStages', () => {
    render(
      <StageProgress stages={makeStages({ requirement_parsing: 'running' })} />,
    );
    const stage = screen.getByTestId('stage-requirement_parsing');
    expect(stage).toHaveAttribute('data-status', 'running');
    expect(stage.textContent).toContain('⟳');
  });

  it('displaysCompleteIcon_forCompleteStages', () => {
    render(
      <StageProgress stages={makeStages({ requirement_parsing: 'complete' })} />,
    );
    const stage = screen.getByTestId('stage-requirement_parsing');
    expect(stage).toHaveAttribute('data-status', 'complete');
    expect(stage.textContent).toContain('✓');
  });

  it('displaysErrorIcon_forErrorStages', () => {
    render(
      <StageProgress stages={makeStages({ scenario_modeling: 'error' })} />,
    );
    const stage = screen.getByTestId('stage-scenario_modeling');
    expect(stage).toHaveAttribute('data-status', 'error');
    expect(stage.textContent).toContain('✗');
  });

  it('displaysHumanReadableLabels', () => {
    render(<StageProgress stages={makeStages()} />);
    expect(screen.getByText('Requirement Parsing')).toBeInTheDocument();
    expect(screen.getByText('Architecture Review')).toBeInTheDocument();
  });
});
