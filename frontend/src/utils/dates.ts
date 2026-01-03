/**
 * Date utilities for secret unlock and expiry handling.
 */

// Constants for validation
export const MIN_EXPIRY_GAP_MS = 15 * 60 * 1000 // 15 minutes
export const MAX_EXPIRY_MS = 5 * 365 * 24 * 60 * 60 * 1000 // ~5 years

// Preset types for date selection (unlock and expiry now match)
export type UnlockPreset = 'now' | '15m' | '1h' | '24h' | '1w' | 'custom'
export type ExpiryPreset = '15m' | '1h' | '24h' | '1w' | 'custom'
// Legacy presets for backwards compatibility
export type DatePreset = 'now' | '15m' | '1h' | '24h' | '1w' | '1m' | '1y' | 'custom'
export type ExtendPreset = 'none' | '+1w' | '+1m' | '+1y' | 'custom'

export interface CustomDateInput {
  date: string
  time: string
}

/**
 * Apply a date offset to a base date based on preset.
 * Works for both absolute presets ('1w') and extend presets ('+1w').
 */
export function applyDateOffset(
  baseDate: Date,
  preset: DatePreset | ExtendPreset,
  customInput?: CustomDateInput,
): Date | null {
  // Normalize preset by removing leading '+' if present
  const normalizedPreset = preset.startsWith('+') ? preset.slice(1) : preset

  switch (normalizedPreset) {
    case 'now':
      return new Date(baseDate.getTime())
    case '15m':
      return new Date(baseDate.getTime() + 15 * 60 * 1000)
    case '1h':
      return new Date(baseDate.getTime() + 60 * 60 * 1000)
    case '24h':
      return new Date(baseDate.getTime() + 24 * 60 * 60 * 1000)
    case '1w':
      return new Date(baseDate.getTime() + 7 * 24 * 60 * 60 * 1000)
    case '1m': {
      const d = new Date(baseDate.getTime())
      d.setMonth(d.getMonth() + 1)
      return d
    }
    case '1y': {
      const d = new Date(baseDate.getTime())
      d.setFullYear(d.getFullYear() + 1)
      return d
    }
    case 'custom':
      return customInput?.date ? new Date(`${customInput.date}T${customInput.time}:00`) : null
    default:
      return null
  }
}

/**
 * Validate expiry date constraints.
 * Returns error message if invalid, null if valid.
 */
export function validateExpiryDate(unlockAt: Date, expiresAt: Date): string | null {
  const now = new Date()

  // Check minimum gap (15 minutes after unlock)
  if (expiresAt.getTime() < unlockAt.getTime() + MIN_EXPIRY_GAP_MS) {
    return 'Expiry date must be at least 15 minutes after unlock date'
  }

  // Check maximum expiry (5 years from now)
  if (expiresAt.getTime() > now.getTime() + MAX_EXPIRY_MS) {
    return 'Expiry date cannot exceed 5 years from now'
  }

  return null
}

/**
 * Format a date for display with locale-aware formatting.
 */
export function formatDateForDisplay(date: Date | null): { date: string; time: string } | null {
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
