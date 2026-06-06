import type { CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { PillarIcon, type PillarId } from './PillarIcon';

interface Pillar {
  id: PillarId;
  name: string;
  description: string;
  path: string;
  enabled: boolean;
  color: string;
}

const PILLARS: Pillar[] = [
  {
    id: 'specweaver',
    name: 'SpecWeaver',
    description: 'Requirements Intelligence',
    path: '/specweaver',
    enabled: true,
    color: 'var(--color-pillar-specweaver)',
  },
  {
    id: 'archon',
    name: 'Archon',
    description: 'Architecture Reasoning',
    path: '/archon',
    enabled: true,
    color: 'var(--color-pillar-archon)',
  },
  {
    id: 'scout',
    name: 'Scout',
    description: 'Repository Intelligence',
    path: '/scout',
    enabled: true,
    color: 'var(--color-pillar-scout)',
  },
  {
    id: 'forge',
    name: 'Forge',
    description: 'Prototype Generation',
    path: '/forge',
    enabled: true,
    color: 'var(--color-pillar-forge)',
  },
];

function isPillarActive(pillar: Pillar, pathname: string): boolean {
  const isActive = pillar.id === 'archon'
    ? pathname.startsWith('/archon') || pathname.startsWith('/conversations/')
    : pathname.startsWith(pillar.path);
  return isActive;
}

function PillarItem({ pillar, mobile }: { pillar: Pillar; mobile: boolean }) {
  const { pathname } = useLocation();
  const isActive = isPillarActive(pillar, pathname);
  const pillarStyle = {
    '--pillar-color': pillar.color,
  } as CSSProperties;
  const className = `pillar-nav-item flex items-start justify-between gap-3 text-left ${
    isActive ? 'pillar-nav-item--active text-gray-200' : 'text-gray-300 hover:bg-sidebar-hover hover:text-gray-100'
  } ${mobile ? 'pillar-nav-item--mobile' : ''}`;

  const content = (
    <>
      <span className="flex min-w-0 items-start gap-2">
        <span className={`pillar-nav-icon ${isActive ? '' : 'text-gray-400'}`}>
          <PillarIcon pillar={pillar.id} size={18} className="shrink-0" />
        </span>
        <span className="min-w-0">
          <span className={`pillar-nav-name block truncate font-medium ${mobile ? 'text-[16px]' : 'text-[13px]'}`}>{pillar.name}</span>
          <span className={`block ${mobile ? 'text-[13px] text-gray-400' : 'truncate text-[11px] text-gray-500'}`}>{pillar.description}</span>
        </span>
      </span>
    </>
  );

  return (
    <Link
      to={pillar.path}
      aria-current={isActive ? 'page' : undefined}
      title={pillar.description}
      className={className}
      style={pillarStyle}
      data-testid={`pillar-${pillar.id}`}
      data-path={pillar.path}
    >
      {content}
    </Link>
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
