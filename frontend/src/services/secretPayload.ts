export type SecretAttachmentInput = {
  name: string
  type: string
  bytes: Uint8Array
}

export type SecretAttachment = {
  name: string
  type: string
  bytes: Uint8Array
}

export type SecretPayload = {
  text: string
  attachments: SecretAttachment[]
}

const MAGIC = new Uint8Array([0x49, 0x45, 0x4f, 0x4d, 0x44]) // "IEOMD"
const VERSION = 1

function writeU32BE(value: number): Uint8Array {
  const bytes = new Uint8Array(4)
  bytes[0] = (value >>> 24) & 0xff
  bytes[1] = (value >>> 16) & 0xff
  bytes[2] = (value >>> 8) & 0xff
  bytes[3] = value & 0xff
  return bytes
}

function readU32BE(bytes: Uint8Array, offset: number): number {
  return (
    ((bytes[offset] << 24) |
      (bytes[offset + 1] << 16) |
      (bytes[offset + 2] << 8) |
      bytes[offset + 3]) >>>
    0
  )
}

function startsWithMagic(payload: Uint8Array): boolean {
  if (payload.length < MAGIC.length + 1) return false
  for (let i = 0; i < MAGIC.length; i++) {
    if (payload[i] !== MAGIC[i]) return false
  }
  return payload[MAGIC.length] === VERSION
}

export function encodeSecretPayloadV1(input: {
  text: string
  attachments: SecretAttachmentInput[]
}): Uint8Array {
  const encoder = new TextEncoder()

  const header = {
    v: 1,
    text: input.text,
    attachments: input.attachments.map((a) => ({
      name: a.name,
      type: a.type,
      size: a.bytes.length,
    })),
  }

  const headerBytes = encoder.encode(JSON.stringify(header))
  const headerLenBytes = writeU32BE(headerBytes.length)

  let dataLen = 0
  for (const attachment of input.attachments) {
    dataLen += attachment.bytes.length
  }

  const totalLen = MAGIC.length + 1 + 4 + headerBytes.length + dataLen
  const out = new Uint8Array(totalLen)
  let offset = 0

  out.set(MAGIC, offset)
  offset += MAGIC.length
  out[offset] = VERSION
  offset += 1

  out.set(headerLenBytes, offset)
  offset += 4
  out.set(headerBytes, offset)
  offset += headerBytes.length

  for (const attachment of input.attachments) {
    out.set(attachment.bytes, offset)
    offset += attachment.bytes.length
  }

  return out
}

export function decodeSecretPayload(payloadBytes: Uint8Array): SecretPayload {
  if (!startsWithMagic(payloadBytes)) {
    const decoder = new TextDecoder()
    return { text: decoder.decode(payloadBytes), attachments: [] }
  }

  const decoder = new TextDecoder()

  let offset = MAGIC.length + 1
  if (payloadBytes.length < offset + 4) {
    throw new Error('Invalid payload: truncated header length')
  }

  const headerLen = readU32BE(payloadBytes, offset)
  offset += 4

  if (payloadBytes.length < offset + headerLen) {
    throw new Error('Invalid payload: truncated header')
  }

  const headerJson = decoder.decode(payloadBytes.slice(offset, offset + headerLen))
  offset += headerLen

  let header: {
    v?: unknown
    text?: unknown
    attachments?: { name?: unknown; type?: unknown; size?: unknown }[]
  }
  try {
    header = JSON.parse(headerJson)
  } catch {
    throw new Error('Invalid payload: header is not valid JSON')
  }

  if (header.v !== 1) {
    throw new Error(`Unsupported payload version: ${String(header.v)}`)
  }

  const text = typeof header.text === 'string' ? header.text : ''
  const attachmentsMeta = Array.isArray(header.attachments) ? header.attachments : []

  const attachments: SecretAttachment[] = []
  for (const meta of attachmentsMeta) {
    const name = typeof meta.name === 'string' ? meta.name : 'attachment'
    const type = typeof meta.type === 'string' ? meta.type : 'application/octet-stream'
    const size = typeof meta.size === 'number' ? meta.size : 0

    if (size < 0 || !Number.isFinite(size)) {
      throw new Error('Invalid payload: attachment size invalid')
    }
    if (payloadBytes.length < offset + size) {
      throw new Error('Invalid payload: truncated attachment data')
    }

    attachments.push({
      name,
      type,
      bytes: payloadBytes.slice(offset, offset + size),
    })
    offset += size
  }

  return { text, attachments }
}
