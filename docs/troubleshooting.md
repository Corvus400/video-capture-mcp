# Troubleshooting

## macOS TCC Denial

Symptom:

```text
TCC permission required
```

Fix:

1. Open System Settings > Privacy & Security > Screen Recording.
2. Add or enable the launcher process described in [permissions.md](permissions.md).
3. Restart the MCP client.
4. Retry `start_recording target=macos` or `start_app_window_recording`.

For pointer tools, repeat the same flow under Accessibility.

## ffmpeg or ffprobe Missing

Symptom:

```text
ffmpeg failed
```

or:

```text
No such file or directory: ffprobe
```

Fix:

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

## No Booted iOS Simulator

Symptom:

```text
no booted simulator
```

Fix:

```bash
xcrun simctl list devices
xcrun simctl boot <UDID>
```

When multiple Simulators are booted, pass `options.device` or `options.udid`.

## xcrun simctl Not Found

Symptom:

```text
xcrun simctl list devices booted failed
```

Fix:

```bash
xcode-select --install
xcrun simctl list devices booted
```

## adb Device Unauthorized

Symptom:

```text
no Android device
```

Fix:

```bash
adb devices
```

If the device shows `unauthorized`, accept the USB debugging prompt on the device, then run:

```bash
adb kill-server
adb start-server
adb devices
```

When multiple devices are connected, pass `options.serial`.

## Output Directory

If `output_path` is omitted, recordings are written under `VIDEO_CAPTURE_MCP_OUTPUT_DIR` when set, otherwise under the system temp directory in `video-capture-mcp`.

To choose a stable output location:

```bash
export VIDEO_CAPTURE_MCP_OUTPUT_DIR="$HOME/Movies/video-capture-mcp"
```
