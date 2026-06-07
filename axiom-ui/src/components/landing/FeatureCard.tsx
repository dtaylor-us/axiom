import type { ReactNode } from 'react';

interface FeatureCardProps {
  icon: ReactNode;
  iconBg: string;
  title: string;
  description: string;
  highlight?: string;
}

/**
 * Reusable landing-page card for pillar capabilities and outputs.
 */
export function FeatureCard({ icon, iconBg, title, description, highlight }: FeatureCardProps) {
  return (
    <div className="feature-card">
      <div className="feature-card-icon" style={{ background: iconBg }}>
        {icon}
      </div>
      <h3 className="feature-card-title">{title}</h3>
      <p className="feature-card-desc">{description}</p>
      {highlight && <p className="feature-card-highlight">{highlight}</p>}
    </div>
  );
}
