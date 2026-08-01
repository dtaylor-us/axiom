interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  accent?: string;
}

/**
 * Consistent section heading used across pillar landing pages.
 */
export function SectionHeading({ title, subtitle, accent }: SectionHeadingProps) {
  return (
    <div className="section-heading">
      {accent && <div className="section-heading-accent" style={{ background: accent }} />}
      <div>
        <h2 className="section-heading-title">{title}</h2>
        {subtitle && <p className="section-heading-subtitle">{subtitle}</p>}
      </div>
    </div>
  );
}
