# Security Policy

## Reporting a Vulnerability
If you discover a security vulnerability, please open a private GitHub security advisory instead of filing a public issue. Include reproduction steps, impact, and any suggested mitigations. We will respond as quickly as possible.

## Supported Versions
Security fixes target the latest `main` branch. Older revisions may not receive patches.

## Cryptography and secrets
- The service is designed for client-side encryption; the server should never receive plaintext or decryption keys.
- Do not commit secrets or `.env` files. Use the provided `.env.example` templates and set real values locally.

Thank you for helping keep users safe.
