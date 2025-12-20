import { useState } from 'react';
import { generateSecret, base64ToBytes } from '../services/crypto';
import { requestChallenge, createSecret } from '../services/api';
import { solveChallenge } from '../services/pow';
import { generateShareableLinks } from '../utils/urlFragments';
import type { ShareableLinks } from '../types';

type Step = 'input' | 'processing' | 'done';

export default function CreateSecret() {
  const [step, setStep] = useState<Step>('input');
  const [message, setMessage] = useState('');
  const [unlockDate, setUnlockDate] = useState('');
  const [unlockTime, setUnlockTime] = useState('00:00');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');
  const [links, setLinks] = useState<ShareableLinks | null>(null);
  const [copied, setCopied] = useState<'edit' | 'view' | null>(null);

  // Calculate minimum date (5 minutes from now)
  const now = new Date();
  const minDate = new Date(now.getTime() + 5 * 60 * 1000);
  const minDateStr = minDate.toISOString().split('T')[0];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStep('processing');

    try {
      // Combine date and time
      const unlockAt = new Date(`${unlockDate}T${unlockTime}:00`);

      if (unlockAt <= new Date()) {
        throw new Error('Unlock date must be in the future');
      }

      // Step 1: Generate cryptographic materials
      setProgress('Encrypting your secret...');
      const secret = await generateSecret(message);

      // Step 2: Request PoW challenge
      setProgress('Requesting proof-of-work challenge...');
      const ciphertextSize = base64ToBytes(secret.encrypted.ciphertext).length;
      const challenge = await requestChallenge(secret.payloadHash, ciphertextSize);

      // Step 3: Solve PoW
      setProgress(`Solving proof-of-work (difficulty: ${challenge.difficulty})...`);
      const powProof = await solveChallenge(challenge, secret.payloadHash, (iterations) => {
        setProgress(`Solving proof-of-work... (${(iterations / 1000).toFixed(0)}k iterations)`);
      });

      // Step 4: Create secret on server
      setProgress('Storing encrypted secret...');
      await createSecret({
        ciphertext: secret.encrypted.ciphertext,
        iv: secret.encrypted.iv,
        auth_tag: secret.encrypted.authTag,
        unlock_at: unlockAt.toISOString(),
        edit_token: secret.editToken,
        decrypt_token: secret.decryptToken,
        pow_proof: powProof,
      });

      // Step 5: Generate shareable links
      const shareableLinks = generateShareableLinks(
        secret.editToken,
        secret.decryptToken,
        secret.encryptionKey
      );

      setLinks(shareableLinks);
      setStep('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setStep('input');
    }
  };

  const copyToClipboard = async (text: string, type: 'edit' | 'view') => {
    await navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  if (step === 'processing') {
    return (
      <div className="create-secret">
        <h1>Creating Your Secret</h1>
        <div className="processing">
          <div className="spinner"></div>
          <p>{progress}</p>
        </div>
      </div>
    );
  }

  if (step === 'done' && links) {
    return (
      <div className="create-secret">
        <h1>Secret Created!</h1>

        <div className="success-message">
          <p>
            Your secret has been encrypted and stored. Save these links carefully -
            you won't see them again!
          </p>
        </div>

        <div className="links-section">
          <div className="link-box">
            <h3>Edit Link (keep this private)</h3>
            <p className="link-description">
              Use this link to extend the unlock date. Only share if you want someone
              else to be able to postpone the release.
            </p>
            <div className="link-container">
              <input type="text" value={links.editLink} readOnly />
              <button
                onClick={() => copyToClipboard(links.editLink, 'edit')}
                className="copy-button"
              >
                {copied === 'edit' ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          <div className="link-box">
            <h3>View Link (share with recipient)</h3>
            <p className="link-description">
              Share this link with the person who should receive your secret.
              They can only access it after the unlock date.
            </p>
            <div className="link-container">
              <input type="text" value={links.viewLink} readOnly />
              <button
                onClick={() => copyToClipboard(links.viewLink, 'view')}
                className="copy-button"
              >
                {copied === 'view' ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
        </div>

        <div className="warning">
          <strong>Important:</strong> The encryption key is in the URL fragment
          (after #). It is never sent to our server. If you lose these links, your
          secret cannot be recovered.
        </div>
      </div>
    );
  }

  return (
    <div className="create-secret">
      <h1>Create a Time-Locked Secret</h1>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="message">Your Secret Message</label>
          <textarea
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter the secret you want to share..."
            rows={6}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="unlock-date">Unlock Date</label>
          <p className="help-text">
            Your recipient will be able to access the secret after this date.
          </p>
          <div className="date-time-inputs">
            <input
              type="date"
              id="unlock-date"
              value={unlockDate}
              onChange={(e) => setUnlockDate(e.target.value)}
              min={minDateStr}
              required
            />
            <input
              type="time"
              id="unlock-time"
              value={unlockTime}
              onChange={(e) => setUnlockTime(e.target.value)}
              required
            />
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" className="button primary" disabled={!message || !unlockDate}>
          Create Secret
        </button>
      </form>
    </div>
  );
}
