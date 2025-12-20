import { useState, useEffect } from 'react';
import { extractFromFragment } from '../utils/urlFragments';
import { getSecretStatus, extendUnlockDate } from '../services/api';

type State =
  | { type: 'loading' }
  | { type: 'missing_params' }
  | { type: 'loaded'; currentUnlockAt: Date }
  | { type: 'saving' }
  | { type: 'saved'; newUnlockAt: Date }
  | { type: 'already_unlocked' }
  | { type: 'already_retrieved' }
  | { type: 'not_found' }
  | { type: 'error'; message: string };

export default function EditSecret() {
  const [state, setState] = useState<State>({ type: 'loading' });
  const [token, setToken] = useState<string | null>(null);
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('00:00');

  useEffect(() => {
    const { token } = extractFromFragment();

    if (!token) {
      setState({ type: 'missing_params' });
      return;
    }

    setToken(token);
    loadStatus(token);
  }, []);

  const loadStatus = async (editToken: string) => {
    try {
      // Note: We're using the edit token as if it were a decrypt token here
      // In a real implementation, you might need a separate status endpoint for edit tokens
      // For now, we'll just try to extend with a far future date to check if the secret exists
      const status = await getSecretStatus(editToken);

      if (!status.exists || status.status === 'not_found') {
        setState({ type: 'not_found' });
        return;
      }

      if (status.status === 'retrieved') {
        setState({ type: 'already_retrieved' });
        return;
      }

      if (status.unlock_at) {
        const unlockAt = new Date(status.unlock_at);

        // Check if already unlocked
        if (unlockAt <= new Date()) {
          setState({ type: 'already_unlocked' });
          return;
        }

        setState({ type: 'loaded', currentUnlockAt: unlockAt });

        // Set default new date to current unlock date
        setNewDate(unlockAt.toISOString().split('T')[0]);
        setNewTime(unlockAt.toTimeString().slice(0, 5));
      }
    } catch {
      setState({ type: 'error', message: 'Failed to load secret status' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token || state.type !== 'loaded') return;

    const newUnlockAt = new Date(`${newDate}T${newTime}:00`);

    if (newUnlockAt <= state.currentUnlockAt) {
      setState({
        type: 'error',
        message: 'New unlock date must be after the current unlock date',
      });
      return;
    }

    setState({ type: 'saving' });

    try {
      await extendUnlockDate(token, newUnlockAt.toISOString());
      setState({ type: 'saved', newUnlockAt });
    } catch (err) {
      setState({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update unlock date',
      });
    }
  };

  if (state.type === 'loading') {
    return (
      <div className="edit-secret">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (state.type === 'missing_params') {
    return (
      <div className="edit-secret">
        <h1>Invalid Link</h1>
        <p>This link is missing the required token. Please check the URL and try again.</p>
      </div>
    );
  }

  if (state.type === 'not_found') {
    return (
      <div className="edit-secret">
        <h1>Secret Not Found</h1>
        <p>
          This secret doesn't exist. It may have been deleted or the link may be
          incorrect.
        </p>
      </div>
    );
  }

  if (state.type === 'already_retrieved') {
    return (
      <div className="edit-secret">
        <h1>Secret Already Retrieved</h1>
        <p>
          This secret has already been retrieved by the recipient and is no longer
          available.
        </p>
      </div>
    );
  }

  if (state.type === 'already_unlocked') {
    return (
      <div className="edit-secret">
        <h1>Secret Already Unlocked</h1>
        <p>
          This secret has already passed its unlock date. You can no longer edit it.
        </p>
      </div>
    );
  }

  if (state.type === 'saving') {
    return (
      <div className="edit-secret">
        <h1>Updating...</h1>
        <div className="loading">Saving new unlock date...</div>
      </div>
    );
  }

  if (state.type === 'saved') {
    return (
      <div className="edit-secret">
        <h1>Unlock Date Updated</h1>
        <div className="success-message">
          <p>
            The unlock date has been extended to{' '}
            <strong>
              {state.newUnlockAt.toLocaleDateString()} at{' '}
              {state.newUnlockAt.toLocaleTimeString()}
            </strong>
          </p>
        </div>
      </div>
    );
  }

  if (state.type === 'error') {
    return (
      <div className="edit-secret">
        <h1>Error</h1>
        <div className="error-message">{state.message}</div>
        <button onClick={() => token && loadStatus(token)} className="button">
          Try Again
        </button>
      </div>
    );
  }

  // state.type === 'loaded'
  return (
    <div className="edit-secret">
      <h1>Extend Unlock Date</h1>

      <div className="current-info">
        <p>
          Current unlock date:{' '}
          <strong>
            {state.currentUnlockAt.toLocaleDateString()} at{' '}
            {state.currentUnlockAt.toLocaleTimeString()}
          </strong>
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="new-date">New Unlock Date</label>
          <p className="help-text">
            Extend the time before your secret becomes available. You can only move
            the date forward, not backward.
          </p>
          <div className="date-time-inputs">
            <input
              type="date"
              id="new-date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              min={state.currentUnlockAt.toISOString().split('T')[0]}
              required
            />
            <input
              type="time"
              id="new-time"
              value={newTime}
              onChange={(e) => setNewTime(e.target.value)}
              required
            />
          </div>
        </div>

        <button type="submit" className="button primary">
          Update Unlock Date
        </button>
      </form>
    </div>
  );
}
