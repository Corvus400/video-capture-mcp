from __future__ import annotations

import stat
import signal

import pytest

from video_capture_mcp import process_registry
from video_capture_mcp.process_registry import ProcessRegistry


def test_registry_file_is_0600(tmp_path) -> None:
    registry = ProcessRegistry(tmp_path)

    registry.write(
        [
            {
                "session_id": "session-1",
                "target": "macos",
                "started_at": "2026-05-18T00:00:00+00:00",
                "video_path": "/tmp/video.mov",
                "mode": "scheduled",
                "pid": 1234,
            }
        ]
    )

    registry_file = next(tmp_path.glob("server-*.json"))

    assert stat.S_IMODE(registry_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700


@pytest.mark.asyncio
async def test_cleanup_dead_servers_sends_sigint(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "server-999999.json"
    registry_path.write_text(
        """
        {
          "server_pid": 999999,
          "sessions": [
            {
              "session_id": "old-session",
              "target": "macos",
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

    async def fake_create_process(*args, **kwargs):
        raise AssertionError("macos cleanup should not spawn subprocesses")

    monkeypatch.setattr(process_registry.os, "kill", fake_kill)

    registry = ProcessRegistry(tmp_path)
    result = await registry.cleanup_dead_servers(fake_create_process)

    assert result == [
        {
            "session_id": "old-session",
            "target": "macos",
            "pid": 456789,
            "signal_sent": True,
        }
    ]
    assert calls == [(999999, 0), (456789, 0), (456789, signal.SIGINT)]
    assert not registry_path.exists()


@pytest.mark.asyncio
async def test_cleanup_dead_android_session_runs_stop_pull_and_cleanup(
    monkeypatch, tmp_path
) -> None:
    registry_path = tmp_path / "server-999999.json"
    registry_path.write_text(
        """
        {
          "server_pid": 999999,
          "sessions": [
            {
              "session_id": "old-android",
              "target": "android",
              "pid": 456789,
              "video_path": "/tmp/android.mp4",
              "remote_path": "/sdcard/old.mp4",
              "options": {"serial": "emulator-5554"}
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        async def wait(self) -> int:
            return 0

    def fake_kill(pid: int, sig: signal.Signals | int) -> None:
        if pid == 999999:
            raise ProcessLookupError

    async def fake_create_process(*args, **kwargs):
        commands.append(tuple(args))
        return FakeProcess()

    monkeypatch.setattr(process_registry.os, "kill", fake_kill)

    registry = ProcessRegistry(tmp_path)
    result = await registry.cleanup_dead_servers(fake_create_process)

    assert result[0]["session_id"] == "old-android"
    assert result[0]["android_stop_exit_code"] == 0
    assert result[0]["pull_exit_code"] == 0
    assert result[0]["cleanup_exit_code"] == 0
    assert commands[0] == (
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "pkill",
        "-2",
        "screenrecord",
    )
    assert commands[1] == (
        "adb",
        "-s",
        "emulator-5554",
        "pull",
        "/sdcard/old.mp4",
        "/tmp/android.mp4",
    )
    assert commands[2] == (
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "rm",
        "/sdcard/old.mp4",
    )


@pytest.mark.asyncio
async def test_cleanup_dead_servers_removes_invalid_registry(tmp_path) -> None:
    registry_path = tmp_path / "server-999999.json"
    registry_path.write_text("{", encoding="utf-8")

    async def fake_create_process(*args, **kwargs):
        raise AssertionError("invalid registry should not spawn subprocesses")

    registry = ProcessRegistry(tmp_path)
    result = await registry.cleanup_dead_servers(fake_create_process)

    assert result == []
    assert not registry_path.exists()
