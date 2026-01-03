# Vault & Capability-Based Identity – Design Document

This document outlines the design for a **capability-based identity system** that enables users to track secrets they've created and sync across devices—without traditional accounts. The core principle is "users without users": possession of a cryptographic key is the identity.

> **Status:** Draft – Open for iteration
> **Issue:** [#157](https://github.com/richmiles/in-the-event-of-my-death/issues/157)
> **Project:** [IEOMD v0.4 - Vault & Capability Identity](https://github.com/users/richmiles/projects/13)

---

## 1. Overview

### Problem Statement

Currently, users create secrets and receive edit/view links. If they:
- Lose the edit link
- Want to track multiple secrets
- Switch devices

...there's no way to recover or manage their secrets. Adding traditional accounts (email/password) conflicts with the privacy-first philosophy.

### Goal

Enable secret tracking and multi-device access while maintaining zero-knowledge properties.

### Core Concept

The identity model is **capability-based**: possession of a `vaultKey` is the "account." No email, no password, no identity verification—just a secret you control.

### Non-Goals / Explicit Tradeoffs

- **No account recovery:** There is no "forgot password" or email-based recovery. If you lose the `vaultKey` (and recovery kit), the vault is unrecoverable by design.
- **No server-side visibility:** The server never needs access to plaintext, encryption keys, or a queryable index of vault contents.
- **No cryptographic protection from XSS:** If attacker-controlled JavaScript runs in-origin, it can exfiltrate or misuse the `vaultKey`. This design assumes XSS prevention is mandatory.

---

## 2. Terminology

| Term | Definition |
|------|------------|
| **vaultKey** | Random 256-bit key generated on first use, stored client-side |
| **vaultId** | `SHA-256(vaultKey)` – identifies the vault on server (not reversible) |
| **vaultBlob** | Single encrypted payload containing all vault state (entries, metadata, syncToken, etc.) |
| **syncToken** | Bearer token for write operations; server stores only a hash of it |
| **Recovery Kit** | Exported vaultKey for backup (file, QR, or mnemonic) |
| **ETag** | Server-provided version identifier for optimistic concurrency |

---

## 3. Functional Requirements

- **VR1:** Generate and store a vaultKey on first secret creation
- **VR2:** Encrypt vault contents client-side before any server storage
- **VR3:** Store encrypted vault blob on server, keyed by vaultId
- **VR4:** Enable cross-device sync via device pairing mechanism
- **VR5:** Provide recovery kit export/import for backup
- **VR6:** Display dashboard of tracked secrets with status
- **VR7:** Server must never have access to vault contents or vaultKey
- **VR8:** The `vaultKey` (and per-secret decryption keys) must never be transmitted to the server (including via query params); any key-in-link transfer must use the URL fragment only.

---

## 4. Non-Functional Requirements

- **Security:** All vault contents are encrypted client-side with keys derived from `vaultKey` (AEAD)
- **Privacy:** Server stores only opaque ciphertext; minimize metadata leakage (sizes/timestamps are unavoidable)
- **Reliability:** Conflict resolution for concurrent edits
- **Usability:** Clear UX for pairing, recovery, and status tracking
- **Offline-first:** Local vault works without connectivity

---

## 5. Architecture

### 5.1 Cryptographic Design

```
vaultKey (256-bit random)
    │
    ├─► HKDF(vaultKey, "vault:aead:v1") ──► vaultAeadKey (AES-256-GCM)
    │
    └─► SHA-256(vaultKey) ──────► vaultId (server identifier)
```

- **Key derivation:** HKDF (RFC 5869) to derive purpose-specific keys
- **Encryption:** AES-256-GCM (AEAD) for authenticated encryption
- **Identifier:** SHA-256 hash ensures server cannot reverse to vaultKey
- **AAD binding:** Include `vaultId` + schema version as additional authenticated data to prevent cross-vault blob substitution

### 5.2 Storage

#### Client-Side (IndexedDB)

IndexedDB preferred over localStorage:
- Larger storage capacity
- Structured data support
- Less likely to be cleared by browser cleanup
- Async API (non-blocking)

```typescript
interface VaultEntry {
  secretId: string           // Server-side secret ID
  editToken: string          // Capability token for editing
  viewToken?: string         // Optional: stored for reference
  encryptionKey: string      // Secret decryption key (from URL fragment; never sent to server)
  createdAt: string          // ISO timestamp
  unlockAt: string           // When secret unlocks
  expiresAt: string          // When secret expires
  label?: string             // User-defined label
  recipientHint?: string     // "For: Mom" etc.
  status?: 'pending' | 'unlocked' | 'retrieved' | 'expired'
}

interface Vault {
  version: number
  syncToken: string
  entries: VaultEntry[]
  createdAt: string
  lastModified: string
}
```

#### Server-Side

- **Storage:** Encrypted blob keyed by vaultId
- **Access control:** `syncToken` required for writes (server stores only `SHA-256(syncToken)`)
- **Versioning:** ETags for conflict detection
- **Minimize metadata:** Server stores only opaque ciphertext (plus required control fields)

```
GET /api/vault/{vaultId}
200 OK
ETag: "{etag}"
Body: { ciphertext: "..." }

PUT /api/vault/{vaultId}
Authorization: Bearer {syncToken}
If-Match: {etag}
Body: { ciphertext: "..." }
```

**Creation semantics (recommended):**
- First write uses `If-None-Match: *` to avoid accidental overwrite.
- If the vault already exists, client should treat it as "vault already registered" and proceed with normal sync (or prompt user if it expected a new vault).

**Bootstrap flow (first vault creation):**
1. Client generates `vaultKey` (256-bit random)
2. Client generates `syncToken` (256-bit random)
3. Client creates initial `Vault` object with `syncToken` inside
4. Client encrypts vault → `vaultBlob`
5. Client sends first write:
   ```
   PUT /api/vault/{vaultId}
   Authorization: Bearer {syncToken}
   If-None-Match: *
   Body: { ciphertext: "..." }
   ```
6. Server stores: `vaultId`, `ciphertext`, `etag`, `syncTokenHash = SHA-256(syncToken)`

**Why syncToken is inside the encrypted blob:**
- Paired devices need the `syncToken` to write
- Including it in the encrypted vault means new devices get it automatically on sync
- Server only stores the hash, so compromise doesn't expose the raw token

### 5.3 Sync Protocol

1. **Pull:** Client fetches encrypted blob by vaultId
2. **Decrypt:** Client decrypts with `vaultAeadKey` derived from vaultKey
3. **Merge:** Client merges with local state (see Conflict Resolution notes)
4. **Encrypt:** Client encrypts merged state
5. **Push:** Client uploads with syncToken and If-Match header

**Conflict resolution (suggested starting point):**
- Treat the vault as a single-writer-most-of-the-time document, but support multi-device edits.
- Start with an **entry-level merge** keyed by `secretId`, using `lastModified` per entry and a vault-level `lastModified` for UX.
- When conflicts cannot be merged safely (e.g., two different labels edited concurrently), surface a UI conflict prompt rather than silently losing data.

---

## 6. Device Pairing

**Goal:** Copy `vaultKey` to another device without introducing accounts.

**Important security note:** Any server-mediated key exchange must be **authenticated**. Otherwise, a malicious (or compromised) server can man-in-the-middle the exchange and learn the `vaultKey`.

### Option A: QR Code (Recommended for v1)

Good for in-person pairing and avoids server involvement.

**Flow:**
1. Device A displays QR containing `vaultKey` (or password-wrapped `vaultKey`)
2. Device B scans with camera
3. Device B stores `vaultKey` and syncs vault from server

**Tradeoffs:**
- Works offline
- Requires camera access
- In-person only

### Option B: Password-Wrapped Link (Remote-friendly)

Simpler to ship and works when devices aren't co-located.

**Flow:**
1. Device A generates a link containing an **encrypted** `vaultKey` in the URL fragment
2. User shares the link to themselves (e.g., notes app) and communicates the password out-of-band
3. Device B opens link, enters password, decrypts `vaultKey` client-side

**Risks / mitigations:**
- Fragments are not sent to the server, but URLs can appear in browser history and be copied around; keep TTL short and show clear warnings.
- Use a strong KDF for password-wrapping (and include a random salt).

### Option C: Short-Code Pairing Session (v2+)

Most secure server-mediated option, but only if the exchange is authenticated (e.g., SAS confirmation or QR-based key pinning).

**Flow:**
1. Device A initiates pairing, receives session ID from server
2. Device A displays 6-digit code (valid 5 minutes)
3. Device B enters code
4. Devices perform an authenticated key exchange via server relay (e.g., X25519 + SAS user confirmation)
5. Device A encrypts `vaultKey` with the shared secret, sends via server
6. Device B decrypts `vaultKey`
7. Session destroyed

**Security properties:**
- vaultKey never in URL
- Time-limited (replay window minimized)
- Requires physical proximity or real-time communication

---

## 7. Recovery

### Recovery Kit Export

On vault creation, prompt user to export recovery kit:

- **File download:** JSON or encrypted blob
- **QR code:** For printing/storing physically
- **Mnemonic phrase:** BIP-39 style word list (optional, adds complexity)

### Recovery Kit Import

1. User opens "Recover Vault" on new device
2. Uploads file, scans QR, or enters mnemonic
3. vaultKey extracted and stored
4. Vault synced from server

### No Recovery Without Kit

**Critical UX consideration:** Users must understand that losing the recovery kit and all paired devices means permanent loss of vault access. Secrets still exist on server but are untracked.

---

## 8. Security Considerations

### 8.1 XSS is Catastrophic

If an attacker can execute JavaScript on the page, they can exfiltrate the vaultKey.

**Mitigations:**
- Strict Content Security Policy (no inline scripts, no eval)
- Trusted Types (where supported)
- Minimal third-party scripts
- Regular security audits
- Prefer isolating crypto operations (and key handling) behind a small, well-audited surface; Web Workers can reduce accidental exposure but do not meaningfully protect against true XSS.

### 8.2 DoS via Ciphertext Clobbering

Without authentication, an attacker who learns vaultId could overwrite the vault blob.

**Mitigations:**
- syncToken (bearer token) required for writes
- Server-side versioning with ETags
- Conflict detection on client
- Rate limiting on write operations

### 8.3 Vault Discovery

vaultId is SHA-256(vaultKey)—computationally infeasible to enumerate.

### 8.4 Server Compromise

Even if server is compromised:
- Attacker gets encrypted blobs only
- Cannot decrypt without vaultKey
- Can observe vaultIds, blob sizes, timestamps, and access patterns (minimize logs/retention to reduce correlatability)

---

## 9. UX Flows

### 9.1 First Secret (New User)

```
User creates secret
    │
    ▼
App generates vaultKey, stores in IndexedDB
    │
    ▼
Edit token + metadata added to local vault
    │
    ▼
Show success + "Your secrets are being tracked"
    │
    ▼
Prompt: "Save your recovery kit" (dismissible but encouraged)
```

### 9.2 Returning User

```
User opens app
    │
    ▼
App checks IndexedDB for vaultKey
    │
    ├─► Found: Show "My Secrets" dashboard
    │
    └─► Not found: Normal create flow (new vault on first secret)
```

### 9.3 Dashboard

Display list of tracked secrets with:
- Label / recipient hint
- Status indicator (pending / unlocked / retrieved / expired)
- Unlock date
- Expiry date
- Quick actions (extend, view status)

### 9.4 Add Device

```
Device A: Settings → "Add Device" → Choose method (QR / link / session code)
    │
Device B: Settings → "Link Device" → Scan / open link / enter code
    │
    ▼
Key exchange completes
    │
    ▼
Device B syncs vault from server
```

---

## 10. Open Questions

1. **Sync frequency:** Push on every change? Pull on app open? WebSocket for real-time?

2. **Conflict resolution:** Last-write-wins? Entry-level merge? Show conflict to user?

3. **Vault expiry:** Should server-side blobs expire if not accessed? (Storage cost vs. expectation)

4. **Premium integration:** Is vault free or premium? Does it unlock other features?

5. **Migration:** How do existing users (with edit links, no vault) transition?

6. **Secret status sync:** Should vault poll server for secret status updates, or only on user action?

---

## 11. Implementation Phases

### Phase 1: Local-Only Vault
- IndexedDB storage
- Track secrets created in this session
- Dashboard UI showing status
- No sync, no pairing

### Phase 2: Server Sync
- Encrypted blob storage endpoint
- Pull/push sync protocol
- syncToken + ETag conflict handling

### Phase 3: Device Pairing
- QR-based pairing (in-person)
- Password-wrapped link (remote-friendly)
- Recovery kit export/import

### Phase 4: Polish
- Authenticated short-code pairing session (if needed)
- Conflict resolution UI
- Offline queue for changes
- Status polling for secrets
- Premium integration (if applicable)

---

## 12. References

- [HKDF RFC 5869](https://tools.ietf.org/html/rfc5869)
- [Web Crypto API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)
- [IndexedDB API](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
- [AES-GCM in Web Crypto](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/encrypt#aes-gcm)
- Signal Protocol (device linking inspiration)

---

## 13. Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-01-03 | Claude + Rich | Initial draft from design discussion |
| 2026-01-03 | Codex | Clarify crypto, pairing security model, and sync semantics |
| 2026-01-03 | Claude | Add syncToken bootstrap flow based on Codex clarification |

---

## 14. Discussion

This document is a living design. Key areas for feedback:

- [ ] Pairing mechanism preference (QR vs. password link vs. authenticated short-code)
- [ ] Conflict resolution strategy
- [ ] Recovery kit format (file vs. QR vs. mnemonic)
- [ ] Premium feature boundaries
- [ ] Migration path for existing users
