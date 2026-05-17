# macOS Permissions

`video-capture-mcp` launches native recording and pointer APIs from the process that starts the MCP server. macOS grants Screen Recording and Accessibility permission to that launcher, not to the repository.

## Screen Recording

Required for:

- `start_recording` with `target="macos"`
- `start_app_window_recording`

Open System Settings > Privacy & Security > Screen Recording, then add the executable that starts the MCP server.

For macOS 14, 15, and 26, the flow is the same:

1. Open System Settings.
2. Go to Privacy & Security.
3. Open Screen Recording.
4. Add or enable the launcher process.
5. Fully restart the MCP client after changing the permission.

Install-route guidance:

- `uvx`: add the Python interpreter used by `uvx`. Run `uvx --from video-capture-mcp python -c "import sys; print(sys.executable)"` if you need to inspect the environment.
- `pip`: add the Python interpreter or console script environment where `video-capture-mcp` is installed. `python -c "import sys; print(sys.executable)"` prints the interpreter path.
- Homebrew: add the `video-capture-mcp` executable reported by `which video-capture-mcp`.
- From source: add `.venv/bin/python` from the cloned checkout.

## Accessibility

Required for:

- `move_pointer`
- `hover_sequence`

Open System Settings > Privacy & Security > Accessibility and add the same launcher process used for the MCP server.

## Backend Notes

- iOS Simulator recording uses `xcrun simctl io ... recordVideo`. It does not require Screen Recording, but it requires Xcode Command Line Tools and a booted Simulator.
- Android recording uses `adb shell screenrecord`. It does not require Screen Recording, but it requires an authorized device.
- `extract_frames` and orientation normalization use `ffmpeg` and `ffprobe`; they need filesystem access to the input video and output directory.

## Checking the Permission Target

For `pip` or source installs:

```bash
python -c "import sys; print(sys.executable)"
```

For Homebrew installs:

```bash
which video-capture-mcp
```

After changing permissions, restart the MCP client process so macOS reloads the TCC decision.
