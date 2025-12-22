import { useEffect } from 'react'

export default function TermsOfService() {
  useEffect(() => {
    document.title = 'Terms of Service | In The Event Of My Death'
  }, [])

  return (
    <div className="about">
      <h1>Terms of Service</h1>
      <p className="subtitle">Please read these terms carefully before using our service.</p>

      <section className="info-section">
        <h2>Beta Service Disclaimer</h2>
        <p>
          <strong>This service is currently in beta.</strong> This service is provided on an
          &quot;as-is&quot; and &quot;as-available&quot; basis. We make no guarantees about the
          service&apos;s availability, reliability, or suitability for any particular purpose.
        </p>
        <p>
          While we strive to provide a secure and reliable service, we cannot guarantee that the
          service will be uninterrupted, timely, secure, or error-free. Use this service at your own
          risk.
        </p>
      </section>

      <section className="info-section">
        <h2>Acceptance of Terms</h2>
        <p>
          By accessing and using this service, you accept and agree to be bound by these Terms of
          Service. If you do not agree to these terms, please do not use the service.
        </p>
      </section>

      <section className="info-section">
        <h2>Acceptable Use</h2>
        <p>You agree to use this service only for lawful purposes. You must not:</p>
        <ul>
          <li>
            Upload, store, or share any content that is illegal, harmful, or infringes on the rights
            of others
          </li>
          <li>Use the service to store or distribute malware, viruses, or other malicious code</li>
          <li>Attempt to circumvent security measures or abuse proof-of-work challenges</li>
          <li>Use the service to harass, threaten, or harm others</li>
          <li>Violate any applicable laws or regulations</li>
          <li>
            Store content that violates intellectual property rights, including copyrighted material
            you do not own
          </li>
          <li>Use automated systems to create secrets or abuse the service in any way</li>
        </ul>
        <p>
          We reserve the right to remove any content that violates these terms or is otherwise
          objectionable, and to terminate access to the service for users who violate these terms.
        </p>
      </section>

      <section className="info-section">
        <h2>Service Availability</h2>
        <p>
          We reserve the right to modify, suspend, or discontinue the service (or any part of it) at
          any time, with or without notice. We may do this for any reason, including but not limited
          to:
        </p>
        <ul>
          <li>Maintenance and updates</li>
          <li>Security concerns</li>
          <li>Legal or regulatory requirements</li>
          <li>Business reasons</li>
        </ul>
        <p>
          We are not liable for any loss or damage that may result from service interruptions or
          termination.
        </p>
      </section>

      <section className="info-section">
        <h2>No Warranty</h2>
        <p>
          THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESS OR
          IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
          PARTICULAR PURPOSE, OR NON-INFRINGEMENT.
        </p>
        <p>We do not guarantee that:</p>
        <ul>
          <li>The service will meet your specific requirements</li>
          <li>The service will be uninterrupted, timely, secure, or error-free</li>
          <li>Secrets will be delivered at the exact time specified</li>
          <li>The service will be free from bugs or security vulnerabilities</li>
        </ul>
      </section>

      <section className="info-section">
        <h2>Limitation of Liability</h2>
        <p>
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL WE BE LIABLE FOR ANY INDIRECT,
          INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR
          REVENUES, WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE, GOODWILL, OR
          OTHER INTANGIBLE LOSSES RESULTING FROM:
        </p>
        <ul>
          <li>Your use or inability to use the service</li>
          <li>
            Any unauthorized access to or use of our servers and/or any personal information stored
            therein
          </li>
          <li>Any interruption or cessation of transmission to or from the service</li>
          <li>
            Any bugs, viruses, or other harmful code that may be transmitted through the service
          </li>
          <li>
            Any errors or omissions in any content or for any loss or damage incurred as a result of
            the use of any content posted, emailed, transmitted, or otherwise made available through
            the service
          </li>
          <li>The deletion, corruption, or failure to store any secrets or other data</li>
        </ul>
      </section>

      <section className="info-section">
        <h2>User Responsibility</h2>
        <p>You are solely responsible for:</p>
        <ul>
          <li>The content of any secrets you create</li>
          <li>Keeping your view and edit links secure and private</li>
          <li>Ensuring your use of the service complies with all applicable laws</li>
          <li>Any consequences of sharing or losing access to your links</li>
          <li>Setting appropriate unlock and expiry dates for your secrets</li>
        </ul>
        <p>
          Remember: If you lose your links, we cannot recover your secrets due to our zero-knowledge
          architecture.
        </p>
      </section>

      <section className="info-section">
        <h2>Termination</h2>
        <p>
          We reserve the right to terminate or suspend your access to the service immediately,
          without prior notice or liability, for any reason whatsoever, including without limitation
          if you breach these Terms of Service.
        </p>
      </section>

      <section className="info-section">
        <h2>Indemnification</h2>
        <p>
          You agree to indemnify and hold harmless the operators of this service, its contributors,
          and affiliates from any claims, damages, losses, liabilities, and expenses (including
          legal fees) arising from your use of the service or violation of these terms.
        </p>
      </section>

      <section className="info-section">
        <h2>Changes to Terms</h2>
        <p>
          We reserve the right to modify or replace these Terms of Service at any time. If we make
          material changes, we will provide notice through the service. Your continued use of the
          service after such modifications constitutes acceptance of the updated terms.
        </p>
      </section>

      <section className="info-section">
        <h2>Governing Law</h2>
        <p>
          These Terms shall be governed by and construed in accordance with applicable laws, without
          regard to conflict of law provisions. Any disputes arising from these terms or your use of
          the service shall be resolved in the appropriate courts.
        </p>
      </section>

      <section className="info-section">
        <h2>Contact</h2>
        <p>
          If you have any questions about these Terms of Service, please contact us through our
          GitHub repository:{' '}
          <a
            href="https://github.com/richmiles/in-the-event-of-my-death"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/richmiles/in-the-event-of-my-death
          </a>
        </p>
      </section>

      <section className="info-section">
        <p>
          <strong>Last updated:</strong> December 22, 2025
        </p>
      </section>
    </div>
  )
}
