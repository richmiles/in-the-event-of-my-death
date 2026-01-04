# Smoke Tests

This repo uses a lightweight smoke test runner to validate staging/production deployments as a guardrail.

- Runner: `scripts/smoke-test.py`
- Backlog/project: https://github.com/users/richmiles/projects/14

## Running

```bash
./scripts/smoke-test.py https://staging.example.com
./scripts/smoke-test.py https://staging.example.com --health-only
```

## Adding coverage

- Create an issue prefixed with `Smoke:` describing the scenario + acceptance criteria.
- Add the issue to the “IEOMD - Smoke Tests” project.
- Keep checks fast and deterministic (target runtime: <3 minutes) and avoid side effects by default.

