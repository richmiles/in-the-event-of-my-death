# AGENTS.md - Instructions for coding agents

This repo is a small monorepo:
- `frontend/`: React 19 + TypeScript + Vite
- `backend/`: FastAPI + SQLAlchemy + Alembic (SQLite for local dev via `DATABASE_URL`)

## Before Starting Work (REQUIRED)
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
     - **#12** - IEOMD - Infrastructure (ongoing DevOps, monitoring, tooling)

3. **Create a branch for the issue**
   - Use: `gh issue develop <issue-number> --checkout`
   - Or manually: `git checkout -b <type>/<issue-number>-short-description main`
   - If already on a branch for the issue, proceed without checkout

**If the user requests work without an issue number, ask them to confirm issue creation before proceeding.**

## Day-to-day commands (prefer Make)
- Install deps: `make install`
- Run dev: `make dev` (backend `:8000`, frontend `:5173`)
- Migrations: `make migrate`
- Tests: `make test`
- Lint/format/typecheck: `make lint`, `make format`, `make typecheck`
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

## Available CLI Tools
These CLIs are authenticated and available:
- **`gh`** - GitHub CLI for issues, PRs, workflows, projects, and API calls
- **`doctl`** - DigitalOcean CLI for droplet management and infrastructure
- **`ssh`** - Direct server access via `ssh root@<ip>` (root is intentional; get IPs from `doctl compute droplet list`)

---

## Parallel Development with Git Worktrees

Multiple Claude Code sessions can work on independent issues simultaneously using git worktrees.

### When to Use Parallel Agents

**Good candidates:**
- Frontend-only vs backend-only changes
- Independent features with no shared files
- Documentation updates alongside code changes

**Avoid parallel work when:**
- Both issues modify the same files
- One issue depends on changes from another
- Changes affect shared configuration (package.json, pyproject.toml)

### Setup

```bash
# Create worktree for an issue
git worktree add ../ieomd-<issue-number> -b feature/<issue-number>-<description>

# Example: working on issue #64
git worktree add ../ieomd-64 -b feature/64-file-uploads

# Start Claude Code session in that worktree
cd ../ieomd-64 && claude
```

### Running Multiple Dev Servers

Each worktree needs different ports:

| Worktree | Frontend | Backend | Command |
|----------|----------|---------|---------|
| Main | 5173 | 8000 | `make dev` |
| Worktree 2 | 5174 | 8001 | `VITE_PORT=5174 BACKEND_PORT=8001 make dev` |
| Worktree 3 | 5175 | 8002 | `VITE_PORT=5175 BACKEND_PORT=8002 make dev` |

### Subsystem Independence Map

| Subsystem | Key Files | Safe to Parallelize With |
|-----------|-----------|--------------------------|
| Frontend UI | `frontend/src/pages/*`, `frontend/src/components/*` | Backend API, Database |
| Frontend Services | `frontend/src/services/*` | Backend (if API unchanged) |
| Backend API | `backend/app/routers/*` | Frontend (if contracts stable) |
| Backend Services | `backend/app/services/*` | Frontend, Database migrations |
| Database | `backend/app/models/*`, `backend/alembic/*` | Frontend |
| Infrastructure | `Makefile`, `docker-compose.yml` | Nothing (serialize these) |
| Docs | `docs/*`, `*.md` | Everything |

### Cleanup After Merge

```bash
git worktree remove ../ieomd-<issue-number>
git worktree prune
```

### Coordination Guidelines

1. **Check for conflicts before starting** - Review which files each issue will touch
2. **Merge sequentially** - Don't merge PRs simultaneously; let CI run between merges
3. **Rebase after conflicts** - If main updates, rebase your branch before continuing
