import type { ReactNode } from 'react';

export type PillarId = 'axiom' | 'archon' | 'specweaver' | 'lens' | 'memoria';

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
    <rect x="4" y="5" width="16" height="4" rx="1.3" />
    <rect x="4" y="15" width="7" height="4" rx="1.3" />
    <rect x="13" y="15" width="7" height="4" rx="1.3" />
    <path d="M12 9v3m-4.5 0h9M7.5 12v3m9-3v3" />
  </>
);

const SpecWeaverIcon = (
  <>
    <path d="M7 3h7l5 5v13H7a2 2 0 01-2-2V5a2 2 0 012-2z" />
    <path d="M14 3v5h5" />
    <path d="M9 11h6M9 14h6M9 17h5" />
  </>
);

const LensIcon = (
  <>
    <circle cx="10.5" cy="10.5" r="5.5" />
    <path d="M14.5 14.5 20 20" />
  </>
);

const MemoriaIcon = (
  <>
    <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H19v15H7.5A2.5 2.5 0 0 0 5 20.5z" />
    <path d="M5 5.5v15M9 7h6M9 11h6M9 15h4" />
  </>
);

const ICONS: Record<PillarId, ReactNode> = {
  axiom: AxiomIcon,
  archon: ArchonIcon,
  specweaver: SpecWeaverIcon,
  lens: LensIcon,
  memoria: MemoriaIcon,
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
