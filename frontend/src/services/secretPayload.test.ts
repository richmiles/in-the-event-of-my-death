import { describe, it, expect } from 'vitest'
import { decodeSecretPayload, encodeSecretPayloadV1 } from './secretPayload'

describe('secretPayload', () => {
  it('round-trips text-only payload', () => {
    const encoded = encodeSecretPayloadV1({ text: 'hello', attachments: [] })
    const decoded = decodeSecretPayload(encoded)
    expect(decoded).toEqual({ text: 'hello', attachments: [] })
  })

  it('round-trips payload with attachments', () => {
    const encoded = encodeSecretPayloadV1({
      text: 'see attached',
      attachments: [
        {
          name: 'a.txt',
          type: 'text/plain',
          bytes: new TextEncoder().encode('abc'),
        },
        {
          name: 'b.bin',
          type: 'application/octet-stream',
          bytes: new Uint8Array([0, 255, 1]),
        },
      ],
    })

    const decoded = decodeSecretPayload(encoded)
    expect(decoded.text).toBe('see attached')
    expect(decoded.attachments).toHaveLength(2)
    expect(decoded.attachments[0].name).toBe('a.txt')
    expect(decoded.attachments[0].type).toBe('text/plain')
    expect(new TextDecoder().decode(decoded.attachments[0].bytes)).toBe('abc')
    expect(decoded.attachments[1].name).toBe('b.bin')
    expect(decoded.attachments[1].type).toBe('application/octet-stream')
    expect(Array.from(decoded.attachments[1].bytes)).toEqual([0, 255, 1])
  })

  it('treats unknown payload as utf-8 text (backwards compatible)', () => {
    const bytes = new TextEncoder().encode('legacy secret')
    const decoded = decodeSecretPayload(bytes)
    expect(decoded).toEqual({ text: 'legacy secret', attachments: [] })
  })
})
