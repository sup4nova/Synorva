const year = new Date().getFullYear()

const rows = [
  { label: 'About',    href: 'https://sup4nova.com/#about' },
  { label: 'Projects', href: 'https://sup4nova.com/#projects' },
  { label: 'Contact',  href: 'https://sup4nova.com/#contact' },
  { label: 'GitHub',   href: 'https://github.com/sup4nova' },
]

export default function Footer() {
  return (
    <footer className="footer">
      <div className="shell">
        <div className="footer-top">
          <div className="footer-brand-block">
            <a className="brand" href="#">
              <span className="brand-mark">
                <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3 L21 12 L12 21 L3 12 Z" stroke="var(--warm)" strokeWidth="1.6" />
                  <circle cx="12" cy="12" r="3" fill="var(--warm)" />
                </svg>
              </span>
              <span className="brand-name">synorva</span>
              <span className="brand-tag">beta</span>
            </a>
            <p className="footer-blurb">
              A research playground exploring multimodal emotion transfer
            </p>
          </div>

          <div className="footer-row">
            <h5>Links</h5>
            <ul>
              {rows.map(l => (
                <li key={l.href}>
                  <a href={l.href} target="_blank" rel="noopener noreferrer">
                    {l.label} <span className="arr">→</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="footer-legal">
            <div className="footer-legal-row">
              <span>© {year} sup4nova</span>
              <a href="https://sup4nova.com/privacy" target="_blank" rel="noopener noreferrer">
                privacy
              </a>
              <a href="https://sup4nova.com/terms" target="_blank" rel="noopener noreferrer">
                terms
              </a>
            </div>
          </div>

        </div>
      </div>
    </footer>
  )
}