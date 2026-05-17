from __future__ import annotations

import pytest

from video_capture_mcp.backends import ios


class FakeCommunicateProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.returncode = returncode
        self._stdout = stdout.encode()
        self._stderr = stderr.encode()

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_ios_precheck_rejects_no_booted_simulator(monkeypatch) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(stdout="== Devices ==\n")

    monkeypatch.setattr(ios.asyncio, "create_subprocess_exec", fake_create_process)

    with pytest.raises(ios.BackendError, match="no booted simulator"):
        await ios.precheck()


@pytest.mark.asyncio
async def test_ios_precheck_reports_command_failure(monkeypatch) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(stderr="xcode missing", returncode=1)

    monkeypatch.setattr(ios.asyncio, "create_subprocess_exec", fake_create_process)

    with pytest.raises(ios.BackendError, match="xcode missing"):
        await ios.precheck()


def test_ios_build_command_uses_default_booted(tmp_path) -> None:
    command = ios.build_command(str(tmp_path / "out.mov"), None)

    assert command[:7] == [
        "xcrun",
        "simctl",
        "io",
        "booted",
        "recordVideo",
        "--codec",
        "h264",
    ]


def test_ios_build_command_uses_udid_and_display(tmp_path) -> None:
    command = ios.build_command(
        str(tmp_path / "out.mov"), None, {"udid": "ABC", "display": "external"}
    )

    assert command == [
        "xcrun",
        "simctl",
        "io",
        "ABC",
        "recordVideo",
        "--codec",
        "h264",
        "--display",
        "external",
        "--force",
        str(tmp_path / "out.mov"),
    ]


def test_ios_build_command_rejects_bad_display(tmp_path) -> None:
    with pytest.raises(ios.BackendError):
        ios.build_command(str(tmp_path / "out.mov"), None, {"display": "side"})
