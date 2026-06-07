import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { ScoutHomePage } from '../views/scout/ScoutHomePage';

describe('ScoutHomePage', () => {
  it('renders planned pillar messaging', () => {
    render(
      <MemoryRouter>
        <ScoutHomePage />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('scout-home-page')).toBeInTheDocument();
    expect(screen.getByText('Planned Pillar')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to Axiom/i })).toHaveAttribute('href', '/');
  });
});
