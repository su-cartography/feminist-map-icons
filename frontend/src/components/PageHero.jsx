export default function PageHero({
  eyebrow,
  title,
  lead,
  children,
  align = 'left',
  compact = false,
}) {
  return (
    <header
      className={[
        'page-banner',
        align === 'center' ? 'is-center' : '',
        compact ? 'is-compact' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="page-banner__orb page-banner__orb--a" aria-hidden="true" />
      <div className="page-banner__orb page-banner__orb--b" aria-hidden="true" />
      <div className="wrap page-banner__inner">
        {eyebrow ? <p className="page-banner__eyebrow">{eyebrow}</p> : null}
        {title ? <h1>{title}</h1> : null}
        {lead ? <p className="page-banner__lead">{lead}</p> : null}
        {children}
      </div>
    </header>
  )
}
