import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createProject, createSessionLink, getProjectSummary, listAdrs, listMemoryEntries, listProjects, removeSessionLink } from '../api/memoria';

describe('memoria API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.setItem('archon.auth', JSON.stringify({ username: 'architect@example.com' }));
  });

  afterEach(() => window.localStorage.removeItem('archon.auth'));

  it('builds authenticated project, memory, ADR, and session-link requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    } as unknown as Response);

    await listProjects('opaque-token');
    await createProject('opaque-token', 'Claims', 'Claims memory');
    await getProjectSummary('opaque-token', 'project-1');
    await listMemoryEntries('opaque-token', 'project-1', { status: 'ACTIVE', tag: 'claims', q: 'broker' });
    await listAdrs('opaque-token', 'project-1', { status: 'ACCEPTED', q: 'Kafka' });
    await createSessionLink('opaque-token', 'project-1', 'ARCHON', 'session-1');

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('status=ACTIVE'), expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('status=ACCEPTED'), expect.any(Object));
    expect(fetchMock).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
      headers: expect.objectContaining({ 'X-Axiom-User-Id': 'architect@example.com' }),
    }));
  });

  it('supports empty DELETE responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 204 } as unknown as Response);
    await expect(removeSessionLink('jwt', 'project-1', 'link-1')).resolves.toBeUndefined();
  });
});
