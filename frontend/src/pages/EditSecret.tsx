import { useState, useEffect, useCallback } from 'react'
import { extractFromFragment } from '../utils/urlFragments'
import { getEditSecretStatus, extendUnlockDate } from '../services/api'

type DatePreset = '+1w' | '+1m' | '+1y' | 'custom'

type State =
  | { type: 'loading' }
  | { type: 'missing_params' }
  | { type: 'loaded'; currentUnlockAt: Date }
  | { type: 'saving' }
  | { type: 'saved'; newUnlockAt: Date }
  | { type: 'already_unlocked' }
  | { type: 'already_retrieved' }
  | { type: 'not_found' }
  | { type: 'error'; message: string }

function getInitialParams(): { token: string | null } {
  const { token } = extractFromFragment()
  return { token: token || null }
}

export default function EditSecret() {
  const [params] = useState(getInitialParams)
  const [state, setState] = useState<State>(() =>
    params.token ? { type: 'loading' } : { type: 'missing_params' },
  )
  const [datePreset, setDatePreset] = useState<DatePreset>('+1m')
  const [customDate, setCustomDate] = useState('')
  const [customTime, setCustomTime] = useState('00:00')

  // Calculate new unlock date based on preset (relative to current unlock date)
  const getNewUnlockDate = (currentUnlockAt: Date): Date | null => {
    switch (datePreset) {
      case '+1w':
        return new Date(currentUnlockAt.getTime() + 7 * 24 * 60 * 60 * 1000)
      case '+1m': {
        const d = new Date(currentUnlockAt.getTime())
        d.setMonth(d.getMonth() + 1)
        return d
      }
      case '+1y': {
        const d = new Date(currentUnlockAt.getTime())
        d.setFullYear(d.getFullYear() + 1)
        return d
      }
      case 'custom':
        return customDate ? new Date(`${customDate}T${customTime}:00`) : null
    }
  }

  // Format unlock date for display
  const formatUnlockDate = (date: Date | null) => {
    if (!date) return null
    return {
      date: date.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }),
      time: date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
    }
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

      if (status.unlock_at) {
        const unlockAt = new Date(status.unlock_at)

        // Check if already unlocked
        if (unlockAt <= new Date()) {
          setState({ type: 'already_unlocked' })
          return
        }

        setState({ type: 'loaded', currentUnlockAt: unlockAt })
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

    if (!newUnlockAt) {
      setState({
        type: 'error',
        message: 'Please select an unlock date',
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

    setState({ type: 'saving' })

    try {
      await extendUnlockDate(params.token, newUnlockAt.toISOString())
      setState({ type: 'saved', newUnlockAt })
    } catch (err) {
      setState({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update unlock date',
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

  if (state.type === 'saving') {
    return (
      <div className="edit-secret">
        <h1>Updating...</h1>
        <div className="loading">Saving new unlock date...</div>
      </div>
    )
  }

  if (state.type === 'saved') {
    return (
      <div className="edit-secret">
        <h1>Unlock Date Updated</h1>
        <div className="success-message">
          <p>
            The unlock date has been extended to{' '}
            <strong>
              {state.newUnlockAt.toLocaleDateString()} at {state.newUnlockAt.toLocaleTimeString()}
            </strong>
          </p>
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
  const newUnlockDisplay = formatUnlockDate(newUnlockDate)
  const currentUnlockDisplay = formatUnlockDate(state.currentUnlockAt)
  const isValid = datePreset !== 'custom' || (customDate && customTime)

  return (
    <div className="edit-secret">
      <h1>Extend Unlock Date</h1>

      <div className="current-info">
        <p>
          Currently unlocks:{' '}
          <strong>
            {currentUnlockDisplay?.date} at {currentUnlockDisplay?.time}
          </strong>
        </p>
      </div>

      <form onSubmit={handleSubmit}>
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

        {newUnlockDisplay && (
          <p className="unlock-preview">
            New unlock: {newUnlockDisplay.date} at {newUnlockDisplay.time}
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

        <button type="submit" className="button primary full-width" disabled={!isValid}>
          Update Unlock Date
        </button>
      </form>
    </div>
  )
}
