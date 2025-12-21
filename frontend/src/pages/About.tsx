export default function About() {
  return (
    <div className="about">
      <h1>About</h1>
      <p className="subtitle">How we keep your secrets safe.</p>

      <section id="how-it-works" className="info-section">
        <h2>How It Works</h2>
        <ol>
          <li>Write your secret message</li>
          <li>Choose when it should unlock</li>
          <li>Share the view link with your recipient</li>
          <li>Keep the edit link to extend the date if needed</li>
        </ol>
      </section>

      <section id="security-privacy" className="info-section">
        <h2>Security &amp; Privacy</h2>
        <ul>
          <li>
            <strong>Zero Knowledge:</strong> End-to-end encrypted. We never see your content or
            keys.
          </li>
          <li>
            <strong>Time-Locked:</strong> Recipients can only access after the unlock date.
          </li>
          <li>
            <strong>One-Time Access:</strong> Retrieved once, then permanently deleted.
          </li>
          <li>
            <strong>No Accounts:</strong> No sign-up. Just create and share.
          </li>
        </ul>
      </section>

      <section id="faq" className="info-section">
        <h2>FAQ</h2>
        <div className="faq-item">
          <h3>Can you read my messages?</h3>
          <p>
            No. Your messages are encrypted in your browser before they reach our servers. The
            encryption key is stored only in the URL fragment (the part after the #), which is never
            sent to the server. This means we have no way to decrypt your data.
          </p>
        </div>
        <div className="faq-item">
          <h3>What happens if I lose the link?</h3>
          <p>
            Unfortunately, the link cannot be recovered. Since the encryption key is stored only in
            the URL, losing the link means the secret is permanently inaccessible. We recommend
            saving both the view link and edit link in a secure location.
          </p>
        </div>
        <div className="faq-item">
          <h3>What if I don&apos;t retrieve my secret before it expires?</h3>
          <p>
            Secrets expire after 90 days from creation. If a secret is not retrieved before
            expiration, it is permanently deleted from our servers and cannot be recovered. Use the
            edit link to extend the unlock date if needed.
          </p>
        </div>
      </section>

      <section id="encryption" className="info-section">
        <h2>Technical Details</h2>
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
