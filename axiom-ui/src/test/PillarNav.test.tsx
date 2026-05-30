import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { PillarNav } from '../components/PillarNav';

describe('PillarNav', () => {
  it('showsArchonAsTheActivePillar', () => {
    render(<PillarNav />);

    expect(screen.getByTestId('pillar-nav')).toBeInTheDocument();
    expect(screen.getByTestId('pillar-archon')).toHaveAttribute('aria-current', 'page');
  });

  it('marksFuturePillarsAsComingSoon', () => {
    render(<PillarNav />);

    expect(screen.getAllByText('Coming soon')).toHaveLength(3);
    expect(screen.getByTestId('pillar-specweaver')).toBeDisabled();
    expect(screen.getByTestId('pillar-scout')).toBeDisabled();
    expect(screen.getByTestId('pillar-forge')).toBeDisabled();
  });
});