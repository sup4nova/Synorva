const year = new Date().getFullYear()

const cols = [
  {
    title: 'Product',
    links: ['Try the beta', 'Examples', 'Genre presets', 'Changelog', 'Roadmap'],
  },
  {
    title: 'Developers',
    links: ['API reference', 'Quickstart', 'Model card', 'Rate limits', 'Status page'],
  },
  {
    title: 'Studio',
    links: ['Projects', 'About', 'Contact', 'GitHub'],
  },
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
            <h3 className="footer-tagline">
              Built at the edge of <span className="it">cyber, sound &amp; AI.</span>
            </h3>
            <p className="footer-blurb">
              A research playground exploring multimodal emotion transfer.
              Part of the sup4nova portfolio.
            </p>
            <a className="footer-portfolio" href="https://github.com/sup4nova" target="_blank" rel="noopener noreferrer">
              <span className="footer-portfolio-mark">S4</span>
              <span className="footer-portfolio-text">
                <small>parent studio</small>
                <strong>sup4nova →</strong>
              </span>
            </a>
          </div>

          {cols.map(col => (
            <div className="footer-col" key={col.title}>
              <h5>{col.title}</h5>
              <ul>
                {col.links.map(l => (
                  <li key={l}>
                    <a href="#">{l} <span className="arr">→</span></a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="footer-bottom">
          <div className="footer-wordmark">
            synorva<span className="it">.</span>
          </div>
          <div className="footer-legal">
            <div className="footer-status">
              <span className="footer-status-dot" />
              all systems operational
            </div>
            <div className="footer-legal-row">
              <span>© {year} sup4nova</span>
              <a href="#">privacy</a>
              <a href="#">terms</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
