import { PillarIcon, type PillarId } from './PillarIcon';

interface PillarBadgeProps {
  pillar: PillarId;
  size?: 'sm' | 'md';
  showLabel?: boolean;
}

const PILLAR_LABELS: Record<PillarId, string> = {
  axiom: 'Axiom',
  archon: 'Archon',
  specweaver: 'SpecWeaver',
  scout: 'Scout',
  forge: 'Forge',
};

/**
 * Coloured pill badge showing the pillar icon and optional name.
 */
export function PillarBadge({ pillar, size = 'md', showLabel = true }: PillarBadgeProps) {
  return (
    <span className={`pillar-badge pillar-badge--${size} pillar-badge--${pillar}`} data-testid={`pillar-badge-${pillar}`}>
      <PillarIcon pillar={pillar} size={size === 'md' ? 14 : 12} />
      {showLabel && <span>{PILLAR_LABELS[pillar]}</span>}
    </span>
  );
}
