import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ReviewReport } from '../components/lens/ReviewReport';
import type { ReviewReport as LensReviewReport } from '../api/lens';

const sampleReport: LensReviewReport = {
  id: 'report-1',
  sessionId: 'session-1',
  executiveSummary: 'Review summary for the accreditation workflow.',
  overallRating: 'NEEDS_REWORK',
  azureWafScorecard: {
    pillars: {
      reliability: {
        score: 4,
        addressed: ['Active-active failover described'],
        gaps: ['RPO is not evidenced'],
        findings: ['Reliability posture is mostly covered.'],
      },
      security: {
        score: 3,
        addressed: ['Mutual TLS is documented'],
        gaps: ['Secret rotation is not evidenced'],
        findings: ['Security controls are partial.'],
      },
      cost_optimisation: {
        score: 2,
        addressed: ['Cost dashboards are mentioned'],
        gaps: ['No budget alert strategy'],
        findings: ['Cost controls are incomplete.'],
      },
      operational_excellence: {
        score: 3,
        addressed: ['Deployment automation is described'],
        gaps: ['No incident response playbooks'],
        findings: ['Ops process is only partially evidenced.'],
      },
      performance_efficiency: {
        score: 4,
        addressed: ['Scaling rules are described'],
        gaps: ['No cache invalidation evidence'],
        findings: ['Performance approach is plausible.'],
      },
    },
  },
  atamAnalysis: {
    quality_attribute_scenarios: [
      {
        scenario: 'Every accreditation result must be reproducible years after publication.',
        quality_attribute: 'Reproducibility',
        architecture_approach: 'Immutable calculation snapshots',
      },
    ],
    sensitivity_points: [
      { decision: 'Immutable snapshots', affected_attribute: 'Reproducibility', effect: 'Stable replay' },
    ],
    tradeoffs: [
      { decision: 'Immutable snapshots', gains: 'Auditability', costs: 'Higher storage demand' },
    ],
    risks: [
      { quality_attribute: 'Availability', scenario: 'Failover plan not proven', severity: 'HIGH' },
    ],
  },
  seiAnalysis: {
    attributes: {
      modifiability: {
        rating: 'ADEQUATE',
        tactics_present: ['Encapsulation through module boundaries'],
        tactics_missing: ['Deferred binding for rule changes'],
        observations: 'Business rules are isolated but deployment-time binding is absent.',
      },
      performance: {
        rating: 'WEAK',
        tactics_present: ['Horizontal scaling rules'],
        tactics_missing: ['Caching strategy'],
        observations: 'Scaling exists but no cache tactic is evidenced.',
      },
      availability: {
        rating: 'ADEQUATE',
        tactics_present: ['Active-active failover'],
        tactics_missing: ['Documented recovery objectives'],
        observations: 'Recovery automation is only partly evidenced.',
      },
      security: {
        rating: 'WEAK',
        tactics_present: ['Mutual TLS'],
        tactics_missing: ['Threat detection'],
        observations: 'Identity controls exist but monitoring is sparse.',
      },
      integrability: {
        rating: 'ADEQUATE',
        tactics_present: ['Published interface contracts'],
        tactics_missing: ['Error propagation standard'],
        observations: 'Integration contracts are present.',
      },
    },
  },
  structuralAnalysis: {
    coupling: {
      score: 4,
      observations: ['Modules communicate through explicit contracts.'],
    },
    cohesion: {
      score: 3,
      observations: ['Responsibilities are mostly aligned by domain.'],
    },
    dependency_direction: {
      score: 2,
      observations: ['A reporting flow still depends on a shared rules package.'],
    },
    boundary_clarity: {
      score: 4,
      observations: ['Ownership boundaries are described in the evidence.'],
    },
    structural_summary: 'Structural boundaries are mostly clear.',
  },
  insufficientInfoGaps: {},
  findings: [],
  risks: [
    {
      title: 'Security evidence is partial',
      description: 'Threat detection is not described.',
      severity: 'HIGH',
      likelihood: 'MEDIUM',
      affectedArea: 'Security',
      mitigationStrategy: 'Add monitoring and detection controls.',
      frameworkReference: 'Azure WAF - Security',
    },
  ],
  recommendationRoadmap: [
    {
      title: 'Define incident response playbooks',
      description: 'Establish production response runbooks.',
      priority: 'P1',
      effort: 'WEEKS',
      addresses_risk: 'Security evidence is partial',
    },
  ],
  generatedAt: '2026-06-27T00:00:00Z',
};

describe('ReviewReport', () => {
  it('renders nested WAF, ATAM, SEI, and structural payload shapes', async () => {
    const user = userEvent.setup();

    render(<ReviewReport report={sampleReport} />);

    await user.click(screen.getByRole('button', { name: 'Azure WAF' }));
    expect(screen.getAllByText('Operational Excellence').length).toBeGreaterThan(0);
    expect(screen.getByText(/Gaps: No incident response playbooks/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'ATAM' }));
    expect(screen.getByText('Reproducibility')).toBeInTheDocument();
    expect(screen.getByText('Immutable calculation snapshots')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'SEI' }));
    expect(screen.getByText(/Encapsulation through module boundaries/)).toBeInTheDocument();
    expect(screen.getByText(/Deferred binding for rule changes/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Structural' }));
    expect(screen.getAllByText('4.0 / 5').length).toBeGreaterThan(0);
    expect(screen.getByText(/Modules communicate through explicit contracts/)).toBeInTheDocument();
    expect(screen.getByText(/A reporting flow still depends on a shared rules package/)).toBeInTheDocument();
  });
});
