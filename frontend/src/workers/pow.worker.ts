/**
 * Web Worker for proof-of-work computation.
 *
 * Runs in a separate thread to avoid blocking the UI.
 */

interface PowRequest {
  nonce: string;
  difficulty: number;
  payloadHash: string;
}

interface PowProgress {
  type: 'progress';
  iterations: number;
}

interface PowSuccess {
  type: 'success';
  counter: number;
  hash: string;
}

interface PowError {
  type: 'error';
  message: string;
}

/**
 * Convert bytes to hex string.
 */
function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Convert Uint8Array to proper ArrayBuffer for Web Crypto API.
 */
function toArrayBuffer(data: Uint8Array): ArrayBuffer {
  const buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
  return buffer as ArrayBuffer;
}

/**
 * SHA-256 hash using Web Crypto API.
 */
async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const hashBuffer = await crypto.subtle.digest('SHA-256', toArrayBuffer(data));
  return new Uint8Array(hashBuffer);
}

/**
 * Convert a BigInt-like comparison for leading zero bits.
 */
function hashMeetsTarget(hashBytes: Uint8Array, difficulty: number): boolean {
  // Count leading zero bits
  let zeroBits = 0;

  for (const byte of hashBytes) {
    if (byte === 0) {
      zeroBits += 8;
    } else {
      // Count leading zeros in this byte
      zeroBits += Math.clz32(byte) - 24; // clz32 counts 32-bit, byte is 8-bit
      break;
    }
  }

  return zeroBits >= difficulty;
}

/**
 * Solve the proof-of-work challenge.
 */
async function solvePoW(request: PowRequest): Promise<void> {
  const { nonce, difficulty, payloadHash } = request;
  const encoder = new TextEncoder();
  const maxIterations = 2 ** 32;
  const progressInterval = 100_000;

  for (let counter = 0; counter < maxIterations; counter++) {
    // Construct preimage: nonce || counter (16 hex chars, zero-padded) || payloadHash
    const counterHex = counter.toString(16).padStart(16, '0');
    const preimage = `${nonce}${counterHex}${payloadHash}`;
    const preimageBytes = encoder.encode(preimage);

    // Hash
    const hashBytes = await sha256(preimageBytes);

    // Check if meets difficulty
    if (hashMeetsTarget(hashBytes, difficulty)) {
      const response: PowSuccess = {
        type: 'success',
        counter,
        hash: bytesToHex(hashBytes),
      };
      self.postMessage(response);
      return;
    }

    // Report progress
    if (counter > 0 && counter % progressInterval === 0) {
      const response: PowProgress = {
        type: 'progress',
        iterations: counter,
      };
      self.postMessage(response);
    }
  }

  const response: PowError = {
    type: 'error',
    message: 'Failed to solve PoW within iteration limit',
  };
  self.postMessage(response);
}

// Handle messages from the main thread
self.onmessage = (event: MessageEvent<PowRequest>) => {
  solvePoW(event.data).catch((error) => {
    const response: PowError = {
      type: 'error',
      message: error.message || 'Unknown error',
    };
    self.postMessage(response);
  });
};
