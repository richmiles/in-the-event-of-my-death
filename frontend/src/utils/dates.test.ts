import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  applyDateOffset,
  validateExpiryDate,
  formatDateForDisplay,
  MIN_EXPIRY_GAP_MS,
  MAX_EXPIRY_MS,
  type DatePreset,
} from './dates'

describe('dates utilities', () => {
  describe('applyDateOffset', () => {
    let baseDate: Date

    beforeEach(() => {
      // Use a fixed date for consistent testing
      baseDate = new Date('2025-01-01T12:00:00Z')
    })

    it('should add 1 week for "1w" preset', () => {
      const result = applyDateOffset(baseDate, '1w')
      expect(result).not.toBeNull()
      expect(result?.getTime()).toBe(baseDate.getTime() + 7 * 24 * 60 * 60 * 1000)
    })

    it('should add 1 week for "+1w" extend preset', () => {
      const result = applyDateOffset(baseDate, '+1w')
      expect(result).not.toBeNull()
      expect(result?.getTime()).toBe(baseDate.getTime() + 7 * 24 * 60 * 60 * 1000)
    })

    it('should add 1 month for "1m" preset', () => {
      const result = applyDateOffset(baseDate, '1m')
      expect(result).not.toBeNull()
      expect(result?.getMonth()).toBe(1) // February (0-indexed)
    })

    it('should add 1 year for "1y" preset', () => {
      const result = applyDateOffset(baseDate, '1y')
      expect(result).not.toBeNull()
      expect(result?.getFullYear()).toBe(2026)
    })

    it('should parse custom date and time', () => {
      const result = applyDateOffset(baseDate, 'custom', {
        date: '2025-06-15',
        time: '14:30',
      })
      expect(result).not.toBeNull()
      expect(result?.getFullYear()).toBe(2025)
      expect(result?.getMonth()).toBe(5) // June (0-indexed)
      expect(result?.getDate()).toBe(15)
    })

    it('should return null for custom preset without custom input', () => {
      const result = applyDateOffset(baseDate, 'custom')
      expect(result).toBeNull()
    })

    it('should return null for invalid preset', () => {
      const result = applyDateOffset(baseDate, 'invalid' as DatePreset)
      expect(result).toBeNull()
    })
  })

  describe('validateExpiryDate', () => {
    let now: Date
    let unlockAt: Date

    beforeEach(() => {
      // Mock the current date
      vi.useFakeTimers()
      now = new Date('2025-01-01T12:00:00Z')
      vi.setSystemTime(now)
      unlockAt = new Date('2025-01-02T12:00:00Z')
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('should reject expiry date less than 15 minutes after unlock', () => {
      const expiresAt = new Date(unlockAt.getTime() + 10 * 60 * 1000) // 10 minutes
      const error = validateExpiryDate(unlockAt, expiresAt)
      expect(error).toBe('Expiry date must be at least 15 minutes after unlock date')
    })

    it('should accept expiry date exactly 15 minutes after unlock', () => {
      const expiresAt = new Date(unlockAt.getTime() + MIN_EXPIRY_GAP_MS)
      const error = validateExpiryDate(unlockAt, expiresAt)
      expect(error).toBeNull()
    })

    it('should reject expiry date more than 5 years from now', () => {
      const expiresAt = new Date(now.getTime() + MAX_EXPIRY_MS + 1000)
      const error = validateExpiryDate(unlockAt, expiresAt)
      expect(error).toBe('Expiry date cannot exceed 5 years from now')
    })

    it('should accept valid expiry date', () => {
      const expiresAt = new Date(unlockAt.getTime() + 7 * 24 * 60 * 60 * 1000) // 1 week
      const error = validateExpiryDate(unlockAt, expiresAt)
      expect(error).toBeNull()
    })
  })

  describe('formatDateForDisplay', () => {
    it('should return null for null date', () => {
      const result = formatDateForDisplay(null)
      expect(result).toBeNull()
    })

    it('should format date with locale-aware formatting', () => {
      const date = new Date('2025-01-15T14:30:00Z')
      const result = formatDateForDisplay(date)
      expect(result).not.toBeNull()
      expect(result?.date).toBeTruthy()
      expect(result?.time).toBeTruthy()
      // Check that it contains date components (format varies by locale)
      expect(result?.date).toMatch(/Jan|15|2025/)
    })
  })
})
