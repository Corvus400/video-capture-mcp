# Tools

All tools are exposed by the FastMCP server named `video_capture`.

## `start_recording`

Start a recording session.

Parameters:

- `target`: `macos`, `ios_simulator`, `ios`, `ios-simulator`, `simulator`, `mac`, `desktop`, or `android`.
- `duration_seconds`: optional for macOS, iOS Simulator, and Android. Omit it when the agent should explicitly stop recording after operating the UI.
- `output_path`: optional local video path. If omitted, the server uses `VIDEO_CAPTURE_MCP_OUTPUT_DIR` or the system temp directory.
- `options`: backend-specific options.

Common options:

- `orientation`: `portrait` or `landscape`; normalizes the final video on stop.
- `rotate_degrees`: `0`, `90`, `180`, or `270`; explicit post-recording rotation.

macOS options:

- `region`: dict `{ "x": int, "y": int, "width": int, "height": int }` or four-item list.
- `display`: display id passed to `screencapture -D`.
- `include_cursor`: include the pointer in macOS recordings.
- `include_clicks`: include clicks in the recording.
- `include_audio`: include audio in the recording.

iOS Simulator options:

- `device` or `udid`: Simulator UDID. Defaults to `booted`.
- `display`: `internal` or `external`.
- Different Simulator UDIDs can be recorded at the same time.

Android options:

- `serial`: adb serial.
- `size`: `WIDTHxHEIGHT`, `{ "width": int, "height": int }`, or `[width, height]`.
- `bit_rate`: integer bit rate for `adb shell screenrecord`.
- Different adb serials can be recorded at the same time.

Example:

```json
{
  "target": "android",
  "duration_seconds": 5,
  "options": {
    "serial": "emulator-5554",
    "size": "1280x720",
    "orientation": "landscape"
  }
}
```

Returns:

```json
{
  "session_id": "...",
  "video_path": "...",
  "mode": "manual_stop"
}
```

## `stop_recording`

Stop a running session.

Parameters:

- `session_id`: id returned by `start_recording`.

Returns the final local `video_path`, elapsed duration, backend exit code, and orientation result. Android sessions also include remote pull and cleanup exit codes.
All targets include `file_exists` and `file_size_bytes` so agents can detect empty or missing recordings before analyzing frames.

## `stop_all_recordings`

Stop all running sessions for the current MCP server.

Parameters:

- `target`: optional target filter. Accepts the same target aliases as `start_recording`.

Returns:

```json
{
  "stopped": []
}
```

Use this when a client lost a `session_id`, when duplicate-target protection reports an active session that should be cleared, or before starting a new demo capture.

## `start_app_window_recording`

Record only the visible front-window region of a macOS app.

Parameters:

- `app_name`: macOS application name, for example `Google Chrome`.
- `duration_seconds`: optional scheduled recording length. Omit it to record until `stop_recording`.
- `output_path`: optional local `.mov` path.
- `padding`: optional region padding.
- `min_visible_ratio`: required visible ratio, default `0.8`.
- `options`: extra macOS recording options.

The tool activates the app, checks visible window bounds, and records using a `screencapture -R` region. If the window is not sufficiently visible, it returns an error object and does not start recording.

For agent-driven UI verification, prefer omitting `duration_seconds`: start recording, operate the app with Computer Use or another UI tool, then call `stop_recording` with the returned `session_id`.

## `get_window_region`

Activate and measure a macOS app's front-window visibility.

Parameters:

- `app_name`: macOS application name.
- `padding`: optional region padding.
- `min_visible_ratio`: value greater than `0` and less than or equal to `1`.
- `activate`: whether to activate the app first.

Returns window bounds, desktop bounds, visible bounds, visible ratio, and a recording `region`.

## `hover_sequence`

Move the macOS pointer through multiple points without clicking.

Parameters:

- `points`: list of `{ "x": number, "y": number }` objects or `[x, y]` pairs.
- `hold_seconds`: delay after each point.
- `app_name`: optional app to activate before movement.
- `steps_per_segment`: interpolation steps between points.
- `step_delay_seconds`: delay between interpolation steps.

Returns normalized points and `moved_count`. When `app_name` is passed, the return value includes `active_window`.

## `move_pointer`

Move the macOS pointer once without clicking.

Parameters:

- `x`: screen x coordinate.
- `y`: screen y coordinate.

Returns the normalized numeric coordinates.

## `extract_frames`

Extract PNG frames from a video.

Parameters:

- `video_path`: input video path.
- `output_dir`: frame output directory.
- `mode`: `scene` or `fixed_fps`.
- `scene_threshold`: ffmpeg scene threshold for `scene` mode.
- `fps`: extraction rate for `fixed_fps` mode.
- `max_frames`: maximum returned frames.
- `inline_images`: return FastMCP `Image` objects when true.
- `rotate_degrees`: optional frame rotation, one of `0`, `90`, `180`, or `270`.

Returns:

```json
{
  "images": [],
  "frame_paths": [".../frame_0001.png"],
  "dropped_for_max": 0
}
```

## `record_and_extract`

Record for a fixed duration and extract frames in one call.

Parameters:

- `target`: recording target.
- `duration_seconds`: fixed recording duration.
- `output_dir`: directory for `recording.mov` or `recording.mp4` and `frames/`.
- `options`: forwarded to `start_recording`.
- `extract_options`: forwarded to `extract_frames`.

Returns the `extract_frames` result plus `video_path` and the stop-recording result under `recording`.

## `list_active_sessions`

List active recording sessions.

Parameters: none.

Returns:

```json
{
  "sessions": []
}
```

## `cleanup_stale_processes`

Clean up recording processes left by a dead previous server process.

Parameters: none.

The server also calls this before starting a recording. It only acts on registry files owned by the current OS user.
