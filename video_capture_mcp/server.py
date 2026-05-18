from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from video_capture_mcp import __version__
from video_capture_mcp.extractor import extract_frames as extract_video_frames
from video_capture_mcp.paths import default_output_root
from video_capture_mcp.pointer import (
    move_sequence as move_pointer_interpolated_sequence,
)
from video_capture_mcp.pointer import move_pointer as move_pointer_once
from video_capture_mcp.session import Session
from video_capture_mcp.window import get_window_region as get_app_window_region


SERVER_INSTRUCTIONS = """\
video_capture MCP server — record macOS / iOS Simulator / Android screen, then extract key frames.

Use this server when screenshots are insufficient: keyboard reveal, hover/unhover, transient layout glitches, animation regressions, or any UI change between two frames.

# Decision tree
1. Recording a macOS app or browser window? -> start_app_window_recording (activates and bounds to the visible front window).
2. Recording the full macOS desktop, a specific region, or a non-foreground window? -> start_recording target="macos" with options.region.
3. Recording an iOS Simulator? -> start_recording target="ios_simulator". Pass options.udid when multiple simulators are booted.
4. Recording an Android device? -> start_recording target="android". Pass options.serial when multiple devices are attached.
5. Need a fixed-duration recording with frame extraction in one call? -> record_and_extract.
6. Hover-only UI verification (no clicks)? -> hover_sequence (preferred over move_pointer when multiple points).

# Target aliases (start_recording.target)
macos | mac | desktop -> macOS screencapture
ios_simulator | ios-simulator | ios | simulator -> xcrun simctl
android -> adb shell screenrecord

# Manual-stop workflow (preferred for agent-driven UI verification)
1. Call start_recording or start_app_window_recording WITHOUT duration_seconds.
2. Save the returned session_id.
3. Operate the UI (Computer Use, hover_sequence, etc.).
4. Call stop_recording(session_id).
5. Verify the response: file_exists must be true and file_size_bytes must be > 0 before extracting frames. If false/zero, the recording failed — check permissions and retry.

# Session management
- list_active_sessions returns all live sessions for this server process.
- stop_all_recordings clears every session for this process, optionally filtered by target. Use when session_id is lost or duplicate-target protection blocks a new start_recording.
- cleanup_stale_processes reaps recordings owned by dead prior server PIDs (current OS user only). The server auto-runs this before each start_recording, but call it explicitly if start fails with stale-process errors.

# Permissions (macOS only; required before first use)
- Screen Recording: required for target=macos and start_app_window_recording. System Settings -> Privacy & Security -> Screen Recording -> add the launcher process -> fully restart the MCP client.
- Accessibility: required for move_pointer and hover_sequence. Same flow under Accessibility.
- iOS Simulator and Android do NOT need Screen Recording (they use xcrun simctl / adb).
- ffmpeg and ffprobe must be on PATH for extract_frames and orientation normalization. Install with `brew install ffmpeg`.
- If a recording or pointer tool fails with TCC denial, the agent cannot self-recover; surface the error to the user with the System Settings path.

# Output paths
- If output_path is omitted, recordings go to $VIDEO_CAPTURE_MCP_OUTPUT_DIR (when set) or to the system temp directory under video-capture-mcp.
- explicit output_path is treated as trusted client input; the agent is responsible for choosing a safe directory.

# Common failure modes and recovery
- "TCC permission required" -> surface to user; agent cannot grant permission.
- "ffmpeg failed" or "No such file or directory: ffprobe" -> install ffmpeg via brew.
- "no booted simulator" -> xcrun simctl boot <UDID>, or pass options.udid.
- iOS multi-simulator -> always pass options.udid explicitly.
- "no Android device" / unauthorized -> ask user to accept the USB-debugging prompt, then adb kill-server && adb start-server. Always pass options.serial when more than one device is attached.
- start_app_window_recording returns {error, window} when visible_ratio < min_visible_ratio -> reposition or unminimize the target window, then retry.

# What NOT to do
- Do not call start_recording target=macos for a single visible app window; use start_app_window_recording so only that window region is captured.
- Do not chain stop_recording calls without checking file_size_bytes; an empty file means the backend never wrote anything.
- Do not pass relative output_path; prefer absolute paths under VIDEO_CAPTURE_MCP_OUTPUT_DIR.
"""

mcp = FastMCP("video_capture", instructions=SERVER_INSTRUCTIONS)
_session = Session()


@mcp.tool()
async def start_recording(
    target: str,
    duration_seconds: float | None = None,
    output_path: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start recording a target screen.

    For macOS browser or desktop-app debugging, prefer
    start_app_window_recording so the target app's visible window is checked and
    only that window region is recorded. Use target="macos" here only when a
    full desktop recording is intentionally needed or when options.region is
    already known. Omitting duration_seconds starts a manual-stop recording.
    """
    return await _session.start_recording(
        target, output_path, duration_seconds, options
    )


@mcp.tool()
async def stop_recording(session_id: str) -> dict[str, Any]:
    """Stop a running recording session."""
    return await _session.stop_recording(session_id)


@mcp.tool()
async def stop_all_recordings(
    target: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Stop all running recording sessions, optionally filtered by target."""
    return await _session.stop_all_recordings(target)


@mcp.tool()
async def list_active_sessions() -> dict[str, list[dict[str, Any]]]:
    """List active recording sessions."""
    return _session.list_active_sessions()


@mcp.tool()
async def cleanup_stale_processes() -> dict[str, list[dict[str, Any]]]:
    """Clean up recording processes left by a dead previous server process."""
    return await _session.cleanup_stale_processes()


@mcp.tool()
async def move_pointer(x: float, y: float) -> dict[str, float]:
    """Move the macOS pointer without clicking.

    Use this for hover-only desktop checks when Computer Use drag would send a
    mouse-up and might activate the target.
    """
    return move_pointer_once(x, y)


@mcp.tool()
async def hover_sequence(
    points: list[Any],
    hold_seconds: float = 0.5,
    app_name: str | None = None,
    steps_per_segment: int = 12,
    step_delay_seconds: float = 0.02,
) -> dict[str, Any]:
    """Move the macOS pointer through hover/unhover points without clicking.

    This is the preferred hover-only fallback for canvas-style or inaccessible
    web pages where Playwright cannot target DOM elements. Pass app_name for
    browser/app checks so the target app is activated immediately before the
    hover sequence. It posts only mouse-move events and does not click.
    """
    active_window = None
    if app_name:
        active_window = await get_app_window_region(app_name, activate=True)
    result = await move_pointer_interpolated_sequence(
        points,
        hold_seconds=hold_seconds,
        steps_per_segment=steps_per_segment,
        step_delay_seconds=step_delay_seconds,
    )
    if active_window is not None:
        result["active_window"] = active_window
    return result


@mcp.tool()
async def get_window_region(
    app_name: str,
    padding: int = 0,
    min_visible_ratio: float = 0.8,
    activate: bool = True,
) -> dict[str, Any]:
    """Return the visible front-window region for a macOS app.

    Call this before macOS app/browser recording to verify the target window is
    actually on screen and active. If visible=false, reposition the window
    before recording.
    """
    return await get_app_window_region(
        app_name,
        padding=padding,
        min_visible_ratio=min_visible_ratio,
        activate=activate,
    )


@mcp.tool()
async def start_app_window_recording(
    app_name: str,
    duration_seconds: float | None = None,
    output_path: str | None = None,
    padding: int = 0,
    min_visible_ratio: float = 0.8,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start recording only the visible front-window region of a macOS app.

    Preferred for Chrome/Safari/desktop-app debugging. It first activates the
    target app, verifies the target front window is sufficiently visible, then
    records only that visible region via screencapture -R instead of recording
    the full desktop. Omitting duration_seconds records until stop_recording is
    called.
    """
    window_region = await get_app_window_region(
        app_name,
        padding=padding,
        min_visible_ratio=min_visible_ratio,
        activate=True,
    )
    if not window_region["visible"]:
        return {
            "error": "target window is not sufficiently visible",
            "window": window_region,
        }
    recording_options = dict(options or {})
    recording_options["region"] = window_region["region"]
    target_output = output_path or str(
        default_output_root()
        / f"video_capture_{app_name.replace(' ', '_').lower()}_window.mov"
    )
    started = await _session.start_recording(
        "macos", target_output, duration_seconds, recording_options
    )
    return {
        **started,
        "window": window_region,
    }


@mcp.tool()
async def extract_frames(
    video_path: str,
    output_dir: str,
    mode: str = "scene",
    scene_threshold: float = 0.1,
    fps: float | None = None,
    max_frames: int = 50,
    inline_images: bool = True,
    rotate_degrees: int | None = None,
) -> dict[str, Any]:
    """Extract key frames from a video."""
    return await extract_video_frames(
        video_path,
        output_dir,
        mode,
        scene_threshold,
        fps,
        max_frames,
        inline_images,
        rotate_degrees,
    )


@mcp.tool()
async def record_and_extract(
    target: str,
    duration_seconds: float,
    output_dir: str,
    options: dict[str, Any] | None = None,
    extract_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a target for a fixed duration and extract frames in one call."""
    return await _session.record_and_extract(
        target,
        duration_seconds,
        output_dir,
        options=options,
        extract_options=extract_options,
    )


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(__version__)
        return
    try:
        mcp.run()
    finally:
        asyncio.run(_session.close())


if __name__ == "__main__":
    main()
