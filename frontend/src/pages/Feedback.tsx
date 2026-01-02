import { useState, useEffect } from 'react'
import { submitFeedback, ApiError } from '../services/api'

type Step = 'input' | 'submitting' | 'done'

export default function Feedback() {
  const [step, setStep] = useState<Step>('input')
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'Feedback | In The Event Of My Death'
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (message.trim().length < 10) {
      setError('Please enter at least 10 characters')
      return
    }

    setStep('submitting')

    try {
      await submitFeedback(message, email || undefined)
      setStep('done')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail)
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
      setStep('input')
    }
  }

  const resetForm = () => {
    setStep('input')
    setMessage('')
    setEmail('')
    setError(null)
  }

  if (step === 'submitting') {
    return (
      <div className="feedback">
        <div className="hero-form">
          <h1>Sending Feedback...</h1>
          <div className="processing">
            <div className="spinner"></div>
          </div>
        </div>
      </div>
    )
  }

  if (step === 'done') {
    return (
      <div className="feedback">
        <div className="hero-form success-state">
          <h1>Thank You!</h1>
          <div className="success-message">
            <p>
              Your feedback has been received. We appreciate you taking the time to share your
              thoughts.
            </p>
          </div>
          <button onClick={resetForm} className="button secondary">
            Send More Feedback
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="feedback">
      <div className="hero-form">
        <h1>Feedback</h1>
        <p className="subtitle">
          Help us improve. Share your thoughts, suggestions, or report issues.
        </p>

        <form onSubmit={handleSubmit} className="feedback-form">
          <div className="form-group">
            <label htmlFor="message">Your Message</label>
            <textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="What's on your mind?"
              rows={6}
              required
              minLength={10}
              maxLength={2000}
              autoFocus
            />
            <span className="char-count">{message.length}/2000</span>
          </div>

          <div className="form-group">
            <label htmlFor="email">Email (optional)</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              maxLength={254}
            />
            <span className="field-hint">Only if you'd like a response</span>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            type="submit"
            className="button primary full-width"
            disabled={message.trim().length < 10}
          >
            Send Feedback
          </button>
        </form>
      </div>
    </div>
  )
}
