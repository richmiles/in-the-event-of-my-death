/**
 * URL fragment handling utilities.
 *
 * Keys and tokens are passed in URL fragments (after #) which are
 * never sent to the server (per RFC 3986).
 */

import type { ShareableLinks } from '../types'

/**
 * Parse key-value pairs from a URL fragment.
 */
export function parseFragment(hash: string): Record<string, string> {
  // Remove leading #
  const fragment = hash.startsWith('#') ? hash.slice(1) : hash

  if (!fragment) return {}

  const params: Record<string, string> = {}

  for (const pair of fragment.split('&')) {
    const [key, value] = pair.split('=')
    if (key && value) {
      params[decodeURIComponent(key)] = decodeURIComponent(value)
    }
  }

  return params
}

/**
 * Build a URL fragment from key-value pairs.
 */
export function buildFragment(params: Record<string, string>): string {
  const pairs = Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')

  return pairs ? `#${pairs}` : ''
}

/**
 * Generate shareable links for a secret.
 *
 * Edit link: for the author to extend the unlock date
 * View link: for recipients to retrieve after unlock
 */
export function generateShareableLinks(
  editToken: string,
  decryptToken: string,
  encryptionKey: string,
  baseUrl: string = window.location.origin,
): ShareableLinks {
  const editFragment = buildFragment({ token: editToken, key: encryptionKey })
  const viewFragment = buildFragment({ token: decryptToken, key: encryptionKey })

  return {
    editLink: `${baseUrl}/edit${editFragment}`,
    viewLink: `${baseUrl}/view${viewFragment}`,
  }
}

/**
 * Extract token and key from current URL fragment.
 */
export function extractFromFragment(): { token?: string; key?: string } {
  const params = parseFragment(window.location.hash)
  return {
    token: params.token,
    key: params.key,
  }
}
