import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { ForgeHomePage } from '../views/forge/ForgeHomePage';

describe('ForgeHomePage', () => {
  it('renders planned pillar messaging', () => {
    render(
      <MemoryRouter>
        <ForgeHomePage />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('forge-home-page')).toBeInTheDocument();
    expect(screen.getByText('Planned Pillar')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to Axiom/i })).toHaveAttribute('href', '/');
  });
});
