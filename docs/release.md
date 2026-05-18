# Release Setup

This file records the manual release setup that cannot be completed from the repository alone.

## PyPI Trusted Publisher

Create a pending publisher at:

```text
https://pypi.org/manage/account/publishing/
```

Use these values:

- PyPI Project Name: `video-capture-mcp`
- Owner: `Corvus400`
- Repository name: `video-capture-mcp`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Then create the GitHub Environment named `pypi` in repository settings. Required reviewers may be enabled there before the first release.

The publish workflow uses GitHub OIDC and does not require a PyPI API token.

## Homebrew Tap

Create the tap repository:

```text
Corvus400/homebrew-video-capture-mcp
```

The tap name used by users is:

```text
Corvus400/video-capture-mcp
```

The tap repository owns:

- `Formula/video-capture-mcp.rb`
- `.github/workflows/update-formula.yml`
- `scripts/generate_formula.py`

The formula installs a small wrapper that runs `uvx video-capture-mcp==<version>`,
depends on `uv` and `ffmpeg`, and exposes `bin/video-capture-mcp`.

## Homebrew Dispatch Secret

Add a fine-grained PAT to this repository:

```text
HOMEBREW_TAP_TOKEN
```

Token scope:

- Repository: `Corvus400/homebrew-video-capture-mcp`
- Contents: read and write
- Pull requests: read and write

The main repository workflow `.github/workflows/update-homebrew.yml` dispatches
the tap repository workflow after the package is visible on PyPI, waits for the
tap workflow, and fails if the tap update fails.

## Release PR Checks

Release Please opens release PRs with the repository `GITHUB_TOKEN`, which does
not reliably trigger `pull_request` checks for the generated release branch.
The main repository workflow `.github/workflows/release-please.yml` uses
`scripts/release_coordinator.py` to dispatch `.github/workflows/ci.yml` for the
open release PR branch and mirror the stable `ci-gate` status onto the release
branch SHA.

Keep `workflow_dispatch` enabled on `ci.yml`, and keep branch protection focused
on the stable `ci-gate` context. The individual CI jobs may change names or
matrix dimensions, but release PR branch protection should not depend on those
implementation details.

## Publish Coordination

GitHub Releases created by `release-please` with `GITHUB_TOKEN` do not reliably
start `release` event workflows. After a release commit is pushed to `main`,
`.github/workflows/release-please.yml` asks `scripts/release_coordinator.py` to:

1. Find the GitHub Release targeting the current commit SHA.
2. Dispatch `publish.yml` on the release tag unless the version is already on
   PyPI.
3. Wait until the PyPI version JSON is visible.
4. Dispatch `update-homebrew.yml` and wait for the tap repository workflow.

This keeps PyPI and Homebrew updates in one observable release pipeline instead
of relying on follow-up manual dispatches.
