# Contributing

Thanks for your interest in contributing to Google Ads MCP Server!

## Development Setup

1. Install [uv](https://docs.astral.sh/uv/) and Python 3.12+
2. Clone the repo and install dependencies:

```bash
git clone https://github.com/bertramdev/GoogleAdsMCP.git
cd GoogleAdsMCP
uv sync
```

3. Copy `.env.example` to `.env` and fill in your Google Ads API credentials.

## Running Tests

```bash
uv run pytest
```

Note: Write tools are not tested against live accounts in CI. Read-only tools have been validated against the live Google Ads API v23.

## Code Style

- Type hints on all public functions
- Google-style docstrings
- Format with Black, sort imports with isort

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or updating tests
- `chore:` — maintenance tasks

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes with tests where applicable
3. Ensure `uv run pytest` passes
4. Submit a PR with a clear description of the change
