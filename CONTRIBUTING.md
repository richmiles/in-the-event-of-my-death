# Contributing

Thanks for your interest in improving InTheEventOfMyDeath.com! This project welcomes issues and pull requests from the community.

## How to contribute
- **Report bugs**: Open a GitHub issue with steps to reproduce, expected vs. actual behavior, and environment details.
- **Propose features**: Start with an issue to discuss scope and alignment before opening a PR.
- **Submit pull requests**: Fork the repo, create a feature branch, and open a PR with a clear description of the change.

## Development setup
1. Clone the repository and install dependencies (`make install`), as described in `README.md`.
2. Copy `.env.example` files for backend and frontend and adjust values for your environment.
3. Run `make dev` to start backend and frontend in development mode.

## Coding guidelines
- Follow the existing automated style:
  - Backend: Ruff (`make lint`, `make format`)
  - Frontend: ESLint + Prettier (`make lint`, `make format`)
- Add or update tests where meaningful (`make test` runs both backend + frontend tests).
- Run `make check` before opening a PR (lint + format check + typecheck + tests).
- Keep changes focused and well-scoped; large refactors should be discussed first.
- Don’t leave debugging output in commits (e.g., `console.log`, `print`).

## Maintainer workflow (this repo)
For maintainers (and anyone who wants to follow the project’s preferred workflow), see `CLAUDE.md` for:
- Issue-first development (every meaningful change traces back to an issue)
- Branch naming conventions
- Commit message conventions
- PR expectations (including referencing the issue and ensuring `make check` passes)

## Commit and PR checklist
- Include context in the PR description: what changed and why.
- Note any breaking changes or migration steps.
- Confirm linters and tests pass locally.

## Communication
Questions or clarifications? Open an issue or start a discussion on GitHub so others can benefit from the answers.
