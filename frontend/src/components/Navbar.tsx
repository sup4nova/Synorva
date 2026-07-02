export default function Navbar() {
  return (
    <nav className="nav">
      <div className="shell nav-inner">
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
        <a className="nav-cta" href="#how">How it works →</a>
      </div>
    </nav>
  )
}
