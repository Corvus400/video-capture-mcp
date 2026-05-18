# Development

## Setup

```bash
git clone https://github.com/Corvus400/video-capture-mcp.git
cd video-capture-mcp
bash install.sh
```

The installer creates `.venv`, installs the package editable with test dependencies, and prints local MCP registration snippets.

## From-Source Wrapper

`bin/video-capture-mcp` is a development wrapper. It runs:

```bash
exec .venv/bin/python -m video_capture_mcp.server
```

Published installs use the `video-capture-mcp` console script generated from `pyproject.toml`.

## Tests

```bash
./.venv/bin/python -m pytest tests/ -v
```

Focused examples:

```bash
./.venv/bin/python -m pytest tests/test_session.py -v
./.venv/bin/python -m pytest tests/test_extractor.py -v
```

## Lint

Install development dependencies, then run pre-commit:

```bash
./.venv/bin/python -m pip install -e ".[dev,test]"
pre-commit run --all-files
```

## Build

```bash
python3 -m build --sdist --wheel
ls dist/
```

Verify the wheel with `uvx`:

```bash
uvx --from ./dist/video_capture_mcp-0.1.1-py3-none-any.whl video-capture-mcp < /dev/null
```

## MCP Smoke Test

MCP tool listing requires initialization before `tools/list`:

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | ./.venv/bin/python -m video_capture_mcp.server
```

For a local macOS manual-recording smoke test, start a macOS or app-window
recording without `duration_seconds`, perform a short UI action, then call
`stop_recording` and confirm the result reports `file_exists=true` and a
non-zero `file_size_bytes`. Write smoke-test videos outside the repository, for
example under `/private/tmp`.

## Release Checks

Before release, run:

```bash
./.venv/bin/python -m pytest tests/ -v
python3 -m build --sdist --wheel
uvx --from ./dist/video_capture_mcp-0.1.1-py3-none-any.whl video-capture-mcp < /dev/null
```
