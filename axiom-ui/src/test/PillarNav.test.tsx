import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { PillarNav } from '../components/PillarNav';

describe('PillarNav', () => {
  it('showsArchonAsTheActivePillar', () => {
    render(
      <MemoryRouter initialEntries={['/archon']}>
        <PillarNav />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('pillar-nav')).toBeInTheDocument();
    expect(screen.getByTestId('pillar-archon')).toHaveAttribute('aria-current', 'page');
  });

  it('shows specweaver as enabled', () => {
    render(
      <MemoryRouter>
        <PillarNav />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('pillar-specweaver')).toHaveAttribute('href', '/specweaver');
  });

  it('shows scout as enabled link', () => {
    render(
      <MemoryRouter>
        <PillarNav />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('pillar-scout')).toHaveAttribute('href', '/scout');
  });

  it('shows forge as enabled link', () => {
    render(
      <MemoryRouter>
        <PillarNav />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('pillar-forge')).toHaveAttribute('href', '/forge');
  });

  it('active pillar uses pillar colour for highlight', () => {
    render(
      <MemoryRouter initialEntries={['/specweaver']}>
        <PillarNav />
      </MemoryRouter>,
    );

    const specweaver = screen.getByTestId('pillar-specweaver');
    expect(specweaver).toHaveAttribute('aria-current', 'page');
    expect(specweaver.getAttribute('style')).toContain('--color-pillar-specweaver');
  });
});
