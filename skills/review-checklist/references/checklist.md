# Review Checklist Prompts

Use these prompts selectively—aim for 1–3 per category based on risk.

## Code Style & Maintainability
- Any patterns diverging from repo conventions (naming, file placement, layering)?
- Comments explain why not what; any comments referencing removed behavior?
- Duplicate flows/components that should be consolidated?
- Utilities with hidden side effects or surprising behavior?

## Tests & Coverage Quality
- Do tests assert outcomes beyond “no crash”?
- Any asserts that can never fail (tautologies)?
- Coverage of critical user journeys and failure modes?
- Are time-dependent tests deterministic (fixed clocks, seeded randomness)?

## Technical Debt Signals
- “Temporary” TODOs still unresolved?
- Partially deprecated APIs or data shapes still in use?
- Code only serving legacy UI paths that could be removed?

## Dependencies & Versions
- Lockfiles aligned with declared versions?
- Unused dependencies/imports?
- Known advisories affecting current versions (esp. crypto/server/HTTP libs)?

## Deployment & Images
- Are container/base images rebuilt when their bases move?
- Deploy config matches environment vars and ports?
- Any stale build args/env vars lingering?

## Security & Privacy
- Sensitive data ever logged (request bodies, secrets, tokens)?
- Security invariants intact (e.g., URL fragments not sent, zero-knowledge handling)?
- Crypto changes isolated and well-tested?
- Rate limits/PoW/cleanup behavior consistent with docs?

## Documentation & Product Truth
- Docs match actual behavior (unlock vs. expiry, edit capabilities)?
- UX copy promises align with backend behavior (deletion semantics, retention)?

## Observability & Ops
- Logging minimal but actionable (errors with context, no secrets)?
- Background jobs or async tasks surfacing failures vs. silently dropping?

## Schema & Data Lifecycle
- Migrations exhaustive and reversible? Data migrations safe?
- Data retention/clearing matches policy and code?

## Frontend UX Consistency
- Multiple entry points produce the same outcomes (e.g., `/` vs `/create`)?
- Validation rules consistent with backend constraints?
