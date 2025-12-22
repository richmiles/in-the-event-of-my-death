import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  parseFragment,
  buildFragment,
  generateShareableLinks,
  extractFromFragment,
} from './urlFragments'

describe('urlFragments utilities', () => {
  describe('parseFragment', () => {
    it('should parse a single key-value pair', () => {
      const result = parseFragment('#key=value')
      expect(result).toEqual({ key: 'value' })
    })

    it('should parse multiple key-value pairs', () => {
      const result = parseFragment('#key1=value1&key2=value2')
      expect(result).toEqual({ key1: 'value1', key2: 'value2' })
    })

    it('should handle URL-encoded values', () => {
      const result = parseFragment('#token=abc%20123&key=def%2Fghi')
      expect(result).toEqual({ token: 'abc 123', key: 'def/ghi' })
    })

    it('should handle fragment without leading #', () => {
      const result = parseFragment('key=value')
      expect(result).toEqual({ key: 'value' })
    })

    it('should return empty object for empty fragment', () => {
      expect(parseFragment('')).toEqual({})
      expect(parseFragment('#')).toEqual({})
    })

    it('should ignore malformed pairs', () => {
      const result = parseFragment('#key1=value1&malformed&key2=value2')
      expect(result).toEqual({ key1: 'value1', key2: 'value2' })
    })
  })

  describe('buildFragment', () => {
    it('should build fragment from single key-value pair', () => {
      const result = buildFragment({ key: 'value' })
      expect(result).toBe('#key=value')
    })

    it('should build fragment from multiple key-value pairs', () => {
      const result = buildFragment({ key1: 'value1', key2: 'value2' })
      // Order may vary, so check both possibilities
      expect(['#key1=value1&key2=value2', '#key2=value2&key1=value1']).toContain(result)
    })

    it('should URL-encode values', () => {
      const result = buildFragment({ token: 'abc 123', key: 'def/ghi' })
      expect(result).toContain('abc%20123')
      expect(result).toContain('def%2Fghi')
    })

    it('should return empty string for empty object', () => {
      const result = buildFragment({})
      expect(result).toBe('')
    })
  })

  describe('generateShareableLinks', () => {
    it('should generate edit and view links with correct fragments', () => {
      const result = generateShareableLinks(
        'edit-token-123',
        'decrypt-token-456',
        'encryption-key-789',
        'https://example.com',
      )

      expect(result.editLink).toContain('https://example.com/edit#')
      expect(result.editLink).toContain('token=edit-token-123')
      expect(result.editLink).toContain('key=encryption-key-789')

      expect(result.viewLink).toContain('https://example.com/view#')
      expect(result.viewLink).toContain('token=decrypt-token-456')
      expect(result.viewLink).toContain('key=encryption-key-789')
    })

    it('should use default base URL from environment', () => {
      const originalEnv = import.meta.env.VITE_BASE_URL
      vi.stubGlobal('location', { origin: 'https://default.com' })

      const result = generateShareableLinks('edit-token', 'decrypt-token', 'key')

      expect(result.editLink).toContain('/edit#')
      expect(result.viewLink).toContain('/view#')

      vi.unstubAllGlobals()
    })
  })

  describe('extractFromFragment', () => {
    let originalLocation: Location

    beforeEach(() => {
      originalLocation = window.location
      delete (window as any).location
    })

    afterEach(() => {
      window.location = originalLocation
    })

    it('should extract token and key from URL fragment', () => {
      window.location = { hash: '#token=abc123&key=def456' } as Location
      const result = extractFromFragment()
      expect(result).toEqual({ token: 'abc123', key: 'def456' })
    })

    it('should return undefined for missing values', () => {
      window.location = { hash: '#other=value' } as Location
      const result = extractFromFragment()
      expect(result).toEqual({ token: undefined, key: undefined })
    })

    it('should handle empty fragment', () => {
      window.location = { hash: '' } as Location
      const result = extractFromFragment()
      expect(result).toEqual({ token: undefined, key: undefined })
    })
  })
})
