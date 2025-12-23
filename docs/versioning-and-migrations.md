# Versioning and database migrations

This repository uses a single, repo-wide version and Alembic migrations for schema changes.

## Versioning policy

- Version scheme: Semantic Versioning (SemVer), including pre-release labels when needed (e.g. `0.1.0-beta`).
- Release tags: tag releases as `vX.Y.Z` (or `vX.Y.Z-beta`), matching the repo-wide version.
- Source of truth: keep these files in sync:
  - `backend/pyproject.toml` (`[tool.poetry].version`)
  - `backend/app/main.py` (`FastAPI(..., version=...)`)
  - `frontend/package.json` (`version`)

The frontend UI displays the version subtly in the footer via `__APP_VERSION__`, which is injected at build time from `frontend/package.json` in `frontend/vite.config.ts`.

## Database migrations (SQLite in production, v0)

### Principles

- Schema changes happen via Alembic migrations only.
- Production migrations are an explicit, serialized step.
- For SQLite, the rollback strategy is to restore from a pre-migration backup of the database file.

### Production migration workflow (maintenance window)

Assuming `DATABASE_URL=sqlite:////path/to/secrets.db` (a persistent path on disk):

1. Stop the backend (or place it in maintenance mode).
2. Backup the database file.
3. Run migrations: `cd backend && poetry run alembic upgrade head`
4. Start the backend and verify health.

Suggested backup procedure:

- Copy the database file with a timestamp (keep at least the most recent few).
- Optionally run an integrity check:
  - `sqlite3 /path/to/secrets.db "PRAGMA integrity_check;"`

### Migration testing

- Migrations are validated by running `alembic upgrade head` against a fresh SQLite database in backend tests.
- Run locally with `make test` or `make check`.

## Plan to migrate to Postgres (future)

SQLite is a good low-cost starting point for a single-instance deployment, but zero-downtime deploys and horizontal scaling typically require Postgres.

High-level migration plan:

1. Provision a Postgres database and set `DATABASE_URL` accordingly.
2. Run `alembic upgrade head` against Postgres (schema created from migrations).
3. Copy data from SQLite to Postgres during a maintenance window.
4. Switch the backend to Postgres and verify behavior.

## Path to zero downtime (future)

To support zero-downtime releases:

- Use "expand/contract" migrations:
  - Expand: add new nullable columns / new tables first.
  - Deploy code that supports both old and new schema.
  - Contract: remove old columns/constraints in a later release.
- Run migrations as a separate one-off job (only once per release), then roll application instances.

