import { useState, useEffect } from 'react'
import { generateSecret, base64ToBytes } from '../services/crypto'
import { requestChallenge, createSecret } from '../services/api'
import { solveChallenge } from '../services/pow'
import { generateShareableLinks } from '../utils/urlFragments'
import {
  applyDateOffset,
  validateExpiryDate,
  formatDateForDisplay,
  type DatePreset,
} from '../utils/dates'
import type { ShareableLinks } from '../types'

type Step = 'input' | 'processing' | 'done'

export default function Home() {
  const [step, setStep] = useState<Step>('input')
  const [message, setMessage] = useState('')
  const [datePreset, setDatePreset] = useState<DatePreset>('1m')
  const [customDate, setCustomDate] = useState('')
  const [customTime, setCustomTime] = useState('00:00')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<string>('')
  const [links, setLinks] = useState<ShareableLinks | null>(null)
  const [copied, setCopied] = useState<'edit' | 'view' | null>(null)

  // Expiry date state
  const [expiryPreset, setExpiryPreset] = useState<ExpiryPreset>('1y')
  const [customExpiryDate, setCustomExpiryDate] = useState('')
  const [customExpiryTime, setCustomExpiryTime] = useState('00:00')
  const [createdUnlockAt, setCreatedUnlockAt] = useState<Date | null>(null)
  const [createdExpiresAt, setCreatedExpiresAt] = useState<Date | null>(null)

  // Tick state to trigger re-renders for live time updates
  const [, setTick] = useState(0)

  useEffect(() => {
    // Only tick when on input step and using non-custom presets (they depend on current time)
    if (step === 'input' && (datePreset !== 'custom' || expiryPreset !== 'custom')) {
      const interval = setInterval(() => setTick((t) => t + 1), 1000)
      return () => clearInterval(interval)
    }
  }, [step, datePreset, expiryPreset])

  // Calculate minimum date (5 minutes from now)
  const now = new Date()
  const minDate = new Date(now.getTime() + 5 * 60 * 1000)
  const minDateStr = minDate.toISOString().split('T')[0]

  // Calculate unlock date from preset
  const getUnlockDate = (): Date | null => {
    return applyDateOffset(new Date(), datePreset, { date: customDate, time: customTime })
  }

  // Calculate expiry date from preset (relative to unlock date)
  const getExpiryDate = (unlockDate: Date): Date | null => {
    return applyDateOffset(unlockDate, expiryPreset, {
      date: customExpiryDate,
      time: customExpiryTime,
    })
  }

  // Check if form is valid
  const isValid =
    message.trim() &&
    (datePreset !== 'custom' || (customDate && customTime)) &&
    (expiryPreset !== 'custom' || (customExpiryDate && customExpiryTime))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const unlockAt = getUnlockDate()
    if (!unlockAt) {
      setError('Please select an unlock date')
      return
    }

    if (unlockAt <= new Date()) {
      setError('Unlock date must be in the future')
      return
    }

    // Calculate expiry date (default: 1 year after unlock)
    const expiresAt = getExpiryDate(unlockAt)
    if (!expiresAt) {
      setError('Please select an expiry date')
      return
    }

    // Validate expiry constraints
    const expiryError = validateExpiryDate(unlockAt, expiresAt)
    if (expiryError) {
      setError(expiryError)
      return
    }

    setStep('processing')

    try {
      // Step 1: Generate cryptographic materials
      setProgress('Encrypting your secret...')
      const secret = await generateSecret(message)

      // Step 2: Request PoW challenge
      setProgress('Requesting proof-of-work challenge...')
      const ciphertextSize = base64ToBytes(secret.encrypted.ciphertext).length
      const challenge = await requestChallenge(secret.payloadHash, ciphertextSize)

      // Step 3: Solve PoW
      setProgress(`Solving proof-of-work (difficulty: ${challenge.difficulty})...`)
      const powProof = await solveChallenge(challenge, secret.payloadHash, (iterations) => {
        setProgress(`Solving proof-of-work... (${(iterations / 1000).toFixed(0)}k iterations)`)
      })

      // Step 4: Create secret on server
      setProgress('Storing encrypted secret...')
      await createSecret({
        ciphertext: secret.encrypted.ciphertext,
        iv: secret.encrypted.iv,
        auth_tag: secret.encrypted.authTag,
        unlock_at: unlockAt.toISOString(),
        expires_at: expiresAt.toISOString(),
        edit_token: secret.editToken,
        decrypt_token: secret.decryptToken,
        pow_proof: powProof,
      })

      // Step 5: Generate shareable links
      const shareableLinks = generateShareableLinks(
        secret.editToken,
        secret.decryptToken,
        secret.encryptionKey,
      )

      setLinks(shareableLinks)
      setCreatedUnlockAt(unlockAt)
      setCreatedExpiresAt(expiresAt)
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      setStep('input')
    }
  }

  const copyToClipboard = async (text: string, type: 'edit' | 'view') => {
    await navigator.clipboard.writeText(text)
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  const resetForm = () => {
    setStep('input')
    setMessage('')
    setDatePreset('1m')
    setCustomDate('')
    setCustomTime('00:00')
    setExpiryPreset('1y')
    setCustomExpiryDate('')
    setCustomExpiryTime('00:00')
    setCreatedUnlockAt(null)
    setCreatedExpiresAt(null)
    setLinks(null)
    setError(null)
  }

  if (step === 'processing') {
    return (
      <div className="home">
        <div className="hero-form">
          <h1>Creating Your Secret</h1>
          <div className="processing">
            <div className="spinner"></div>
            <p>{progress}</p>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'done' && links) {
    return (
      <div className="home">
        <div className="hero-form success-state">
          <h1>Secret Created!</h1>

          <div className="success-message">
            <p>
              Your secret has been encrypted and stored. Save these links carefully - you won't see
              them again!
            </p>
          </div>

          {createdUnlockAt && createdExpiresAt && (
            <div className="dates-info">
              <p>
                <strong>Unlocks:</strong>{' '}
                {createdUnlockAt.toLocaleDateString(undefined, {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}{' '}
                at{' '}
                {createdUnlockAt.toLocaleTimeString(undefined, {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
              <p>
                <strong>Expires:</strong>{' '}
                {createdExpiresAt.toLocaleDateString(undefined, {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}{' '}
                at{' '}
                {createdExpiresAt.toLocaleTimeString(undefined, {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          )}

          <div className="links-section">
            <div className="link-box">
              <h3>Edit Link (keep this private)</h3>
              <p className="link-description">Use this link to extend the unlock date.</p>
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
              <p className="link-description">Share this with who should receive your secret.</p>
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
            <strong>Important:</strong> The encryption key is in the URL fragment. If you lose these
            links, your secret cannot be recovered.
          </div>

          <button onClick={resetForm} className="button secondary">
            Create Another Secret
          </button>
        </div>
      </div>
    )
  }

  const unlockDateDisplay = formatDateForDisplay(getUnlockDate())

  return (
    <div className="home">
      <div className="hero-form">
        <p className="hero-title">In The Event Of My Death</p>
        <form onSubmit={handleSubmit} className="inline-form">
          <div className="message-input-container">
            <textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Enter your secret message..."
              rows={4}
              required
              autoFocus
            />
          </div>

          <div className="date-presets">
            <span className="presets-label">Unlock in:</span>
            <button
              type="button"
              className={datePreset === '1w' ? 'active' : ''}
              onClick={() => setDatePreset('1w')}
            >
              1 Week
            </button>
            <button
              type="button"
              className={datePreset === '1m' ? 'active' : ''}
              onClick={() => setDatePreset('1m')}
            >
              1 Month
            </button>
            <button
              type="button"
              className={datePreset === '1y' ? 'active' : ''}
              onClick={() => setDatePreset('1y')}
            >
              1 Year
            </button>
            <button
              type="button"
              className={datePreset === 'custom' ? 'active' : ''}
              onClick={() => setDatePreset('custom')}
            >
              Custom
            </button>
          </div>

          {unlockDateDisplay && (
            <p className="unlock-preview">
              Unlocks: {unlockDateDisplay.date} at {unlockDateDisplay.time}
            </p>
          )}

          {datePreset === 'custom' && (
            <div className="custom-date-row">
              <div className="form-group">
                <label htmlFor="custom-date">Date</label>
                <input
                  type="date"
                  id="custom-date"
                  value={customDate}
                  onChange={(e) => setCustomDate(e.target.value)}
                  min={minDateStr}
                />
              </div>
              <div className="form-group">
                <label htmlFor="custom-time">Time</label>
                <input
                  type="time"
                  id="custom-time"
                  value={customTime}
                  onChange={(e) => setCustomTime(e.target.value)}
                />
              </div>
            </div>
          )}

          {datePreset === 'custom' && !customDate && (
            <p className="field-hint">Select a date to continue</p>
          )}

          <div className="date-presets">
            <span className="presets-label">Expire in:</span>
            <button
              type="button"
              className={expiryPreset === '1w' ? 'active' : ''}
              onClick={() => setExpiryPreset('1w')}
            >
              +1 Week
            </button>
            <button
              type="button"
              className={expiryPreset === '1m' ? 'active' : ''}
              onClick={() => setExpiryPreset('1m')}
            >
              +1 Month
            </button>
            <button
              type="button"
              className={expiryPreset === '1y' ? 'active' : ''}
              onClick={() => setExpiryPreset('1y')}
            >
              +1 Year
            </button>
            <button
              type="button"
              className={expiryPreset === 'custom' ? 'active' : ''}
              onClick={() => setExpiryPreset('custom')}
            >
              Custom
            </button>
          </div>

          {getUnlockDate() && getExpiryDate(getUnlockDate()!) && (
            <p className="unlock-preview">
              Expires: {formatDateForDisplay(getExpiryDate(getUnlockDate()!))?.date} at{' '}
              {formatDateForDisplay(getExpiryDate(getUnlockDate()!))?.time}
            </p>
          )}

          {expiryPreset === 'custom' && (
            <div className="custom-date-row">
              <div className="form-group">
                <label htmlFor="custom-expiry-date">Date</label>
                <input
                  type="date"
                  id="custom-expiry-date"
                  value={customExpiryDate}
                  onChange={(e) => setCustomExpiryDate(e.target.value)}
                  min={getUnlockDate()?.toISOString().split('T')[0] || minDateStr}
                />
              </div>
              <div className="form-group">
                <label htmlFor="custom-expiry-time">Time</label>
                <input
                  type="time"
                  id="custom-expiry-time"
                  value={customExpiryTime}
                  onChange={(e) => setCustomExpiryTime(e.target.value)}
                />
              </div>
            </div>
          )}

          {expiryPreset === 'custom' && !customExpiryDate && (
            <p className="field-hint">Select an expiry date to continue</p>
          )}

          <button
            type="submit"
            className="button primary full-width send-button"
            disabled={!isValid}
          >
            Send
          </button>

          <p className="security-note">Encrypted in your browser. We never see your plaintext.</p>

          {error && <div className="error-message">{error}</div>}
        </form>
      </div>
    </div>
  )
}
