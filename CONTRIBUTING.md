# Contributing

Thanks for helping improve video-capture-mcp.

## Development Setup

```bash
git clone https://github.com/Corvus400/video-capture-mcp.git
cd video-capture-mcp
bash install.sh
```

## Tests

Run the test suite before opening a pull request:

```bash
./.venv/bin/python -m pytest tests/ -v
```

Run linting and formatting hooks when configured:

```bash
pre-commit run --all-files
```

## Commits

Use Conventional Commits:

- `feat:` for user-visible features.
- `fix:` for bug fixes.
- `docs:` for documentation changes.
- `test:` for test-only changes.
- `build:` or `ci:` for packaging and automation.
- `chore:` for maintenance.

Release notes and the changelog are generated with release-please.

## Pull Request Checklist

- Tests pass locally.
- Linting passes locally when the tooling is installed.
- Documentation is updated for user-visible behavior.
- Security-sensitive changes include tests or a clear verification note.
- Breaking changes are called out explicitly.
