# CLAUDE.md - Project Instructions for Claude Code

## Project Overview
"In The Event Of My Death" - A zero-knowledge, time-locked secret delivery service.
- Frontend: React 19 + TypeScript + Vite
- Backend: Python FastAPI + SQLAlchemy + SQLite
- Encryption: AES-256-GCM (client-side)

## Development Commands
- `make dev` - Run both frontend and backend
- `make test` - Run all tests (backend + frontend)
- `make lint` - Lint both frontend and backend
- `make format` - Format code
- `make typecheck` - TypeScript type checking
- `make check` - Run all checks (lint, format, typecheck, test)

## Architecture Notes
- Zero-knowledge: encryption keys are never sent to server (stored in URL fragment)
- Secrets have `unlock_at` (when viewable) and `expires_at` (when auto-deleted)
- Proof-of-work protects against spam

## Key Files
- `frontend/src/pages/Home.tsx` - Main secret creation form
- `frontend/src/services/crypto.ts` - Client-side encryption
- `backend/app/models/secret.py` - Secret database model
- `backend/app/services/secret_service.py` - Secret business logic

## Code Conventions
- Use existing patterns when adding features
- Keep page components in `frontend/src/pages/`
- Backend follows FastAPI patterns: routers → services → models
- Run `make check` before committing

## Environment Variables
- Frontend: `VITE_API_URL`, `VITE_BASE_URL`
- Backend: `DATABASE_URL`, `CORS_ORIGINS`

---

## Workflow

### Before Starting Work (REQUIRED)
**STOP: Do not write any code until these steps are complete.**

1. **Verify a GitHub issue exists** for the task
   - If no issue exists, create one: `gh issue create --title "<title>" --body "<description>"`
   - Every change must trace back to an issue

2. **Link the issue to the appropriate GitHub project**
   - `gh project item-add <project-number> --owner richmiles --url <issue-url>`
   - Active projects:
     - **#8** - IEOMD v0.2 - Payment Infrastructure (capability tokens, Lightning)
     - **#9** - IEOMD v0.3 - Premium Features (file uploads, edit content)
     - **#11** - IEOMD - UX Enhancements (link ordering, defaults, sharing)

3. **Create a branch for the issue**
   - Use: `gh issue develop <issue-number> --checkout`
   - Or manually: `git checkout -b <type>/<issue-number>-short-description main`

**If the user requests work without an issue number, ask them to confirm issue creation before proceeding.**

### Branch Naming
- Feature: `feature/<issue-number>-short-description` (e.g., `feature/5-expiry-backend`)
- Fix: `fix/<issue-number>-short-description`
- Docs: `docs/<description>`

### Commit Messages
Format: `<type>: <description>`

Types:
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code refactoring
- `docs` - Documentation
- `test` - Adding/updating tests
- `chore` - Maintenance tasks

Example: `feat: add expires_at column to secrets model`

### Pull Request Process
1. Create branch from `main`
2. Make changes, commit with conventional messages
3. Run `make check` - all checks must pass
4. Create PR referencing the issue: "Closes #5"
5. PR title should match the issue title

### Testing Requirements
- Backend: Add/update tests in `backend/tests/` for any new functionality
- Run `make test` before submitting PR
- New API endpoints need integration tests
- New service functions need unit tests

### Before Submitting
Checklist:
- [ ] `make check` passes
- [ ] Tests added/updated for new functionality
- [ ] No console.log or print statements left in code
- [ ] Environment variables documented if added
