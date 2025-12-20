import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="home">
      <h1>In The Event Of My Death</h1>
      <p className="tagline">
        Create time-locked secrets that can only be accessed after a specific date.
      </p>

      <div className="features">
        <div className="feature">
          <h3>Zero Knowledge</h3>
          <p>
            Your secrets are encrypted in your browser. We never see the plaintext
            or the encryption keys.
          </p>
        </div>

        <div className="feature">
          <h3>Time-Locked</h3>
          <p>
            Set an unlock date. Recipients can only access your secret after that
            date passes.
          </p>
        </div>

        <div className="feature">
          <h3>One-Time Access</h3>
          <p>
            Each secret can only be retrieved once. After that, it's permanently
            deleted.
          </p>
        </div>

        <div className="feature">
          <h3>No Accounts</h3>
          <p>
            No sign-up required. Just create your secret and share the link.
          </p>
        </div>
      </div>

      <div className="cta">
        <Link to="/create" className="button primary">
          Create a Secret
        </Link>
      </div>

      <div className="how-it-works">
        <h2>How It Works</h2>
        <ol>
          <li>
            <strong>Write your secret</strong> and choose an unlock date.
          </li>
          <li>
            <strong>Get two links:</strong>
            <ul>
              <li>An <em>edit link</em> for you to extend the unlock date</li>
              <li>A <em>view link</em> to share with your recipient</li>
            </ul>
          </li>
          <li>
            <strong>Your recipient visits the view link</strong> after the unlock date
            to read your secret.
          </li>
        </ol>
      </div>
    </div>
  );
}
