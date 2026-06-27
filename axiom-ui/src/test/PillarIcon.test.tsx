import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { PillarIcon } from '../components/PillarIcon';

describe('PillarIcon', () => {
  it('renders specweaver icon without crashing', () => {
    render(<PillarIcon pillar="specweaver" />);

    expect(screen.getByTestId('pillar-icon-specweaver')).toBeInTheDocument();
  });

  it('renders archon icon without crashing', () => {
    render(<PillarIcon pillar="archon" />);

    expect(screen.getByTestId('pillar-icon-archon')).toBeInTheDocument();
  });

  it('renders lens icon without crashing', () => {
    render(<PillarIcon pillar="lens" />);

    expect(screen.getByTestId('pillar-icon-lens')).toBeInTheDocument();
  });

  it('renders axiom icon without crashing', () => {
    render(<PillarIcon pillar="axiom" />);

    expect(screen.getByTestId('pillar-icon-axiom')).toBeInTheDocument();
  });

  it('applies custom size prop', () => {
    render(<PillarIcon pillar="archon" size={28} />);

    const icon = screen.getByTestId('pillar-icon-archon');
    expect(icon).toHaveAttribute('width', '28');
    expect(icon).toHaveAttribute('height', '28');
  });
});
