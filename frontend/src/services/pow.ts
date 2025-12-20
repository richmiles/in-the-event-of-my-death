/**
 * Proof-of-work solver service.
 *
 * Wraps the Web Worker for easier use.
 */

import type { Challenge, PowProof } from '../types'

interface PowProgress {
  type: 'progress'
  iterations: number
}

interface PowSuccess {
  type: 'success'
  counter: number
  hash: string
}

interface PowError {
  type: 'error'
  message: string
}

type PowResponse = PowProgress | PowSuccess | PowError

/**
 * Solve a proof-of-work challenge.
 *
 * @param challenge - The challenge from the server
 * @param payloadHash - SHA256 hash of the payload
 * @param onProgress - Optional callback for progress updates
 * @returns The proof to submit to the server
 */
export async function solveChallenge(
  challenge: Challenge,
  payloadHash: string,
  onProgress?: (iterations: number) => void,
): Promise<PowProof> {
  return new Promise((resolve, reject) => {
    // Create the worker
    const worker = new Worker(new URL('../workers/pow.worker.ts', import.meta.url), {
      type: 'module',
    })

    worker.onmessage = (event: MessageEvent<PowResponse>) => {
      const response = event.data

      switch (response.type) {
        case 'progress':
          onProgress?.(response.iterations)
          break

        case 'success':
          worker.terminate()
          resolve({
            challenge_id: challenge.challenge_id,
            nonce: challenge.nonce,
            counter: response.counter,
            payload_hash: payloadHash,
          })
          break

        case 'error':
          worker.terminate()
          reject(new Error(response.message))
          break
      }
    }

    worker.onerror = (error) => {
      worker.terminate()
      reject(new Error(`Worker error: ${error.message}`))
    }

    // Start the worker
    worker.postMessage({
      nonce: challenge.nonce,
      difficulty: challenge.difficulty,
      payloadHash,
    })
  })
}
