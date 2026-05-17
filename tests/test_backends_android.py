from __future__ import annotations

import pytest

from video_capture_mcp.backends import android


class FakeCommunicateProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.returncode = returncode
        self._stdout = stdout.encode()
        self._stderr = stderr.encode()

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_android_precheck_detects_device(monkeypatch) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(
            stdout="List of devices attached\nemulator-5554\tdevice\n"
        )

    monkeypatch.setattr(android.asyncio, "create_subprocess_exec", fake_create_process)

    await android.precheck()


@pytest.mark.asyncio
async def test_android_precheck_rejects_no_device(monkeypatch) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(
            stdout="List of devices attached\nemulator-5554\tunauthorized\n"
        )

    monkeypatch.setattr(android.asyncio, "create_subprocess_exec", fake_create_process)

    with pytest.raises(android.BackendError, match="no Android device"):
        await android.precheck()


def test_android_build_command_uses_serial_size_and_bit_rate(tmp_path) -> None:
    command = android.build_command(
        str(tmp_path / "out.mp4"),
        None,
        {
            "serial": "emulator-5554",
            "size": "1280x720",
            "bit_rate": 4_000_000,
            "_remote_path": "/sdcard/test.mp4",
        },
    )

    assert command == [
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "screenrecord",
        "--time-limit",
        "0",
        "--size",
        "1280x720",
        "--bit-rate",
        "4000000",
        "/sdcard/test.mp4",
    ]


def test_android_size_accepts_dict_and_list() -> None:
    assert android._format_size({"width": 320, "height": 240}) == "320x240"
    assert android._format_size([640, 480]) == "640x480"


def test_android_size_rejects_bad_string() -> None:
    with pytest.raises(android.BackendError):
        android._format_size("large")
