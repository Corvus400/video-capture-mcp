# video-capture-mcp

> macOS, iOS Simulator, and Android screen recording plus key-frame extraction for MCP-aware AI agents.

[![PyPI](https://img.shields.io/pypi/v/video-capture-mcp.svg)](https://pypi.org/project/video-capture-mcp/)
[![CI](https://github.com/Corvus400/video-capture-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Corvus400/video-capture-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11--3.12-blue.svg)](pyproject.toml)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](docs/permissions.md)

`video-capture-mcp` gives AI agents a stdio MCP server for recording UI motion while they operate apps, then extracting frames with ffmpeg. It is designed for bugs and requirements that screenshots miss, such as keyboards opening, hover/unhover states, and transient layout glitches.

## Features

- 3 OS recording backends in one MCP server: macOS, iOS Simulator, and Android.
- App-window-bounded macOS recording with activation and visible-region checks.
- Manual start/stop recording across macOS, iOS Simulator, and Android.
- Hover sequence API for UI demos that need mouse movement without clicks.
- `record_and_extract` for one-shot recording plus ffmpeg key-frame extraction.
- FastMCP `Image` inline responses for extracted frames.

## Requirements

- macOS 12 or newer.
- Python 3.11 or 3.12 for PyPI and `uvx` installs. Homebrew installs its own Python dependency.
- `ffmpeg` and `ffprobe`.
- Xcode Command Line Tools for iOS Simulator recording.
- Android platform-tools and `adb` for Android recording.

## Installation

### Option 1: uvx (zero install) [Recommended]

Claude Code:

```bash
claude mcp add --scope user --transport stdio video_capture -- uvx video-capture-mcp
```

Claude Desktop:

```json
{
  "mcpServers": {
    "video_capture": {
      "command": "uvx",
      "args": ["video-capture-mcp"]
    }
  }
}
```

VS Code / Cursor:

```json
{
  "servers": {
    "video_capture": {
      "type": "stdio",
      "command": "uvx",
      "args": ["video-capture-mcp"]
    }
  }
}
```

Codex:

```toml
[mcp_servers.video_capture]
command = "uvx"
args = ["video-capture-mcp"]
```

Goose:

```bash
goose configure --name video_capture --command "uvx video-capture-mcp"
```

### Option 2: pip

```bash
python3 -m pip install video-capture-mcp
claude mcp add --scope user --transport stdio video_capture -- video-capture-mcp
```

Codex:

```toml
[mcp_servers.video_capture]
command = "video-capture-mcp"
args = []
```

### Option 3: Homebrew

```bash
brew install Corvus400/tap/video-capture-mcp
claude mcp add --scope user --transport stdio video_capture -- video-capture-mcp
```

Codex:

```toml
[mcp_servers.video_capture]
command = "video-capture-mcp"
args = []
```

## macOS Permissions

See [docs/permissions.md](docs/permissions.md) for full details.

- Screen Recording is required for `start_recording target=macos` and `start_app_window_recording`.
- Accessibility is required for `move_pointer` and `hover_sequence`.
- Add the executable that launches the server to System Settings > Privacy & Security. For `uvx` and `pip`, this is usually the Python interpreter for that environment. For Homebrew, it is the installed `video-capture-mcp` executable.

## Quickstart (Claude Code)

1. Install `ffmpeg`.

   ```bash
   brew install ffmpeg
   ```

2. Register the MCP server.

   ```bash
   claude mcp add --scope user --transport stdio video_capture -- uvx video-capture-mcp
   ```

3. Ask Claude Code to start recording a visible app window:

   ```json
   {
     "app_name": "Finder",
     "options": {
       "include_cursor": true
     }
   }
   ```

4. Have the agent operate the UI, then call `mcp__video_capture__stop_recording`
   with the returned `session_id`.

## Tools

| Tool | Purpose | Key args |
| --- | --- | --- |
| `start_recording` | Start recording on selected target | `target`, `duration_seconds`, `options` |
| `stop_recording` | Stop a session and normalize orientation | `session_id` |
| `stop_all_recordings` | Stop active sessions, optionally by target | `target` |
| `start_app_window_recording` | macOS app-window-bounded recording | `app_name`, `duration_seconds`, `options` |
| `get_window_region` | Activate and measure front-window visibility | `app_name`, `min_visible_ratio` |
| `hover_sequence` | Mouse-move sequence without clicks | `points`, `hold_seconds`, `app_name` |
| `move_pointer` | Single mouse-move without click | `x`, `y` |
| `extract_frames` | ffmpeg scene or fixed-fps frame extraction | `video_path`, `mode`, `max_frames` |
| `record_and_extract` | Record and extract in one call | `target`, `duration_seconds`, `output_dir` |
| `list_active_sessions` | List current recordings | none |
| `cleanup_stale_processes` | Reap recordings from dead previous server PIDs | none |

Detailed parameters and option schemas are in [docs/tools.md](docs/tools.md).

## Configuration

- `VIDEO_CAPTURE_MCP_OUTPUT_DIR`: default output root for recordings when `output_path` is omitted. Defaults to the system temp directory under `video-capture-mcp`.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for TCC denial, missing `ffmpeg`, no booted Simulator, and unauthorized adb devices.

## Development

See [docs/development.md](docs/development.md) for clone, local install, tests, linting, package build, and the `bin/video-capture-mcp` from-source wrapper.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities through GitHub Private Security Advisories.

Explicit `output_path` values are treated as trusted MCP client input. Use MCP client approvals and filesystem policy to control where agents may write.

## License

MIT. See [LICENSE](LICENSE).
