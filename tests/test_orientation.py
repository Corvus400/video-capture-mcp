from __future__ import annotations

import pytest

from video_capture_mcp import orientation


class FakeCommunicateProcess:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.returncode = returncode
        self._stdout = stdout.encode()
        self.communicated = False

    async def communicate(self) -> tuple[bytes, bytes]:
        self.communicated = True
        return self._stdout, b""

    async def wait(self) -> int:
        return self.returncode


def test_rotation_needed_for_landscape_from_portrait() -> None:
    assert orientation._rotation_needed(720, 1280, "landscape", None) == 90


def test_rotation_needed_for_portrait_from_landscape() -> None:
    assert orientation._rotation_needed(1280, 720, "portrait", None) == 270


def test_rotation_needed_prefers_explicit_degrees() -> None:
    assert orientation._rotation_needed(1280, 720, "portrait", 180) == 180


def test_rotation_needed_rejects_bad_orientation() -> None:
    with pytest.raises(orientation.OrientationError):
        orientation._rotation_needed(1280, 720, "square", None)


@pytest.mark.asyncio
async def test_probe_dimensions_reads_ffprobe_json() -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_create_process(*args, **kwargs):
        calls.append(tuple(args))
        return FakeCommunicateProcess('{"streams":[{"width":1280,"height":720}]}')

    result = await orientation.probe_dimensions(
        "/tmp/in.mp4", create_process=fake_create_process
    )

    assert result == {"width": 1280, "height": 720}
    assert calls[0][:4] == ("ffprobe", "-v", "error", "-select_streams")


@pytest.mark.asyncio
async def test_probe_dimensions_rejects_missing_stream() -> None:
    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess('{"streams":[]}')

    with pytest.raises(orientation.OrientationError):
        await orientation.probe_dimensions(
            "/tmp/in.mp4", create_process=fake_create_process
        )


@pytest.mark.asyncio
async def test_normalize_video_orientation_returns_not_requested() -> None:
    result = await orientation.normalize_video_orientation("/tmp/in.mp4", None)

    assert result == {"normalized": False, "reason": "orientation not requested"}


@pytest.mark.asyncio
async def test_normalize_video_orientation_skips_when_already_matching(
    monkeypatch,
) -> None:
    async def fake_probe_dimensions(*args, **kwargs):
        return {"width": 1280, "height": 720}

    monkeypatch.setattr(orientation, "probe_dimensions", fake_probe_dimensions)

    result = await orientation.normalize_video_orientation("/tmp/in.mp4", "landscape")

    assert result == {
        "normalized": False,
        "reason": "already matches orientation",
        "before": {"width": 1280, "height": 720},
        "after": {"width": 1280, "height": 720},
    }


@pytest.mark.asyncio
async def test_normalize_video_orientation_raises_on_ffmpeg_failure(
    monkeypatch, tmp_path
) -> None:
    video = tmp_path / "in.mp4"
    video.write_bytes(b"video")

    async def fake_probe_dimensions(*args, **kwargs):
        return {"width": 720, "height": 1280}

    async def fake_create_process(*args, **kwargs):
        return FakeCommunicateProcess(returncode=1)

    monkeypatch.setattr(orientation, "probe_dimensions", fake_probe_dimensions)

    with pytest.raises(orientation.OrientationError):
        await orientation.normalize_video_orientation(
            str(video), "landscape", create_process=fake_create_process
        )


@pytest.mark.asyncio
async def test_normalize_video_orientation_drains_ffmpeg_stderr(
    monkeypatch, tmp_path
) -> None:
    video = tmp_path / "in.mp4"
    video.write_bytes(b"video")
    ffmpeg = FakeCommunicateProcess(returncode=0)
    calls: list[dict] = []

    async def fake_probe_dimensions(*args, **kwargs):
        return {"width": 720, "height": 1280}

    async def fake_create_process(*args, **kwargs):
        calls.append(kwargs)
        return ffmpeg

    monkeypatch.setattr(orientation, "probe_dimensions", fake_probe_dimensions)
    monkeypatch.setattr(orientation.Path, "replace", lambda self, target: None)

    await orientation.normalize_video_orientation(
        str(video), "landscape", create_process=fake_create_process
    )

    assert calls[0]["stdout"] == orientation.asyncio.subprocess.DEVNULL
    assert calls[0]["stderr"] == orientation.asyncio.subprocess.PIPE
    assert ffmpeg.communicated is True


def test_transpose_filter_rejects_zero() -> None:
    with pytest.raises(orientation.OrientationError):
        orientation._transpose_filter(0)
