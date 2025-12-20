/**
 * API client for the backend.
 */

import type {
  Challenge,
  SecretCreateRequest,
  SecretCreateResponse,
  SecretStatusResponse,
  SecretRetrieveResponse,
} from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = 'An error occurred'
    try {
      const data = await response.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      detail = response.statusText
    }
    throw new ApiError(response.status, detail)
  }
  return response.json()
}

/**
 * Request a proof-of-work challenge.
 */
export async function requestChallenge(
  payloadHash: string,
  ciphertextSize: number,
): Promise<Challenge> {
  const response = await fetch(`${API_BASE}/challenges`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payload_hash: payloadHash,
      ciphertext_size: ciphertextSize,
    }),
  })
  return handleResponse<Challenge>(response)
}

/**
 * Create a new secret.
 */
export async function createSecret(request: SecretCreateRequest): Promise<SecretCreateResponse> {
  const response = await fetch(`${API_BASE}/secrets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return handleResponse<SecretCreateResponse>(response)
}

/**
 * Check the status of a secret without triggering one-time deletion.
 */
export async function getSecretStatus(decryptToken: string): Promise<SecretStatusResponse> {
  const response = await fetch(`${API_BASE}/secrets/status`, {
    headers: { Authorization: `Bearer ${decryptToken}` },
  })
  return handleResponse<SecretStatusResponse>(response)
}

/**
 * Retrieve a secret's encrypted content.
 * This is a ONE-TIME operation after unlock.
 */
export async function retrieveSecret(decryptToken: string): Promise<SecretRetrieveResponse> {
  const response = await fetch(`${API_BASE}/secrets/retrieve`, {
    headers: { Authorization: `Bearer ${decryptToken}` },
  })

  // Handle 403 (not yet unlocked) specially
  if (response.status === 403) {
    const data = await response.json()
    return {
      status: 'pending',
      unlock_at: data.detail?.unlock_at,
      message: data.detail?.message || 'Secret not yet available',
    }
  }

  // Handle 410 (already retrieved)
  if (response.status === 410) {
    return {
      status: 'retrieved',
      message: 'This secret has already been retrieved',
    }
  }

  return handleResponse<SecretRetrieveResponse>(response)
}

/**
 * Extend the unlock date of a secret.
 */
export async function extendUnlockDate(
  editToken: string,
  newUnlockAt: string,
): Promise<{ secret_id: string; unlock_at: string }> {
  const response = await fetch(`${API_BASE}/secrets/edit`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${editToken}`,
    },
    body: JSON.stringify({ unlock_at: newUnlockAt }),
  })
  return handleResponse(response)
}

export { ApiError }
