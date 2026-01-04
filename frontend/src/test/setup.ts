import 'fake-indexeddb/auto'
import '@testing-library/jest-dom/vitest'
import { Crypto } from '@peculiar/webcrypto'

// Replace crypto with polyfill for consistent behavior across environments
const crypto = new Crypto()
Object.defineProperty(globalThis, 'crypto', {
  value: crypto,
  writable: false,
  configurable: true,
})
