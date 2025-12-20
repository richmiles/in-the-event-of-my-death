export default function About() {
  return (
    <div className="about">
      <h1>About</h1>
      <p className="subtitle">How we keep your secrets safe.</p>

      <div className="features-section">
        <div className="features">
          <div className="feature">
            <div className="feature-icon" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <circle cx="12" cy="16" r="1" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h3>Zero Knowledge</h3>
            <p>End-to-end encrypted. We never see your content or keys.</p>
          </div>

          <div className="feature">
            <div className="feature-icon" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h3>Time-Locked</h3>
            <p>Recipients can only access after the unlock date.</p>
          </div>

          <div className="feature">
            <div className="feature-icon" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            </div>
            <h3>One-Time Access</h3>
            <p>Retrieved once, then permanently deleted.</p>
          </div>

          <div className="feature">
            <div className="feature-icon" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="8.5" cy="7" r="4" />
                <line x1="20" y1="8" x2="20" y2="14" />
                <line x1="23" y1="11" x2="17" y2="11" />
              </svg>
            </div>
            <h3>No Accounts</h3>
            <p>No sign-up. Just create and share.</p>
          </div>
        </div>
      </div>

      <section id="how-it-works" className="info-section">
        <h2>How It Works</h2>
        <ol>
          <li>Write your secret message</li>
          <li>Choose when it should unlock</li>
          <li>Share the view link with your recipient</li>
          <li>Keep the edit link to extend the date if needed</li>
        </ol>
      </section>

      <section id="encryption" className="info-section">
        <h2>Encryption Details</h2>
        <p>
          Your secrets are encrypted using AES-256-GCM in your browser before being sent to our
          servers. The encryption key is stored only in the URL fragment, which is never sent to the
          server. This means we can never decrypt your data—only someone with the complete link can
          access it.
        </p>
      </section>
    </div>
  )
}
