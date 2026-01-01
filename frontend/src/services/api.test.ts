import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { retrieveSecret } from './api'

describe('retrieveSecret', () => {
  const mockFetch = vi.fn()
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    globalThis.fetch = mockFetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.resetAllMocks()
  })

  it('returns expired status when backend returns 410 with status=expired', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 410,
      json: async () => ({
        detail: {
          status: 'expired',
          expires_at: '2024-01-15T12:00:00Z',
          message: 'This secret has expired and is no longer available',
        },
      }),
    })

    const result = await retrieveSecret('test-token')

    expect(result.status).toBe('expired')
    expect(result.expires_at).toBe('2024-01-15T12:00:00Z')
    expect(result.message).toBe('This secret has expired and is no longer available')
  })

  it('returns retrieved status when backend returns 410 with status=retrieved', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 410,
      json: async () => ({
        detail: {
          status: 'retrieved',
          message: 'This secret has already been viewed',
        },
      }),
    })

    const result = await retrieveSecret('test-token')

    expect(result.status).toBe('retrieved')
    expect(result.message).toBe('This secret has already been viewed')
  })

  it('returns retrieved status with default message when 410 has no detail', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 410,
      json: async () => ({}),
    })

    const result = await retrieveSecret('test-token')

    expect(result.status).toBe('retrieved')
    expect(result.message).toBe('This secret has already been retrieved')
  })

  it('returns pending status when backend returns 403', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({
        detail: {
          status: 'pending',
          unlock_at: '2024-12-31T23:59:59Z',
          message: 'Secret not yet available',
        },
      }),
    })

    const result = await retrieveSecret('test-token')

    expect(result.status).toBe('pending')
    expect(result.unlock_at).toBe('2024-12-31T23:59:59Z')
    expect(result.message).toBe('Secret not yet available')
  })

  it('returns secret data on successful retrieval', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'available',
        ciphertext: 'encrypted-data',
        iv: 'iv-data',
        auth_tag: 'auth-tag-data',
      }),
    })

    const result = await retrieveSecret('test-token')

    expect(result.status).toBe('available')
    expect(result.ciphertext).toBe('encrypted-data')
    expect(result.iv).toBe('iv-data')
    expect(result.auth_tag).toBe('auth-tag-data')
  })
})
