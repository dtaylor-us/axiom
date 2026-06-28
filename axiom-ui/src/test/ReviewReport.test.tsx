import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ReviewReport } from '../components/lens/ReviewReport';
import type { ReviewReport as LensReviewReport } from '../api/lens';

const report: LensReviewReport = {
  id: 'report-1',
  sessionId: 'lens-1',
  executiveSummary: 'Strong foundations with a few gaps to close.',
  azureWafScorecard: {
    reliability: { score: 4.5, addressed: ['Retries'], gaps: ['No multi-region failover'], findings: ['DR plan missing'] },
    security: { score: 4.0, addressed: ['Auth'], gaps: [], findings: [] },
    cost: { score: 3.0, addressed: ['Budgets'], gaps: ['No alerts'], findings: [] },
    operational_excellence: { score: 2.5, addressed: ['Runbooks'], gaps: [], findings: ['No dashboards'] },
    performance_efficiency: { score: 4.0, addressed: ['Caching'], gaps: [], findings: [] },
  },
  atamAnalysis: {
    quality_attribute_scenarios: [
      { scenario: 'Traffic spike', attribute: 'performance', response: 'Scales horizontally' },
    ],
    sensitivity_points: ['Database pool size'],
    tradeoffs: ['Throughput vs. simplicity'],
    risks: [{ title: 'Single region', severity: 'high' }],
  },
  seiAnalysis: {
    modifiability: { rating: 'GOOD', tactics_present: ['Layered modules'], tactics_missing: [] },
    performance: { rating: 'FAIR', tactics_present: ['Caching'], tactics_missing: ['Async queues'] },
    availability: { rating: 'GOOD', tactics_present: ['Health probes'], tactics_missing: [] },
    security: { rating: 'EXCELLENT', tactics_present: ['Least privilege'], tactics_missing: [] },
    integrability: { rating: 'FAIR', tactics_present: ['REST APIs'], tactics_missing: ['Event contracts'] },
  },
  structuralAnalysis: {
    coupling_score: 3.5,
    cohesion_score: 4.0,
    dependency_direction_score: 4.5,
    boundary_clarity_score: 3.0,
    observations: ['Shared ownership across services'],
  },
  insufficientInfoGaps: {},
  findings: [
    {
      findingType: 'INSUFFICIENT_INFORMATION',
      category: 'SECURITY',
      title: 'Missing auth evidence',
      description: 'No explicit authentication evidence was provided.',
      evidence: 'Review notes',
      frameworkReference: 'AZURE-WAF-SECURITY',
      severity: 'HIGH',
    },
  ],
  risks: [
    {
      title: 'No multi-region failover',
      description: 'Single-region deployment',
      severity: 'CRITICAL',
      likelihood: 'MEDIUM',
      affectedArea: 'Reliability',
      mitigationStrategy: 'Add active-active region support',
      frameworkReference: 'AZURE-WAF-RELIABILITY',
    },
    {
      title: 'Slow builds',
      description: 'Build pipeline takes too long',
      severity: 'HIGH',
      likelihood: 'LOW',
      affectedArea: 'Operations',
      mitigationStrategy: 'Parallelize pipeline steps',
      frameworkReference: 'AZURE-WAF-OPERATIONS',
    },
  ],
  recommendationRoadmap: [
    {
      priority: 'P1',
      title: 'Add multi-region failover',
      description: 'Duplicate critical services across regions.',
      effort: 'L',
      addresses_risk: 'No multi-region failover',
    },
    {
      priority: 'P2',
      title: 'Improve build observability',
      description: 'Expose pipeline metrics.',
      effort: 'S',
      addresses_risk: 'Slow builds',
    },
  ],
  overallRating: 'APPROVED_WITH_CONDITIONS',
  generatedAt: '2026-06-27T00:00:00Z',
};

describe('ReviewReport', () => {
  it('renders report sections and supports tab switching', async () => {
    const user = userEvent.setup();
    render(<ReviewReport report={report} />);

    expect(screen.getByTestId('lens-review-report')).toBeInTheDocument();
    expect(screen.getByText('APPROVED_WITH_CONDITIONS')).toHaveClass('bg-amber-100');
    expect(screen.getByText('Strong foundations with a few gaps to close.')).toBeInTheDocument();
    expect(screen.getByText('1 insufficient-information finding(s) were included due to unresolved gap evidence.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Azure WAF' }));
    expect(screen.getAllByText('Reliability')).toHaveLength(2);
    expect(screen.getAllByText(/Gaps:\s*1/)).toHaveLength(2);

    await user.click(screen.getByRole('button', { name: 'ATAM' }));
    expect(screen.getByText('Traffic spike')).toBeInTheDocument();
    expect(screen.getByText('Throughput vs. simplicity')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'SEI' }));
    expect(screen.getByText(/modifiability/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Rating:\s*GOOD/)).not.toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Structural' }));
    expect(screen.getByText('Coupling')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Risks' }));
    expect(screen.getByText('No multi-region failover')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Severity'), 'HIGH');
    expect(screen.queryByText('No multi-region failover')).not.toBeInTheDocument();
    expect(screen.getByText('Slow builds')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Recommendations' }));
    expect(screen.getByText('P1 recommendations (1)')).toBeInTheDocument();
    expect(screen.getByText('Add multi-region failover')).toBeInTheDocument();
  });
});
