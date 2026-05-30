interface Pillar {
  id: string;
  name: string;
  description: string;
  path: string;
  enabled: boolean;
}

const PILLARS: Pillar[] = [
  {
    id: 'archon',
    name: 'Archon',
    description: 'Architecture Reasoning',
    path: '/',
    enabled: true,
  },
  {
    id: 'specweaver',
    name: 'SpecWeaver',
    description: 'Requirements Intelligence',
    path: '/specweaver',
    enabled: false,
  },
  {
    id: 'scout',
    name: 'Scout',
    description: 'Repository Intelligence',
    path: '/scout',
    enabled: false,
  },
  {
    id: 'forge',
    name: 'Forge',
    description: 'Prototype Generation',
    path: '/forge',
    enabled: false,
  },
];

function PillarIcon({ enabled }: { enabled: boolean }) {
  const iconPath = enabled
    ? 'M4 6h16M4 12h10M4 18h14'
    : 'M10 13a3 3 0 116 0v2h1a1 1 0 011 1v4H8v-4a1 1 0 011-1h1v-2zm1-3V9a2 2 0 114 0v1';

  return (
    <svg
      className="w-4 h-4 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={iconPath} />
    </svg>
  );
}

function PillarItem({ pillar, mobile }: { pillar: Pillar; mobile: boolean }) {
  const isActive = pillar.id === 'archon';

  return (
    <button
      type="button"
      disabled={!pillar.enabled}
      aria-current={isActive ? 'page' : undefined}
      title={pillar.enabled ? pillar.description : 'Coming soon'}
      className={`pillar-nav-item flex items-start justify-between gap-3 text-left ${
        isActive
          ? 'pillar-nav-item--active text-white'
          : 'text-gray-300 hover:bg-sidebar-hover hover:text-gray-100'
      } ${pillar.enabled ? '' : 'pillar-nav-item--disabled'} ${mobile ? 'pillar-nav-item--mobile' : ''}`}
      data-testid={`pillar-${pillar.id}`}
      data-path={pillar.path}
    >
      <span className="flex min-w-0 items-start gap-2">
        <span className={isActive ? 'text-white' : 'text-gray-400'}>
          <PillarIcon enabled={pillar.enabled} />
        </span>
        <span className="min-w-0">
          <span className={`block truncate font-medium ${mobile ? 'text-[16px]' : 'text-[13px]'}`}>{pillar.name}</span>
          <span className={`block ${mobile ? 'text-[13px] text-gray-400' : 'truncate text-[11px] text-gray-500'}`}>{pillar.description}</span>
        </span>
      </span>
      {!pillar.enabled && (
        <span className="pillar-nav-item__coming-soon shrink-0">Coming soon</span>
      )}
    </button>
  );
}

/**
 * Platform pillar switcher for the Axiom shell.
 */
export function PillarNav({ mobile = false }: { mobile?: boolean }) {
  return (
    <nav
      className={`pillar-nav ${mobile ? 'pillar-nav--mobile' : ''}`}
      aria-label="Platform pillars"
      data-testid="pillar-nav"
    >
      <div className="px-3 pb-2 pt-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">
          Platform pillars
        </p>
      </div>
      <div className="flex flex-col gap-1 px-2 pb-2">
        {PILLARS.map((pillar) => (
          <PillarItem key={pillar.id} pillar={pillar} mobile={mobile} />
        ))}
      </div>
    </nav>
  );
}