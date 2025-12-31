import { describe, it, expect } from 'vitest'
import { resolveApiBaseUrl } from './apiBase'

describe('resolveApiBaseUrl', () => {
  it('defaults to local backend in dev', () => {
    expect(resolveApiBaseUrl({ isDev: true, origin: 'http://localhost:5173' })).toBe(
      'http://localhost:8000/api/v1',
    )
  })

  it('defaults to same-origin in prod', () => {
    expect(resolveApiBaseUrl({ isDev: false, origin: 'https://staging.ieomd.com' })).toBe(
      'https://staging.ieomd.com/api/v1',
    )
  })

  it('accepts configured backend origin and appends /api/v1', () => {
    expect(
      resolveApiBaseUrl({
        apiUrl: 'https://api-staging.ieomd.com',
        isDev: false,
        origin: 'https://staging.ieomd.com',
      }),
    ).toBe('https://api-staging.ieomd.com/api/v1')
  })

  it('accepts configured /api/v1 base directly', () => {
    expect(
      resolveApiBaseUrl({
        apiUrl: 'https://staging.ieomd.com/api/v1',
        isDev: false,
        origin: 'https://staging.ieomd.com',
      }),
    ).toBe('https://staging.ieomd.com/api/v1')
  })

  it('accepts relative /api/v1', () => {
    expect(
      resolveApiBaseUrl({
        apiUrl: '/api/v1',
        isDev: false,
        origin: 'https://staging.ieomd.com',
      }),
    ).toBe('https://staging.ieomd.com/api/v1')
  })
})
