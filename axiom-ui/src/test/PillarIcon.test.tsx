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

    const icon = screen.getByTestId('pillar-icon-archon');
    expect(icon).toBeInTheDocument();
    expect(icon.querySelectorAll('rect')).toHaveLength(3);
    expect(icon.querySelector('path')).toHaveAttribute('d', 'M12 9v3m-4.5 0h9M7.5 12v3m9-3v3');
  });

  it('renders lens icon without crashing', () => {
    render(<PillarIcon pillar="lens" />);

    const icon = screen.getByTestId('pillar-icon-lens');
    expect(icon).toBeInTheDocument();
    expect(icon.querySelector('circle')).toHaveAttribute('cx', '10.5');
    expect(icon.querySelector('path')).toHaveAttribute('d', 'M14.5 14.5 20 20');
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
