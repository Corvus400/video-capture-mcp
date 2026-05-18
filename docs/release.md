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

The formula should install the PyPI sdist with Homebrew's Python virtualenv helpers, depend on `python@3.12` and `ffmpeg`, and expose `bin/video-capture-mcp`.

## Homebrew Dispatch Secret

Add a fine-grained PAT to this repository:

```text
HOMEBREW_TAP_TOKEN
```

Token scope:

- Repository: `Corvus400/homebrew-video-capture-mcp`
- Contents: read and write

The main repository workflow `.github/workflows/update-homebrew.yml` dispatches the tap repository workflow after a GitHub Release is published.

## Release PR Checks

Release Please opens release PRs with the repository `GITHUB_TOKEN`, which does
not reliably trigger `pull_request` checks for the generated release branch.
The main repository workflow `.github/workflows/release-please.yml` dispatches
`.github/workflows/ci.yml` for the open release PR branch after the release PR is
created. Keep `workflow_dispatch` enabled on `ci.yml`; otherwise release PRs can
remain blocked with no required checks reported.
