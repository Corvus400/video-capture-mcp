# video-capture-mcp

MCP server for autonomous screen recording and frame extraction on macOS,
iOS Simulator, and Android.

The server records a target screen, stops the recording cleanly, optionally
normalizes video orientation, and extracts key frames so MCP clients can inspect
short UI transitions.

## Requirements

- macOS
- Python >=3.11,<3.13 for installation. The installer prefers `python3.11`
  when available and otherwise uses `python3`; set `PYTHON_BIN` to override.
- `ffmpeg` and `ffprobe` for frame extraction and orientation normalization
- Xcode command line tools for iOS Simulator recording
- Android platform tools for Android recording

## Install

```bash
uvx video-capture-mcp
# or
pip install video-capture-mcp
# or
brew install Corvus400/tap/video-capture-mcp
```

For local development from a cloned checkout, run `bash install.sh`.

## MCP Registration

Claude Code:

```bash
claude mcp add --scope user --transport stdio video_capture -- uvx video-capture-mcp
```

Codex `~/.codex/config.toml`:

```toml
[mcp_servers.video_capture]
command = "uvx"
args = ["video-capture-mcp"]
```

## Runtime Behavior

The MCP server must be launched with the OS permissions required by the target
backend. iOS Simulator recording needs access to CoreSimulatorService, Android
recording needs access to `adb`, and macOS recording needs Screen Recording
permission for the Python binary that runs this package.

The server also keeps a small per-process registry under
`~/Library/Caches/video-capture-mcp/sessions`. On startup it removes stale
records from dead previous server processes and attempts to stop only the
recording processes it previously started. On normal server shutdown it stops
active sessions and clears its own registry file.

## macOS Screen Recording Permission

For macOS desktop recording, add the venv Python binary to:

System Settings > Privacy & Security > Screen Recording

Path:

```text
$(python -c 'import sys; print(sys.executable)')
```

iOS Simulator and Android recording do not use macOS Screen Recording.

## Tools

### `start_recording`

Arguments:

- `target`: `macos`, `ios_simulator`, or `android`
- `duration_seconds`: required for `macos`; optional for iOS/Android
- `output_path`: optional local video path
- `options`: backend options

Common options:

- `orientation`: `portrait` or `landscape`; normalizes the final video if the
  recorded dimensions do not match
- `rotate_degrees`: explicit post-recording rotation, one of `0`, `90`, `180`,
  or `270`

iOS options:

- `device` or `udid`: Simulator UDID. Use this when multiple Simulators are
  booted.
- `display`: `internal` or `external`

Android options:

- `serial`: adb serial. Use this when multiple Android devices are connected.
- `size`: screenrecord size, for example `1280x720`
- `bit_rate`: screenrecord bit rate

### `stop_recording`

Stops a running recording session.

- iOS Simulator: sends SIGINT to `xcrun simctl ... recordVideo`
- Android: sends SIGINT to the remote `screenrecord` process with
  `adb shell pkill -2 screenrecord`, waits, pulls the mp4, then removes the
  remote file
- macOS: waits for the scheduled `screencapture -V` recording to finish

### `list_active_sessions`

Returns active session metadata.

### `move_pointer`

Moves the macOS pointer without clicking.

Arguments:

- `x`: macOS screen x coordinate
- `y`: macOS screen y coordinate

### `hover_sequence`

Moves the macOS pointer through multiple points without clicking. Use this when
recording hover-only desktop behavior that must not trigger a mouse click.

Arguments:

- `points`: list of `{"x": number, "y": number}` objects or `[x, y]` pairs
- `hold_seconds`: delay after each point, default `0.5`
- `app_name`: optional macOS application name to activate before moving
- `steps_per_segment`: interpolated mouse-move steps between points, default
  `12`
- `step_delay_seconds`: delay between interpolated steps, default `0.02`

### `get_window_region`

Activates a macOS app and returns its visible front-window region. Use this as a
preflight before recording app-specific desktop behavior.

Arguments:

- `app_name`: macOS application name, for example `Google Chrome`
- `padding`: optional region padding in screen coordinates
- `min_visible_ratio`: required visible ratio, default `0.8`
- `activate`: activate the app before checking bounds, default `true`

### `start_app_window_recording`

Starts macOS recording for only the visible front-window region of a target app.
This is the preferred tool for browser or desktop-app debugging because it
activates the target app and avoids recording unrelated screens.

Arguments:

- `app_name`: macOS application name, for example `Google Chrome`
- `duration_seconds`: scheduled recording length
- `output_path`: optional local `.mov` path
- `padding`: optional region padding in screen coordinates
- `min_visible_ratio`: required visible ratio, default `0.8`
- `options`: extra macOS recording options

### `extract_frames`

Extracts PNG frames from a video.

Modes:

- `scene`: `select='gt(scene,T)',showinfo` with `-vsync vfr`
- `fixed_fps`: fixed interval extraction with `fps=<n>`

Options:

- `max_frames`: caps frames and drops extra frames by even sampling
- `inline_images`: returns FastMCP `Image` objects as well as file paths
- `rotate_degrees`: rotates extracted frames

### `record_and_extract`

Records for a fixed duration and extracts frames in one call.

## Verification

```bash
cd video-capture-mcp
./.venv/bin/python -m pytest tests/test_session.py tests/test_extractor.py -v
```

MCP tool listing requires MCP initialization before `tools/list`:

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | ./.venv/bin/python -m video_capture_mcp.server
```

Orientation verification should include both dimensions:

- portrait video: `height > width`
- landscape video: `width > height`

Observed live outputs during implementation:

- iOS portrait: `1668x2420`
- iOS landscape normalized: `2420x1668`
- Android portrait: `720x1280`
- Android landscape normalized: `1280x720`
