import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getDiagramByType } from '../api/architecture';
import { listSessions } from '../api/sessions';
import { useArchitecture } from '../hooks/useArchitecture';
import { useArchDoc, resolveAdlCategory, resolveAdlEnforcement, resolveAdlId, resolveAdlRationale, resolveAdlSubject } from '../hooks/useArchDoc';
import { useBuyVsBuild } from '../hooks/useBuyVsBuild';
import { useGovernance } from '../hooks/useGovernance';
import { useTactics } from '../hooks/useTactics';

vi.mock('../store/useStore', () => ({
  useStore: vi.fn((selector: (state: unknown) => unknown) =>
    selector({ token: 'jwt', conversationId: 'conversation-1' }),
  ),
}));
vi.mock('../api/architecture', () => ({ getDiagramByType: vi.fn() }));
vi.mock('../api/sessions', () => ({ listSessions: vi.fn() }));
vi.mock('../hooks/useArchitecture', () => ({ useArchitecture: vi.fn() }));
vi.mock('../hooks/useGovernance', () => ({ useGovernance: vi.fn() }));
vi.mock('../hooks/useTactics', () => ({ useTactics: vi.fn() }));
vi.mock('../hooks/useBuyVsBuild', () => ({ useBuyVsBuild: vi.fn() }));

const mocked = <T,>(value: T) => value as never;

describe('useArchDoc', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listSessions).mockResolvedValue(mocked([{ id: 'conversation-1', title: 'Claims Platform' }]));
    vi.mocked(getDiagramByType).mockResolvedValue('graph TD; Web-->API');
    vi.mocked(useArchitecture).mockReturnValue(mocked({
      architecture: {
        conversationId: 'conversation-1',
        style: 'event-driven microservices',
        componentDiagram: 'graph LR; Portal-->Gateway',
        sequenceDiagram: 'sequenceDiagram\nPortal->>Gateway: Submit claim',
        components: [
          { name: 'API Gateway', type: 'service', technology: 'Spring', responsibility: 'Routes and authenticates all inbound claims requests for downstream services.' },
          { name: 'Claims Service', type: 'service', technology: 'Java', responsibility: 'Validates, persists, and coordinates the complete claims processing lifecycle.' },
          { name: 'Event Broker', type: 'infrastructure', technology: 'Kafka', responsibility: 'Provides durable asynchronous delivery of domain events between claim components.' },
        ],
        interactions: [
          { from: 'API Gateway', to: 'Claims Service', protocol: 'HTTPS', purpose: 'Submit and query claims' },
          { from: 'Claims Service', to: 'Event Broker', protocol: 'Kafka', purpose: 'Publish ClaimSubmitted events' },
        ],
      },
      loading: false,
      error: null,
    }));
    vi.mocked(useGovernance).mockReturnValue(mocked({
      tradeOffs: [{
        decision_id: 'TD-1', decision: 'Use asynchronous events', recommendation: 'Adopt Kafka',
        context_dependency: 'High throughput', confidence: 'high',
        optimises_characteristics: ['Scalability', 'Availability'], sacrifices_characteristics: ['Simplicity'],
        options_considered: [{ option: 'Synchronous HTTP', rejected_because: 'Tight coupling' }],
        acceptable_because: 'Operations can support Kafka',
      }],
      adl: { document: 'claims.adl', rules: [
        { rule_id: 'ADL-1', category: 'module dependency', subject: 'Claims module boundary', statement: 'Modules must not bypass APIs.', rationale: 'Preserves ownership', validation_hint: { enforcement_level: 'required' } },
        { rule_id: 'ADL-2', category: 'connector protocol', subject: 'Service communication', statement: 'External calls use HTTPS.', rationale: 'Protects data in transit' },
        { rule_id: 'ADL-3', category: 'cloud deployment', subject: 'Regional deployment', statement: 'Services run across zones.', rationale: 'Improves availability' },
      ] },
      weaknesses: { summary: 'One material risk', weaknesses: [{
        id: 'W-1', title: 'Broker concentration', description: 'A broker outage interrupts processing.', severity: 8,
        likelihood: 4, category: 'availability', component_affected: 'Event Broker', mitigation: 'Deploy a multi-zone cluster',
        effort_to_fix: 'medium', early_warning_signals: ['Consumer lag'], linked_characteristic: 'Availability',
      }] },
      fmea: [{ id: 'F-1', failure_mode: 'Broker unavailable', component: 'Event Broker', severity: 8, occurrence: 4, detection: 3, rpn: 96, recommended_action: 'Use multi-zone replication' }],
      governanceReport: { improvementRecommendations: [{ area: 'Resilience', recommendation: 'Exercise broker failover.', priority: 'high', requires_reiteration: true }] },
      loading: false,
      error: null,
    }));
    vi.mocked(useTactics).mockReturnValue(mocked({
      tactics: [{ id: '1', tacticId: 'T-1', tacticName: 'Active redundancy', characteristicName: 'Availability', category: 'fault recovery', description: 'Maintain redundant instances.', concreteApplication: 'Run brokers across zones with automated failover and health checks.', implementationExamples: ['Kafka ISR'], alreadyAddressed: false, addressEvidence: '', effort: 'medium', priority: 'critical', createdAt: '2026-01-01' }],
      summary: null, loading: false, error: null,
    }));
    vi.mocked(useBuyVsBuild).mockReturnValue(mocked({
      summary: { decisions: [{ componentName: 'Event Broker', recommendation: 'adopt', rationale: 'Commodity infrastructure', alternativesConsidered: ['Build'], recommendedSolution: 'Managed Kafka', estimatedBuildCost: 'High', vendorLockInRisk: 'medium', integrationEffort: 'medium', conflictsWithUserPreference: false, conflictExplanation: '', isCoreeDifferentiator: false }] },
      loading: false, error: null,
    }));
  });

  it('builds a complete architecture document from analysis outputs', async () => {
    const { result } = renderHook(() => useArchDoc());

    await waitFor(() => expect(result.current.conversationTitle).toBe('Claims Platform'));
    await waitFor(() => expect(result.current.deploymentDiagram).toContain('Web-->API'));

    expect(result.current.hasData).toBe(true);
    expect(result.current.systemTitle).toBe('Claims Platform');
    expect(result.current.stakeholderConcerns).toEqual(expect.arrayContaining([
      expect.objectContaining({ characteristic: 'Availability' }),
    ]));
    expect(result.current.fmeaByComponent['Event Broker']).toHaveLength(1);
    expect(result.current.moduleAdlRules).toHaveLength(1);
    expect(result.current.connectorAdlRules).toHaveLength(1);
    expect(result.current.allocationAdlRules).toHaveLength(1);
    expect(result.current.fullPackageMarkdown).toContain('Claims Platform');
    expect(result.current.fullPackageMarkdown).toContain('Broker concentration');
    expect(result.current.exportFilename).toMatch(/^architecture-docs-claims-platform-/);
  });

  it('returns a useful empty state while architecture data is unavailable', () => {
    vi.mocked(useArchitecture).mockReturnValue(mocked({ architecture: null, loading: true, error: 'pending' }));

    const { result } = renderHook(() => useArchDoc());

    expect(result.current.hasData).toBe(false);
    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBe('pending');
    expect(result.current.fullPackageMarkdown).toBe('');
  });

  it('normalises legacy ADL rule fields', () => {
    const rule = { title: 'Encryption rule', justification: 'Protect data', characteristic_enforced: 'security', enforcement_level: 'mandatory', adl_id: 'legacy-1' } as never;
    expect(resolveAdlSubject(rule)).toBe('Encryption rule');
    expect(resolveAdlRationale(rule)).toBe('Protect data');
    expect(resolveAdlCategory(rule)).toBe('security');
    expect(resolveAdlEnforcement(rule)).toBe('mandatory');
    expect(resolveAdlId(rule)).toBe('legacy-1');
  });
});
