import { useState, useEffect, useCallback } from 'react'
import { extractFromFragment } from '../utils/urlFragments'
import { getEditSecretStatus, updateSecretDates } from '../services/api'
import {
  applyDateOffset,
  validateExpiryDate,
  formatDateForDisplay,
  type ExtendPreset,
} from '../utils/dates'

type State =
  | { type: 'loading' }
  | { type: 'missing_params' }
  | { type: 'loaded'; currentUnlockAt: Date; currentExpiresAt: Date }
  | { type: 'saving' }
  | { type: 'saved'; newUnlockAt: Date; newExpiresAt: Date }
  | { type: 'already_unlocked' }
  | { type: 'already_retrieved' }
  | { type: 'expired' }
  | { type: 'not_found' }
  | { type: 'error'; message: string }

function getInitialParams(): { token: string | null } {
  const { token } = extractFromFragment()
  return { token: token || null }
}

export default function EditSecret() {
  useEffect(() => {
    document.title = 'Edit Secret | In The Event Of My Death'
  }, [])

  const [params] = useState(getInitialParams)
  const [state, setState] = useState<State>(() =>
    params.token ? { type: 'loading' } : { type: 'missing_params' },
  )
  const [datePreset, setDatePreset] = useState<ExtendPreset>('none')
  const [customDate, setCustomDate] = useState('')
  const [customTime, setCustomTime] = useState('00:00')

  // Expiry date state
  const [expiryPreset, setExpiryPreset] = useState<ExtendPreset>('none')
  const [customExpiryDate, setCustomExpiryDate] = useState('')
  const [customExpiryTime, setCustomExpiryTime] = useState('00:00')

  // Calculate new unlock date based on preset (relative to current unlock date)
  const getNewUnlockDate = (currentUnlockAt: Date): Date | null => {
    return applyDateOffset(currentUnlockAt, datePreset, { date: customDate, time: customTime })
  }

  // Calculate new expiry date based on preset (relative to current expiry date)
  const getNewExpiryDate = (currentExpiresAt: Date): Date | null => {
    return applyDateOffset(currentExpiresAt, expiryPreset, {
      date: customExpiryDate,
      time: customExpiryTime,
    })
  }

  const loadStatus = useCallback(async (editToken: string) => {
    try {
      const status = await getEditSecretStatus(editToken)

      if (!status.exists || status.status === 'not_found') {
        setState({ type: 'not_found' })
        return
      }

      if (status.status === 'retrieved') {
        setState({ type: 'already_retrieved' })
        return
      }

      if (status.status === 'expired') {
        setState({ type: 'expired' })
        return
      }

      if (status.unlock_at && status.expires_at) {
        const unlockAt = new Date(status.unlock_at)
        const expiresAt = new Date(status.expires_at)

        // Check if already unlocked
        if (unlockAt <= new Date()) {
          setState({ type: 'already_unlocked' })
          return
        }

        setState({ type: 'loaded', currentUnlockAt: unlockAt, currentExpiresAt: expiresAt })
      }
    } catch {
      setState({ type: 'error', message: 'Failed to load secret status' })
    }
  }, [])

  useEffect(() => {
    if (params.token) {
      loadStatus(params.token)
    }
  }, [params.token, loadStatus])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!params.token || state.type !== 'loaded') return

    const newUnlockAt = getNewUnlockDate(state.currentUnlockAt)
    const newExpiresAt = getNewExpiryDate(state.currentExpiresAt)

    if (!newUnlockAt) {
      setState({
        type: 'error',
        message: 'Please select an unlock date',
      })
      return
    }

    if (!newExpiresAt) {
      setState({
        type: 'error',
        message: 'Please select an expiry date',
      })
      return
    }

    if (newUnlockAt <= state.currentUnlockAt) {
      setState({
        type: 'error',
        message: 'New unlock date must be after the current unlock date',
      })
      return
    }

    // Validate expiry constraints
    const expiryError = validateExpiryDate(newUnlockAt, newExpiresAt)
    if (expiryError) {
      setState({ type: 'error', message: expiryError })
      return
    }

    setState({ type: 'saving' })

    try {
      await updateSecretDates(params.token, newUnlockAt.toISOString(), newExpiresAt.toISOString())
      setState({ type: 'saved', newUnlockAt, newExpiresAt })
    } catch (err) {
      setState({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update dates',
      })
    }
  }

  if (state.type === 'loading') {
    return (
      <div className="edit-secret">
        <div className="loading">Loading...</div>
      </div>
    )
  }

  if (state.type === 'missing_params') {
    return (
      <div className="edit-secret">
        <h1>Invalid Link</h1>
        <p>This link is missing the required token. Please check the URL and try again.</p>
      </div>
    )
  }

  if (state.type === 'not_found') {
    return (
      <div className="edit-secret">
        <h1>Secret Not Found</h1>
        <p>This secret doesn't exist. It may have been deleted or the link may be incorrect.</p>
      </div>
    )
  }

  if (state.type === 'already_retrieved') {
    return (
      <div className="edit-secret">
        <h1>Secret Already Retrieved</h1>
        <p>This secret has already been retrieved by the recipient and is no longer available.</p>
      </div>
    )
  }

  if (state.type === 'already_unlocked') {
    return (
      <div className="edit-secret">
        <h1>Secret Already Unlocked</h1>
        <p>This secret has already passed its unlock date. You can no longer edit it.</p>
      </div>
    )
  }

  if (state.type === 'expired') {
    return (
      <div className="edit-secret">
        <h1>Secret Expired</h1>
        <p>This secret has expired and is no longer available.</p>
      </div>
    )
  }

  if (state.type === 'saving') {
    return (
      <div className="edit-secret">
        <h1>Updating...</h1>
        <div className="loading">Saving new dates...</div>
      </div>
    )
  }

  if (state.type === 'saved') {
    return (
      <div className="edit-secret">
        <h1>Dates Updated</h1>
        <div className="success-message">
          <div className="dates-info">
            <p>
              <strong>New unlock date:</strong> {state.newUnlockAt.toLocaleDateString()} at{' '}
              {state.newUnlockAt.toLocaleTimeString()}
            </p>
            <p>
              <strong>New expiry date:</strong> {state.newExpiresAt.toLocaleDateString()} at{' '}
              {state.newExpiresAt.toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (state.type === 'error') {
    return (
      <div className="edit-secret">
        <h1>Error</h1>
        <div className="error-message">{state.message}</div>
        <button onClick={() => params.token && loadStatus(params.token)} className="button">
          Try Again
        </button>
      </div>
    )
  }

  // state.type === 'loaded'
  const newUnlockDate = getNewUnlockDate(state.currentUnlockAt)
  const newUnlockDisplay = formatDateForDisplay(newUnlockDate)
  const currentUnlockDisplay = formatDateForDisplay(state.currentUnlockAt)
  const newExpiryDate = getNewExpiryDate(state.currentExpiresAt)
  const newExpiryDisplay = formatDateForDisplay(newExpiryDate)
  const currentExpiryDisplay = formatDateForDisplay(state.currentExpiresAt)
  const isValid =
    datePreset !== 'none' &&
    expiryPreset !== 'none' &&
    (datePreset !== 'custom' || (customDate && customTime)) &&
    (expiryPreset !== 'custom' || (customExpiryDate && customExpiryTime))

  return (
    <div className="edit-secret">
      <h1>Edit Secret Dates</h1>

      <div className="current-info">
        <p>
          Currently unlocks:{' '}
          <strong>
            {currentUnlockDisplay?.date} at {currentUnlockDisplay?.time}
          </strong>
        </p>
        <p>
          Currently expires:{' '}
          <strong>
            {currentExpiryDisplay?.date} at {currentExpiryDisplay?.time}
          </strong>
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <h3>Extend Unlock Date</h3>
        <div className="date-presets">
          <span className="presets-label">Extend by:</span>
          <button
            type="button"
            className={datePreset === '+1w' ? 'active' : ''}
            onClick={() => setDatePreset('+1w')}
          >
            +1 Week
          </button>
          <button
            type="button"
            className={datePreset === '+1m' ? 'active' : ''}
            onClick={() => setDatePreset('+1m')}
          >
            +1 Month
          </button>
          <button
            type="button"
            className={datePreset === '+1y' ? 'active' : ''}
            onClick={() => setDatePreset('+1y')}
          >
            +1 Year
          </button>
          <button
            type="button"
            className={datePreset === 'custom' ? 'active' : ''}
            onClick={() => setDatePreset('custom')}
          >
            Custom
          </button>
        </div>

        {datePreset === 'none' ? (
          <p className="field-hint">Select an extension to preview the new date</p>
        ) : (
          newUnlockDisplay && (
            <p className="unlock-preview">
              New unlock: {newUnlockDisplay.date} at {newUnlockDisplay.time}
            </p>
          )
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
                min={state.currentUnlockAt.toISOString().split('T')[0]}
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

        <h3>Extend Expiry Date</h3>
        <div className="date-presets">
          <span className="presets-label">Extend by:</span>
          <button
            type="button"
            className={expiryPreset === '+1w' ? 'active' : ''}
            onClick={() => setExpiryPreset('+1w')}
          >
            +1 Week
          </button>
          <button
            type="button"
            className={expiryPreset === '+1m' ? 'active' : ''}
            onClick={() => setExpiryPreset('+1m')}
          >
            +1 Month
          </button>
          <button
            type="button"
            className={expiryPreset === '+1y' ? 'active' : ''}
            onClick={() => setExpiryPreset('+1y')}
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

        {expiryPreset === 'none' ? (
          <p className="field-hint">Select an extension to preview the new date</p>
        ) : (
          newExpiryDisplay && (
            <p className="unlock-preview">
              New expiry: {newExpiryDisplay.date} at {newExpiryDisplay.time}
            </p>
          )
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
                min={state.currentExpiresAt.toISOString().split('T')[0]}
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

        <button type="submit" className="button primary full-width" disabled={!isValid}>
          Update Dates
        </button>
      </form>
    </div>
  )
}
