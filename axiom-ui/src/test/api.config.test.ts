import { afterEach, describe, expect, it, vi } from 'vitest';

async function loadConfig() {
  return import('../api/config');
}

describe('api config', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('usesDirectRoutingWhenGatewayIsDisabled', async () => {
    vi.stubEnv('VITE_USE_GATEWAY', 'false');

    const { ARCHON_API_BASE, AUTH_BASE, CHAT_BASE, SESSIONS_BASE } = await loadConfig();

    expect(ARCHON_API_BASE).toBe('/api/v1');
    expect(AUTH_BASE).toBe('/api/v1/auth');
    expect(CHAT_BASE).toBe('/api/v1/chat');
    expect(SESSIONS_BASE).toBe('/api/v1/sessions');
  });

  it('routesThroughTheGatewayWhenEnabled', async () => {
    vi.stubEnv('VITE_USE_GATEWAY', 'true');

    const { ARCHON_API_BASE, CHAT_BASE, WORKSHOP_BASE } = await loadConfig();

    expect(ARCHON_API_BASE).toBe('/api/v1/archon');
    expect(CHAT_BASE).toBe('/api/v1/archon/chat');
    expect(WORKSHOP_BASE).toBe('/api/v1/archon/workshop');
  });
});