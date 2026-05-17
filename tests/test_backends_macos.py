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


def test_macos_build_command_requires_duration() -> None:
    with pytest.raises(macos.BackendError):
        macos.build_command("/tmp/out.mov", None)


def test_macos_build_command_formats_region_and_flags(tmp_path) -> None:
    output = tmp_path / "out.mov"

    command = macos.build_command(
        str(output),
        3.8,
        {
            "region": {"x": 10, "y": 20, "width": 300, "height": 200},
            "display": 2,
            "include_clicks": True,
            "include_audio": True,
        },
    )

    assert command == [
        "screencapture",
        "-V",
        "3",
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

    with pytest.raises(macos.BackendError, match="TCC permission required"):
        await macos.precheck()
