import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AxiomHomePage } from '../views/AxiomHomePage';

describe('AxiomHomePage', () => {
  it('renders pillar cards and workflow section', () => {
    render(
      <MemoryRouter>
        <AxiomHomePage />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('axiom-home-page')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-pillar-card-specweaver')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-pillar-card-archon')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-pillar-card-scout')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-pillar-card-forge')).toBeInTheDocument();
    expect(screen.getByText('The Workflow')).toBeInTheDocument();
  });
});
