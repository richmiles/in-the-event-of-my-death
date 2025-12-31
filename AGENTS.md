# AGENTS.md - Instructions for coding agents

This repo is a small monorepo:
- `frontend/`: React 19 + TypeScript + Vite
- `backend/`: FastAPI + SQLAlchemy + Alembic (SQLite for local dev via `DATABASE_URL`)

## First question to ask (before coding)
If the user didn’t provide an issue number/link, ask whether to create one first. Every meaningful change should trace back to a GitHub issue.

## Day-to-day commands (prefer Make)
- Install deps: `make install`
- Run dev: `make dev` (backend `:8000`, frontend `:5173`)
- Migrations: `make migrate`
- Checks (must pass before PR): `make check`

## Repository conventions
- Frontend pages live in `frontend/src/pages/` and should follow existing component patterns.
- Backend layering is `routers/` → `services/` → `models/` (+ `schemas/` for Pydantic).
- Add/update tests for new behavior:
  - Backend: `backend/tests/` (unit + integration style tests)
  - Frontend: `vitest` via `npm run test` (wired through `make test`)
- Do not leave `console.log` / `print` debugging in commits.

## Security / privacy invariants (do not violate)
- Zero-knowledge: encryption/decryption happens client-side; never send keys or plaintext to the server.
- Decryption keys are carried in the URL fragment; the server must never need or log them.
- Avoid logging sensitive request bodies or ciphertext; keep telemetry minimal.
- Be conservative changing cryptography (`frontend/src/services/crypto.ts`); prefer small, well-reviewed edits with tests.

## Branch + commit expectations (when doing repo work)
- Branch naming:
  - Feature: `feature/<issue-number>-short-description`
  - Fix: `fix/<issue-number>-short-description`
  - Docs: `docs/<description>`
- Commit messages: `<type>: <description>` (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`)
- PRs should reference the issue (e.g., “Closes #123”) and `make check` must pass.

## When adding dependencies
Avoid new dependencies unless necessary; prefer built-ins and existing libs. If a new dependency is required, explain why and update lockfiles (`backend/poetry.lock` or `frontend/package-lock.json`) intentionally.

