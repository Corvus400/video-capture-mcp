from __future__ import annotations

import asyncio
import signal

import pytest

from video_capture_mcp import pointer
from video_capture_mcp import process_registry
from video_capture_mcp import session as session_module
from video_capture_mcp import server
from video_capture_mcp import window
from video_capture_mcp.paths import default_output_root
from video_capture_mcp.session import Session
from video_capture_mcp.backends import ios


class FakeProcess:
    def __init__(self) -> None:
        self.pid = 1234
        self.returncode = None
        self.signals: list[signal.Signals] = []

    def send_signal(self, sig: signal.Signals) -> None:
        self.signals.append(sig)
        self.returncode = 0

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        await self.wait()
        return b"", b""


class FakeCommunicateProcess:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self._stdout = stdout.encode()
        self._stderr = stderr.encode()

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


def test_default_output_root_uses_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("VIDEO_CAPTURE_MCP_OUTPUT_DIR", str(tmp_path))

    assert default_output_root() == tmp_path


def test_default_output_root_uses_tempdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("VIDEO_CAPTURE_MCP_OUTPUT_DIR", raising=False)
    monkeypatch.setattr(
        "video_capture_mcp.paths.tempfile.gettempdir", lambda: str(tmp_path)
    )

    assert default_output_root() == tmp_path / "video-capture-mcp"


def test_default_output_path_uses_shared_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("VIDEO_CAPTURE_MCP_OUTPUT_DIR", str(tmp_path))

    output_path = session_module._default_output_path("android")

    assert output_path.startswith(str(tmp_path))
    assert output_path.endswith(".mp4")
    assert tmp_path.exists()


@pytest.mark.asyncio
async def test_stop_recording_sends_sigint_for_ios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    monkeypatch.setattr(
        ios, "build_command", lambda *args, **kwargs: ["recordVideo", "/tmp/test.mov"]
    )
    session = Session(create_process=create_process, run_precheck=False)
    result = await session.start_recording("ios_simulator", "/tmp/test.mov")

    stopped = await session.stop_recording(result["session_id"])

    assert process.signals == [signal.SIGINT]
    assert stopped["video_path"] == "/tmp/test.mov"
    assert stopped["exit_code"] == 0


@pytest.mark.asyncio
async def test_stop_recording_sends_sigint_for_manual_macos() -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    session = Session(create_process=create_process, run_precheck=False)
    result = await session.start_recording("macos", "/tmp/test.mov")

    await session.stop_recording(result["session_id"])

    assert result["mode"] == "manual_stop"
    assert process.signals == [signal.SIGINT]


@pytest.mark.asyncio
async def test_stop_recording_can_interrupt_scheduled_macos() -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    session = Session(create_process=create_process, run_precheck=False)
    result = await session.start_recording("macos", "/tmp/test.mov", duration_seconds=1)

    await session.stop_recording(result["session_id"])

    assert result["mode"] == "scheduled"
    assert process.signals == [signal.SIGINT]


@pytest.mark.asyncio
async def test_stop_recording_reports_no_orientation_when_not_requested() -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    session = Session(create_process=create_process, run_precheck=False)
    result = await session.start_recording("macos", "/tmp/test.mov", duration_seconds=1)

    stopped = await session.stop_recording(result["session_id"])

    assert stopped["orientation"] == {
        "normalized": False,
        "reason": "orientation not requested",
    }
    assert stopped["file_exists"] is False
    assert stopped["file_size_bytes"] is None


@pytest.mark.asyncio
async def test_rejects_duplicate_target_recording() -> None:
    async def create_process(*args, **kwargs):
        return FakeProcess()

    session = Session(create_process=create_process, run_precheck=False)
    first = await session.start_recording("macos", "/tmp/one.mov", duration_seconds=1)
    duplicate = await session.start_recording(
        "macos", "/tmp/two.mov", duration_seconds=1
    )

    assert duplicate == {
        "error": "already recording",
        "existing_session_id": first["session_id"],
    }


@pytest.mark.asyncio
async def test_allows_distinct_ios_simulators_to_record_concurrently() -> None:
    async def create_process(*args, **kwargs):
        return FakeProcess()

    session = Session(create_process=create_process, run_precheck=False)

    ipad, iphone = await asyncio.gather(
        session.start_recording(
            "ios_simulator", "/tmp/ipad.mov", options={"udid": "IPAD-UDID"}
        ),
        session.start_recording(
            "ios_simulator", "/tmp/iphone.mov", options={"udid": "IPHONE-UDID"}
        ),
    )

    assert "session_id" in ipad
    assert "session_id" in iphone
    assert ipad["session_id"] != iphone["session_id"]
    assert len(session.list_active_sessions()["sessions"]) == 2


@pytest.mark.asyncio
async def test_rejects_duplicate_ios_simulator_device_recording() -> None:
    async def create_process(*args, **kwargs):
        return FakeProcess()

    session = Session(create_process=create_process, run_precheck=False)
    first = await session.start_recording(
        "ios_simulator", "/tmp/one.mov", options={"udid": "SAME-UDID"}
    )
    duplicate = await session.start_recording(
        "ios_simulator", "/tmp/two.mov", options={"device": "SAME-UDID"}
    )

    assert duplicate == {
        "error": "already recording",
        "existing_session_id": first["session_id"],
    }


@pytest.mark.asyncio
async def test_recording_process_uses_devnull_to_avoid_pipe_deadlock() -> None:
    captured_kwargs: list[dict] = []

    async def create_process(*args, **kwargs):
        captured_kwargs.append(kwargs)
        return FakeProcess()

    session = Session(create_process=create_process, run_precheck=False)

    await session.start_recording("android", "/tmp/android.mp4")

    assert captured_kwargs[0]["stdout"] == asyncio.subprocess.DEVNULL
    assert captured_kwargs[0]["stderr"] == asyncio.subprocess.DEVNULL


@pytest.mark.asyncio
async def test_list_active_sessions_contains_started_session() -> None:
    async def create_process(*args, **kwargs):
        return FakeProcess()

    session = Session(create_process=create_process, run_precheck=False)
    started = await session.start_recording(
        "macos", "/tmp/test.mov", duration_seconds=1
    )

    active = session.list_active_sessions()

    assert active["sessions"][0]["session_id"] == started["session_id"]
    assert active["sessions"][0]["target"] == "macos"


@pytest.mark.asyncio
async def test_list_active_sessions_reaps_finished_session(tmp_path) -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    session = Session(
        create_process=create_process, run_precheck=False, registry_dir=tmp_path
    )
    await session.start_recording("macos", "/tmp/test.mov", duration_seconds=1)
    process.returncode = 0

    active = session.list_active_sessions()

    assert active == {"sessions": []}
    assert not list(tmp_path.glob("server-*.json"))


@pytest.mark.asyncio
async def test_close_stops_active_ios_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    process = FakeProcess()

    async def create_process(*args, **kwargs):
        return process

    monkeypatch.setattr(
        ios, "build_command", lambda *args, **kwargs: ["recordVideo", "/tmp/test.mov"]
    )
    session = Session(
        create_process=create_process, run_precheck=False, registry_dir=tmp_path
    )
    await session.start_recording("ios_simulator", "/tmp/test.mov")

    await session.close()

    assert process.signals == [signal.SIGINT]
    assert session.list_active_sessions() == {"sessions": []}
    assert not list(tmp_path.glob("server-*.json"))


@pytest.mark.asyncio
async def test_stop_all_recordings_stops_current_sessions(tmp_path) -> None:
    first = FakeProcess()
    second = FakeProcess()
    processes = [first, second]

    async def create_process(*args, **kwargs):
        return processes.pop(0)

    session = Session(
        create_process=create_process, run_precheck=False, registry_dir=tmp_path
    )
    mac = await session.start_recording("macos", "/tmp/mac.mov")
    ios_started = await session.start_recording(
        "ios_simulator", "/tmp/ios.mov", options={"udid": "IPHONE"}
    )

    result = await session.stop_all_recordings()

    assert {item["session_id"] for item in result["stopped"]} == {
        mac["session_id"],
        ios_started["session_id"],
    }
    assert first.signals == [signal.SIGINT]
    assert second.signals == [signal.SIGINT]
    assert session.list_active_sessions() == {"sessions": []}
    assert not list(tmp_path.glob("server-*.json"))


@pytest.mark.asyncio
async def test_stop_all_recordings_can_filter_by_target() -> None:
    first = FakeProcess()
    second = FakeProcess()
    processes = [first, second]

    async def create_process(*args, **kwargs):
        return processes.pop(0)

    session = Session(create_process=create_process, run_precheck=False)
    mac = await session.start_recording("macos", "/tmp/mac.mov")
    ios_started = await session.start_recording(
        "ios_simulator", "/tmp/ios.mov", options={"udid": "IPHONE"}
    )

    result = await session.stop_all_recordings("mac")

    assert [item["session_id"] for item in result["stopped"]] == [mac["session_id"]]
    assert first.signals == [signal.SIGINT]
    assert second.signals == []
    assert [
        active["session_id"] for active in session.list_active_sessions()["sessions"]
    ] == [ios_started["session_id"]]


@pytest.mark.asyncio
async def test_cleanup_dead_server_registry_sends_sigint(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    registry_path = tmp_path / "server-999999.json"
    registry_path.write_text(
        """
        {
          "server_pid": 999999,
          "sessions": [
            {
              "session_id": "old-session",
              "target": "ios_simulator",
              "pid": 456789,
              "video_path": "/tmp/old.mov",
              "options": {}
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    calls: list[tuple[int, signal.Signals | int]] = []

    def fake_kill(pid: int, sig: signal.Signals | int) -> None:
        calls.append((pid, sig))
        if pid == 999999:
            raise ProcessLookupError

    async def create_process(*args, **kwargs):
        raise AssertionError("ios cleanup should not spawn a subprocess")

    monkeypatch.setattr(process_registry.os, "kill", fake_kill)
    session = Session(
        create_process=create_process, run_precheck=False, registry_dir=tmp_path
    )

    result = await session.cleanup_stale_processes()

    assert result["cleaned"][0]["session_id"] == "old-session"
    assert result["cleaned"][0]["signal_sent"] is True
    assert calls == [(999999, 0), (456789, 0), (456789, signal.SIGINT)]
    assert not registry_path.exists()


@pytest.mark.asyncio
async def test_hover_sequence_moves_pointer_without_clicking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    points: list[tuple[float, float]] = []

    def fake_move_pointer_to(point: pointer.CGPoint) -> None:
        points.append((point.x, point.y))

    monkeypatch.setattr(pointer, "_move_pointer_to", fake_move_pointer_to)

    result = await pointer.move_sequence(
        [
            {"x": 100, "y": 200},
            [300, -400],
        ],
        hold_seconds=0,
        steps_per_segment=1,
        step_delay_seconds=0,
    )

    assert result == {
        "points": [{"x": 100.0, "y": 200.0}, {"x": 300.0, "y": -400.0}],
        "moved_count": 2,
    }
    assert points == [(100.0, 200.0), (300.0, -400.0)]


@pytest.mark.asyncio
async def test_get_window_region_returns_visible_intersection() -> None:
    outputs = [
        "100, -1302, 1300, -26",
        "0, -1440, 3440, 1440",
    ]

    async def create_process(*args, **kwargs):
        return FakeCommunicateProcess(outputs.pop(0))

    result = await window.get_window_region(
        "Google Chrome", create_process=create_process
    )

    assert result["visible"] is True
    assert result["region"] == {
        "x": 100,
        "y": -1302,
        "width": 1200,
        "height": 1276,
    }
    assert result["activated"] is False


@pytest.mark.asyncio
async def test_get_window_region_can_activate_before_bounds() -> None:
    outputs = [
        "",
        "100, -1302, 1300, -26",
        "0, -1440, 3440, 1440",
    ]
    scripts: list[str] = []

    async def create_process(*args, **kwargs):
        scripts.append(args[2])
        return FakeCommunicateProcess(outputs.pop(0))

    result = await window.get_window_region(
        "Google Chrome",
        activate=True,
        activation_delay_seconds=0,
        create_process=create_process,
    )

    assert scripts == [
        'tell application "Google Chrome" to activate',
        'tell application "Google Chrome" to get bounds of front window',
        'tell application "Finder" to get bounds of window of desktop',
    ]
    assert result["activated"] is True


@pytest.mark.asyncio
async def test_get_window_region_reports_insufficient_visibility() -> None:
    outputs = [
        "3000, 100, 3800, 700",
        "0, 0, 3440, 1440",
    ]

    async def create_process(*args, **kwargs):
        return FakeCommunicateProcess(outputs.pop(0))

    result = await window.get_window_region(
        "Google Chrome", create_process=create_process
    )

    assert result["visible"] is False
    assert 0 < result["visible_ratio"] < 0.8
    assert result["region"] == {
        "x": 3000,
        "y": 100,
        "width": 440,
        "height": 600,
    }


@pytest.mark.asyncio
async def test_start_app_window_recording_records_visible_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window_region = {
        "visible": True,
        "region": {"x": 100, "y": -1302, "width": 1200, "height": 1276},
    }
    calls: list[tuple[str, str | None, float | None, dict]] = []

    async def fake_get_window_region(*args, **kwargs):
        assert kwargs["activate"] is True
        return window_region

    class FakeSessionForServer:
        async def start_recording(self, target, output_path, duration_seconds, options):
            calls.append((target, output_path, duration_seconds, options))
            return {
                "session_id": "session-1",
                "video_path": output_path,
                "mode": "scheduled",
            }

    monkeypatch.setattr(server, "get_app_window_region", fake_get_window_region)
    monkeypatch.setattr(server, "_session", FakeSessionForServer())

    result = await server.start_app_window_recording(
        "Google Chrome",
        3,
        "/tmp/chrome.mov",
        options={"orientation": "landscape"},
    )

    assert result["window"] == window_region
    assert calls == [
        (
            "macos",
            "/tmp/chrome.mov",
            3,
            {
                "orientation": "landscape",
                "region": {"x": 100, "y": -1302, "width": 1200, "height": 1276},
            },
        )
    ]


@pytest.mark.asyncio
async def test_start_app_window_recording_uses_shared_default_output_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    window_region = {
        "visible": True,
        "region": {"x": 100, "y": -1302, "width": 1200, "height": 1276},
    }
    calls: list[tuple[str, str | None, float | None, dict]] = []

    async def fake_get_window_region(*args, **kwargs):
        return window_region

    class FakeSessionForServer:
        async def start_recording(self, target, output_path, duration_seconds, options):
            calls.append((target, output_path, duration_seconds, options))
            return {
                "session_id": "session-1",
                "video_path": output_path,
                "mode": "scheduled",
            }

    monkeypatch.setenv("VIDEO_CAPTURE_MCP_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(server, "get_app_window_region", fake_get_window_region)
    monkeypatch.setattr(server, "_session", FakeSessionForServer())

    result = await server.start_app_window_recording("Google Chrome", 3)

    assert result["video_path"] == str(
        tmp_path / "video_capture_google_chrome_window.mov"
    )
    assert calls[0][1] == str(tmp_path / "video_capture_google_chrome_window.mov")


@pytest.mark.asyncio
async def test_start_app_window_recording_allows_manual_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window_region = {
        "visible": True,
        "region": {"x": 100, "y": -1302, "width": 1200, "height": 1276},
    }
    calls: list[tuple[str, str | None, float | None, dict]] = []

    async def fake_get_window_region(*args, **kwargs):
        return window_region

    class FakeSessionForServer:
        async def start_recording(self, target, output_path, duration_seconds, options):
            calls.append((target, output_path, duration_seconds, options))
            return {
                "session_id": "session-1",
                "video_path": output_path,
                "mode": "manual_stop",
            }

    monkeypatch.setattr(server, "get_app_window_region", fake_get_window_region)
    monkeypatch.setattr(server, "_session", FakeSessionForServer())

    result = await server.start_app_window_recording(
        "Google Chrome",
        output_path="/tmp/chrome.mov",
    )

    assert result["mode"] == "manual_stop"
    assert calls == [
        (
            "macos",
            "/tmp/chrome.mov",
            None,
            {"region": {"x": 100, "y": -1302, "width": 1200, "height": 1276}},
        )
    ]


@pytest.mark.asyncio
async def test_start_app_window_recording_rejects_hidden_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window_region = {
        "visible": False,
        "region": {"x": 3000, "y": 100, "width": 440, "height": 600},
    }

    async def fake_get_window_region(*args, **kwargs):
        assert kwargs["activate"] is True
        return window_region

    class FakeSessionForServer:
        async def start_recording(self, *args, **kwargs):
            raise AssertionError("hidden windows must not start recording")

    monkeypatch.setattr(server, "get_app_window_region", fake_get_window_region)
    monkeypatch.setattr(server, "_session", FakeSessionForServer())

    result = await server.start_app_window_recording("Google Chrome", 3)

    assert result == {
        "error": "target window is not sufficiently visible",
        "window": window_region,
    }


@pytest.mark.asyncio
async def test_server_hover_sequence_can_activate_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_window = {
        "app_name": "Google Chrome",
        "visible": True,
        "activated": True,
        "region": {"x": 0, "y": -1400, "width": 1800, "height": 1374},
    }
    calls: list[tuple[str, dict]] = []

    async def fake_get_window_region(*args, **kwargs):
        calls.append((args[0], kwargs))
        return active_window

    async def fake_hover_sequence(points, **kwargs):
        assert kwargs["hold_seconds"] == 0
        assert kwargs["steps_per_segment"] == 12
        assert kwargs["step_delay_seconds"] == 0.02
        return {"points": points, "hold_seconds": kwargs["hold_seconds"]}

    monkeypatch.setattr(server, "get_app_window_region", fake_get_window_region)
    monkeypatch.setattr(
        server, "move_pointer_interpolated_sequence", fake_hover_sequence
    )

    result = await server.hover_sequence(
        [{"x": 100, "y": -200}],
        hold_seconds=0,
        app_name="Google Chrome",
    )

    assert calls == [("Google Chrome", {"activate": True})]
    assert result == {
        "points": [{"x": 100, "y": -200}],
        "hold_seconds": 0,
        "active_window": active_window,
    }


@pytest.mark.asyncio
async def test_start_recording_returns_error_object_for_backend_failure() -> None:
    session = Session(run_precheck=False)

    result = await session.start_recording(
        "android", "/tmp/test.mp4", options={"size": "bad"}
    )

    assert result["target"] == "android"
    assert "options.size" in result["error"]


def test_ios_command_uses_h264_display_option_and_device() -> None:
    command = ios.build_command(
        "/tmp/test.mov",
        None,
        {"display": "external", "device": "ABC-123"},
    )

    assert command == [
        "xcrun",
        "simctl",
        "io",
        "ABC-123",
        "recordVideo",
        "--codec",
        "h264",
        "--display",
        "external",
        "--force",
        "/tmp/test.mov",
    ]


@pytest.mark.asyncio
async def test_android_stop_sends_sigint_pulls_and_cleans_remote() -> None:
    calls: list[tuple[str, ...]] = []
    kwargs_list: list[dict] = []
    screenrecord = FakeProcess()
    stop = FakeProcess()
    pull = FakeProcess()
    cleanup = FakeProcess()
    processes = [screenrecord, stop, pull, cleanup]

    async def create_process(*args, **kwargs):
        calls.append(tuple(args))
        kwargs_list.append(kwargs)
        return processes.pop(0)

    session = Session(create_process=create_process, run_precheck=False)
    started = await session.start_recording(
        "android",
        "/tmp/android.mp4",
        options={"serial": "emulator-5554"},
    )

    stopped = await session.stop_recording(started["session_id"])

    assert screenrecord.signals == []
    assert calls[0][:7] == (
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "screenrecord",
        "--time-limit",
        "0",
    )
    assert calls[1] == (
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "pkill",
        "-2",
        "screenrecord",
    )
    assert calls[2] == (
        "adb",
        "-s",
        "emulator-5554",
        "pull",
        stopped["remote_path"],
        "/tmp/android.mp4",
    )
    assert calls[3] == (
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "rm",
        stopped["remote_path"],
    )
    assert stopped["android_stop_exit_code"] == 0
    assert stopped["pull_exit_code"] == 0
    assert stopped["cleanup_exit_code"] == 0
    assert all(
        kwargs["stdout"] == asyncio.subprocess.DEVNULL
        and kwargs["stderr"] == asyncio.subprocess.DEVNULL
        for kwargs in kwargs_list
    )
