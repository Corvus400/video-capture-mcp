from __future__ import annotations

import pytest

from video_capture_mcp.backends import macos


class FakeCommunicateProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.returncode = returncode
        self._stdout = stdout.encode()
        self._stderr = stderr.encode()

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


def test_macos_build_command_allows_manual_stop_recording(tmp_path) -> None:
    output = tmp_path / "out.mov"

    command = macos.build_command(str(output), None)

    assert command == ["screencapture", "-v", str(output)]


def test_macos_build_command_formats_scheduled_region_and_flags(tmp_path) -> None:
    output = tmp_path / "out.mov"

    command = macos.build_command(
        str(output),
        3.8,
        {
            "region": {"x": 10, "y": 20, "width": 300, "height": 200},
            "display": 2,
            "include_cursor": True,
            "include_clicks": True,
            "include_audio": True,
        },
    )

    assert command == [
        "screencapture",
        "-v",
        "-V",
        "3",
        "-C",
        "-R",
        "10,20,300,200",
        "-D",
        "2",
        "-k",
        "-g",
        str(output),
    ]


def test_macos_build_command_rejects_bad_region(tmp_path) -> None:
    with pytest.raises(macos.BackendError):
        macos.build_command(str(tmp_path / "out.mov"), 1, {"region": [0, 0, 0, 100]})


@pytest.mark.asyncio
async def test_macos_precheck_reports_tcc_failure(monkeypatch, tmp_path) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(stderr="permission denied", returncode=1)

    monkeypatch.setattr(macos.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(macos.asyncio, "create_subprocess_exec", fake_create_process)

    with pytest.raises(macos.BackendError, match="macOS TCC permission required"):
        await macos.precheck()


@pytest.mark.asyncio
async def test_macos_permission_diagnosis_reports_launcher_guidance(
    monkeypatch, tmp_path
) -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(stderr="permission denied", returncode=1)

    monkeypatch.setattr(macos.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(macos.sys, "executable", "/test/python")
    monkeypatch.setattr(macos.asyncio, "create_subprocess_exec", fake_create_process)

    diagnosis = await macos.diagnose_screen_recording()

    assert diagnosis["ok"] is False
    assert diagnosis["required_permission"] == "Screen Recording"
    assert diagnosis["settings_path"] == (
        "System Settings > Privacy & Security > Screen Recording"
    )
    assert diagnosis["launcher_process"] == "/test/python"
    assert diagnosis["restart_required"] is True
    assert "MCP client" in diagnosis["restart_hint"]
    assert (
        "macOS recording needs Screen Recording permission" in diagnosis["user_message"]
    )
    assert "Claude Code or Codex" in diagnosis["user_message"]
    assert "one-time setup step" in diagnosis["user_message"]
    assert diagnosis["screencapture_stderr"] == "permission denied"


@pytest.mark.asyncio
async def test_macos_permission_diagnosis_reports_success(
    monkeypatch, tmp_path
) -> None:
    async def fake_create_process(*args, **kwargs):
        output_path = macos.Path(args[3])
        output_path.write_bytes(b"movie")
        return FakeCommunicateProcess(returncode=0)

    monkeypatch.setattr(macos.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(macos.asyncio, "create_subprocess_exec", fake_create_process)

    diagnosis = await macos.diagnose_screen_recording()

    assert diagnosis["ok"] is True
    assert diagnosis["probe_file_size_bytes"] == 5
