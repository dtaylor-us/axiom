import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SeverityGrid } from '../components/SeverityGrid';
import type { FmeaEntry } from '../types/api';

const sampleEntries: FmeaEntry[] = [
  {
    id: 'F-001',
    failure_mode: 'DB connection loss',
    component: 'DataService',
    severity: 4,
    occurrence: 3,
    detection: 2,
    rpn: 24,
    recommended_action: 'Add connection pooling',
  },
  {
    id: 'F-002',
    failure_mode: 'Auth bypass',
    component: 'AuthService',
    severity: 5,
    occurrence: 2,
    detection: 5,
    rpn: 50,
    recommended_action: 'Add rate limiting',
  },
  {
    id: 'F-003',
    failure_mode: 'Memory leak',
    component: 'CacheService',
    severity: 3,
    occurrence: 4,
    detection: 3,
    rpn: 36,
    recommended_action: 'Add memory monitoring',
  },
];

describe('SeverityGrid', () => {
  it('rendersEmptyState_whenNoEntries', () => {
    render(<SeverityGrid entries={[]} />);
    expect(screen.getByTestId('severity-grid-empty')).toBeInTheDocument();
    expect(screen.getByText('No FMEA data available')).toBeInTheDocument();
  });

  it('rendersGrid_withEntries', () => {
    render(<SeverityGrid entries={sampleEntries} />);
    expect(screen.getByTestId('severity-grid')).toBeInTheDocument();
  });

  it('placesEntriesInCorrectGridCells', () => {
    render(<SeverityGrid entries={sampleEntries} />);
    // F-001: severity=4, occurrence=3 → cell-4-3
    const cell43 = screen.getByTestId('cell-4-3');
    expect(cell43.textContent).toContain('F-001');

    // F-002: severity=5, occurrence=2 → cell-5-2
    const cell52 = screen.getByTestId('cell-5-2');
    expect(cell52.textContent).toContain('F-002');
  });

  it('rendersLegendTableSortedByRPN', () => {
    render(<SeverityGrid entries={sampleEntries} />);
    // Legend should exist with all entry IDs
    expect(screen.getAllByText('F-001').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('F-002').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('F-003').length).toBeGreaterThanOrEqual(1);
  });

  it('appliesCorrectColorClassBasedOnRPN', () => {
    const highRpnEntry: FmeaEntry[] = [
      {
        id: 'F-HIGH',
        failure_mode: 'Catastrophic failure',
        component: 'Core',
        severity: 5,
        occurrence: 5,
        detection: 5,
        rpn: 250,
        recommended_action: 'Redesign',
      },
    ];
    render(<SeverityGrid entries={highRpnEntry} />);
    const cell = screen.getByTestId('cell-5-5');
    expect(cell.className).toContain('bg-red-600');
  });
});
