import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HomeView } from '../views/HomeView';

describe('HomeView', () => {
  it('rendersHomeViewContainer', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByTestId('home-view')).toBeInTheDocument();
  });

  it('rendersArchonHeading', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Archon' })).toBeInTheDocument();
  });

  it('rendersStartSessionButton', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByTestId('home-start-session')).toBeInTheDocument();
    expect(screen.getByTestId('home-start-session')).toHaveTextContent(
      'Start an architecture session',
    );
  });

  it('callsOnStartSessionWhenButtonClicked', async () => {
    const onStartSession = vi.fn();
    const user = userEvent.setup();

    render(<HomeView onStartSession={onStartSession} />);
    await user.click(screen.getByTestId('home-start-session'));

    expect(onStartSession).toHaveBeenCalledOnce();
  });

  it('rendersPipelineStagesSection', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByText('Pipeline stages')).toBeInTheDocument();
    // The pipeline list should render all 13 stages
    expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(13);
  });

  it('rendersRequirementParsingStage', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByText('Requirement parsing')).toBeInTheDocument();
  });

  it('rendersGovernanceStageWithReviewBadge', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByText('Architecture review')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
    expect(
      screen.getByText(/Governance stage.*independent review/),
    ).toBeInTheDocument();
  });

  it('rendersKeyCapabilitiesSection', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByText('Key capabilities')).toBeInTheDocument();
    expect(screen.getByText('Architecture style selection')).toBeInTheDocument();
    expect(screen.getByText('Architecture tactics')).toBeInTheDocument();
    // 'Buy vs build analysis' also appears in the pipeline stages list.
    expect(screen.getAllByText('Buy vs build analysis').length).toBeGreaterThan(0);
    expect(screen.getByText('Executable governance')).toBeInTheDocument();
    expect(screen.getByText('FMEA and weakness analysis')).toBeInTheDocument();
    expect(screen.getByText('Architecture review agent')).toBeInTheDocument();
  });

  it('rendersOutputArtifactsSection', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    expect(screen.getByText('Output artifacts')).toBeInTheDocument();
    expect(screen.getByText(/Architecture diagrams/)).toBeInTheDocument();
  });

  it('rendersWhyItsDifferentSection', () => {
    render(<HomeView onStartSession={vi.fn()} />);

    // The heading uses a curly/smart apostrophe (U+2019), matched via regex.
    expect(screen.getByText(/Why it.s different/)).toBeInTheDocument();
    expect(
      screen.getByText(/Requirements are challenged before design begins/),
    ).toBeInTheDocument();
  });
});
