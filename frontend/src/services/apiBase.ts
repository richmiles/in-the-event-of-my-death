type ResolveApiBaseUrlOptions = {
  /**
   * Optional override for the backend server URL.
   * Accepts either an absolute URL (e.g. https://api.example.com)
   * or a relative path (e.g. /api/v1).
   */
  apiUrl?: string
  /**
   * Whether we're running in dev mode (Vite).
   * In dev, default to a local backend for convenience.
   */
  isDev: boolean
  /**
   * The current page origin, used to resolve relative URLs.
   */
  origin: string
}

const DEFAULT_DEV_API_ORIGIN = 'http://localhost:8000'
const API_PREFIX = '/api/v1'

function toUrl(input: string, origin: string): URL {
  const trimmed = input.trim()
  if (trimmed.startsWith('/')) return new URL(trimmed, origin)
  return new URL(trimmed)
}

function ensureApiPrefix(url: URL): URL {
  const next = new URL(url.toString())
  const normalizedPath = next.pathname.replace(/\/+$/, '')
  if (normalizedPath === API_PREFIX) return next
  next.pathname = API_PREFIX
  return next
}

export function resolveApiBaseUrl(options: ResolveApiBaseUrlOptions): string {
  const configured = options.apiUrl?.trim()
  const base =
    configured && configured.length > 0
      ? configured
      : options.isDev
        ? DEFAULT_DEV_API_ORIGIN
        : options.origin

  const parsed = toUrl(base, options.origin)
  const api = ensureApiPrefix(parsed)
  return api.toString().replace(/\/+$/, '')
}
