# Vault & Capability-Based Identity – Design Document

This document outlines the design for a **capability-based identity system** that enables users to track secrets they've created and sync across devices—without traditional accounts. The core principle is "users without users": possession of a cryptographic key is the identity.

> **Status:** Draft – Open for iteration
> **Issue:** [#157](https://github.com/richmiles/in-the-event-of-my-death/issues/157)
> **Project:** [v0.4 - Vault & Capability Identity](https://github.com/users/richmiles/projects/13)

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

---

## 2. Terminology

| Term | Definition |
|------|------------|
| **vaultKey** | Random 256-bit key generated on first use, stored client-side |
| **vaultId** | `SHA-256(vaultKey)` – identifies the vault on server (not reversible) |
| **syncToken** | Bearer token for write operations (prevents unauthorized overwrites) |
| **Recovery Kit** | Exported vaultKey for backup (file, QR, or mnemonic) |

---

## 3. Functional Requirements

- **VR1:** Generate and store a vaultKey on first secret creation
- **VR2:** Encrypt vault contents client-side before any server storage
- **VR3:** Store encrypted vault blob on server, keyed by vaultId
- **VR4:** Enable cross-device sync via device pairing mechanism
- **VR5:** Provide recovery kit export/import for backup
- **VR6:** Display dashboard of tracked secrets with status
- **VR7:** Server must never have access to vault contents or vaultKey

---

## 4. Non-Functional Requirements

- **Security:** All vault contents encrypted with keys derived from vaultKey
- **Privacy:** Server stores only opaque ciphertext; no metadata leakage
- **Reliability:** Conflict resolution for concurrent edits
- **Usability:** Clear UX for pairing, recovery, and status tracking
- **Offline-first:** Local vault works without connectivity

---

## 5. Architecture

### 5.1 Cryptographic Design

```
vaultKey (256-bit random)
    │
    ├─► HKDF(vaultKey, "enc") ──► encKey (AES-256-GCM encryption)
    │
    ├─► HKDF(vaultKey, "mac") ──► macKey (HMAC integrity)
    │
    └─► SHA-256(vaultKey) ──────► vaultId (server identifier)
```

- **Key derivation:** HKDF (RFC 5869) to derive purpose-specific keys
- **Encryption:** AES-256-GCM for authenticated encryption
- **Integrity:** HMAC for additional integrity verification
- **Identifier:** SHA-256 hash ensures server cannot reverse to vaultKey

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
  encryptionKey: string      // The secret's encryption key
  createdAt: string          // ISO timestamp
  unlockAt: string           // When secret unlocks
  expiresAt: string          // When secret expires
  label?: string             // User-defined label
  recipientHint?: string     // "For: Mom" etc.
  status?: 'pending' | 'unlocked' | 'retrieved' | 'expired'
}

interface Vault {
  version: number
  entries: VaultEntry[]
  createdAt: string
  lastModified: string
}
```

#### Server-Side

- **Storage:** Encrypted blob keyed by vaultId
- **Access control:** syncToken required for writes
- **Versioning:** ETags for conflict detection
- **No metadata:** Server stores only opaque ciphertext

```
POST /api/vault/{vaultId}
Authorization: Bearer {syncToken}
If-Match: {etag}
Body: { ciphertext: "..." }
```

### 5.3 Sync Protocol

1. **Pull:** Client fetches encrypted blob by vaultId
2. **Decrypt:** Client decrypts with encKey derived from vaultKey
3. **Merge:** Client merges with local state (conflict resolution TBD)
4. **Encrypt:** Client encrypts merged state
5. **Push:** Client uploads with syncToken and If-Match header

---

## 6. Device Pairing

### Option A: Short-Code Session (Recommended)

Most secure option—vaultKey never appears in a URL.

**Flow:**
1. Device A initiates pairing, receives session ID from server
2. Device A displays 6-digit code (valid 5 minutes)
3. Device B enters code
4. Server facilitates ephemeral key exchange (e.g., X25519)
5. Device A encrypts vaultKey with shared secret, sends via server
6. Device B decrypts vaultKey
7. Session destroyed

**Security properties:**
- vaultKey never in URL or logs
- Time-limited (replay window minimized)
- Requires physical proximity or real-time communication

### Option B: Password-Wrapped Link

Simpler but riskier.

**Flow:**
1. Device A generates link with encrypted vaultKey in fragment
2. Encryption uses password provided by user
3. Device B opens link, enters password
4. vaultKey decrypted client-side

**Risks:**
- URL may appear in browser history, logs
- Password strength varies

### Option C: QR Code

Good for in-person pairing.

**Flow:**
1. Device A displays QR containing vaultKey (or encrypted key)
2. Device B scans with camera
3. vaultKey transferred directly

**Tradeoffs:**
- Works offline
- Requires camera access
- In-person only

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
- Minimal third-party scripts
- Regular security audits
- Consider Web Worker for key operations (harder to exfiltrate)

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
- Cannot determine which vaultIds are active

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
Device A: Settings → "Add Device" → Display 6-digit code
    │
Device B: Settings → "Link Device" → Enter code
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
- Short-code pairing flow
- Recovery kit export/import

### Phase 4: Polish
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

---

## 14. Discussion

This document is a living design. Key areas for feedback:

- [ ] Pairing mechanism preference (short-code vs. alternatives)
- [ ] Conflict resolution strategy
- [ ] Recovery kit format (file vs. QR vs. mnemonic)
- [ ] Premium feature boundaries
- [ ] Migration path for existing users
