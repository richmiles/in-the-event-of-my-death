# InTheEventOfMyDeath.com – Design Document

This document outlines the functional, technical, and security design for **InTheEventOfMyDeath.com**, a time-locked secret delivery service. The goal is to enable a user to create an encrypted message or file with a configurable unlock time, distribute a decryption link to recipients, and retain an edit link to extend or modify the unlock time. Recipients can attempt to access the message at any time, but the ciphertext is only released after the unlock time has passed.

> **Terminology:** This system uses two distinct timestamps:
> - **Unlock time (`unlock_at`)**: When the secret becomes retrievable by recipients.
> - **Expiration time (`expires_at`)**: When the secret is automatically deleted from the server.

---

## 1. Overview

### Purpose
- Provide a **time-locked secret** delivery service that allows users to set up messages or files to be released after a specific unlock time.
- Maintain a **zero-knowledge** approach: the server stores only encrypted data and minimal metadata, never plaintext or decryption keys.
- Offer two distinct access links:
  - An **edit link** for the author to update the message or postpone its release.
  - A **decrypt link** for recipients to retrieve and decrypt the message after unlock.

### Scope
- **In scope:** web UI, client-side encryption/decryption, unlock/expiration handling, abuse mitigation, minimal API for secret management.
- **Out of scope:** user accounts, identity verification, content moderation, long-term archival storage, legal/estate planning services.

---

## 2. User Roles & Use Cases

### Roles
- **Author:** Creates a secret, sets unlock and expiration times, and retains the edit link.
- **Recipient:** Receives a decrypt link and can retrieve the secret after unlock.

### Primary Use Cases
- **Create Secret:** Author submits text or a file, sets unlock and expiration times, and receives both edit and decrypt links.
- **Update Secret:** Author uses the edit link to modify the ciphertext and/or push the unlock time forward.
- **Attempt Early Retrieval:** Recipient visits decrypt link before unlock and is shown the scheduled unlock time only.
- **Retrieve Secret:** Recipient visits decrypt link after unlock and receives ciphertext for client-side decryption.
- **One-Time Access:** Ciphertext is deleted after first successful post-unlock retrieval or upon expiration.

---

## 3. Functional Requirements

- **FR1:** Allow authors to submit text or files and specify unlock and expiration times.
- **FR2:** Generate two opaque, unguessable tokens per secret: an edit token and a decrypt token.
- **FR3:** Edit token permits updating ciphertext and/or unlock time prior to unlock.
- **FR4:** Decrypt token permits retrieval of ciphertext only after unlock.
- **FR5:** Server enforces unlock time and never serves ciphertext before the unlock timestamp.
- **FR6:** Ciphertext deleted after first post-unlock retrieval or upon expiration.
- **FR7:** Server shall not store, log, or transmit plaintext secrets or decryption keys.
- **FR8:** Secret creation requires either proof-of-work or a one-time paid capability token.

---

## 4. Non-Functional Requirements

- **Security:** Client-side encryption (AES-256-GCM); HTTPS only.
- **Reliability:** Server-authoritative unlock time enforcement.
- **Usability:** Clear UX around unlock/expiration times, one-time access, and link loss.
- **Scalability:** Stateless APIs with rate limiting.
- **Privacy:** No accounts; minimal metadata; ephemeral IP handling.
- **Abuse Resistance:** Computational and economic friction without identity.

---

## 5. Cryptographic Model

- Keys generated client-side.
- AES-256-GCM encryption.
- Keys never transmitted to server.
- Decryption keys conveyed via URL fragments or out-of-band.
- Server stores only ciphertext and hashed tokens.

---

## 6. Abuse Prevention

### Proof-of-Work
- Server issues nonce, difficulty, and expiry.
- Client solves SHA256(nonce || counter || payload_hash).
- Challenges are single-use and time-limited.
- Difficulty may scale by size, duration, or request rate.

### Economic Friction
- Optional one-time payments for large files or extended durations.
- Payment yields a single-use capability token.

### Hard Limits
- Max file size.
- Max time until expiration.
- Mandatory expiration.

---

## 7. Threat Analysis & Mitigations

### Infrastructure Abuse
- Mitigated by size limits, duration caps, PoW, and rate limiting.

### Automated Attacks
- Mitigated by PoW, nonce binding, and single-use challenges.

### Early Disclosure
- Prevented by server-enforced unlock time and server-authoritative clock.

### Confidentiality Breach
- Client-side encryption prevents plaintext exposure even on DB compromise.

### Replay & Reuse
- One-time retrieval; first-access-wins semantics.

### Malicious Content Hosting
- System unsuitability via limits, ephemerality, and no discovery.

### Accepted Residual Risks
- Server could violate unlock time.
- Link sharing.
- Client compromise.
- Coercion.

---

## 8. Design Principles

- Capability-based access
- Zero-knowledge storage
- Minimal retention
- Anonymous usage
- Friction over identity

---

## 9. Summary

InTheEventOfMyDeath.com is a privacy-preserving, abuse-resistant, zero-knowledge system for time-locked secret release. It emphasizes transparency of trust boundaries, simplicity, and harm reduction over absolute control.
