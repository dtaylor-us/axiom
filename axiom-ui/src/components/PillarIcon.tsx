import type { ReactNode } from 'react';

export type PillarId = 'axiom' | 'archon' | 'specweaver' | 'scout' | 'forge';

interface PillarIconProps {
  pillar: PillarId;
  size?: number;
  className?: string;
}

const AxiomIcon = (
  <>
    <path d="M12 3l8 4v10l-8 4-8-4V7l8-4z" />
    <path d="M12 7l4 2v6l-4 2-4-2V9l4-2z" />
  </>
);

const ArchonIcon = (
  <>
    <rect x="3" y="4" width="6" height="4" rx="1" />
    <rect x="15" y="4" width="6" height="4" rx="1" />
    <rect x="9" y="16" width="6" height="4" rx="1" />
    <path d="M6 8v3m12-3v3m-6-2v5m-6 0h12" />
  </>
);

const SpecWeaverIcon = (
  <>
    <path d="M7 3h7l5 5v13H7a2 2 0 01-2-2V5a2 2 0 012-2z" />
    <path d="M14 3v5h5" />
    <path d="M9 11h6M9 14h6M9 17h5" />
  </>
);

const ScoutIcon = (
  <>
    <circle cx="10" cy="10" r="5" />
    <path d="M13.8 13.8L20 20" />
    <circle cx="9" cy="9" r="1.2" />
    <path d="M9 7v4M7 9h4" />
  </>
);

const ForgeIcon = (
  <>
    <path d="M4 6l3-3 2 2-3 3 10 10-2 2L4 10 2 8l2-2z" />
    <path d="M14 3l2-2m0 0l2 2m-2-2v4" />
  </>
);

const ICONS: Record<PillarId, ReactNode> = {
  axiom: AxiomIcon,
  archon: ArchonIcon,
  specweaver: SpecWeaverIcon,
  scout: ScoutIcon,
  forge: ForgeIcon,
};

/**
 * Renders the icon for a pillar across navigation, headers, and badges.
 */
export function PillarIcon({ pillar, size = 20, className = '' }: PillarIconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      data-testid={`pillar-icon-${pillar}`}
    >
      {ICONS[pillar]}
    </svg>
  );
}
