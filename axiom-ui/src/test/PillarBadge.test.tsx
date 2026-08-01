import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { PillarBadge } from '../components/PillarBadge';

describe('PillarBadge', () => {
  it('renders pillar name when showLabel=true', () => {
    render(<PillarBadge pillar="specweaver" showLabel />);

    expect(screen.getByText('SpecWeaver')).toBeInTheDocument();
  });

  it('hides label when showLabel=false', () => {
    render(<PillarBadge pillar="specweaver" showLabel={false} />);

    expect(screen.queryByText('SpecWeaver')).not.toBeInTheDocument();
  });

  it('applies correct CSS class for each pillar', () => {
    const pillars = ['axiom', 'archon', 'specweaver', 'lens'] as const;

    pillars.forEach((pillar) => {
      const { unmount } = render(<PillarBadge pillar={pillar} />);
      expect(screen.getByTestId(`pillar-badge-${pillar}`)).toHaveClass(`pillar-badge--${pillar}`);
      unmount();
    });
  });
});
