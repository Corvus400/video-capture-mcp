from __future__ import annotations

import asyncio
import math
import shutil

import pytest

from video_capture_mcp.extractor import ExtractorError
from video_capture_mcp.extractor import extract_frames
from video_capture_mcp.extractor import _filter_chain
from video_capture_mcp.orientation import probe_dimensions


async def _make_test_video(path) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=160x90:rate=10:duration=1",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode == 0


@pytest.mark.asyncio
async def test_extract_frames_fixed_fps(tmp_path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    video = tmp_path / "input.mp4"
    await _make_test_video(video)

    result = await extract_frames(
        str(video),
        str(tmp_path / "frames"),
        mode="fixed_fps",
        fps=2,
        inline_images=False,
    )

    assert len(result["frame_paths"]) > 0
    assert result["images"] == []
    assert result["dropped_for_max"] == 0


@pytest.mark.asyncio
async def test_extract_frames_rotates_output_frames(tmp_path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe is not installed")
    video = tmp_path / "input.mp4"
    await _make_test_video(video)

    result = await extract_frames(
        str(video),
        str(tmp_path / "frames"),
        mode="fixed_fps",
        fps=1,
        inline_images=False,
        rotate_degrees=90,
        max_frames=1,
    )

    dimensions = await probe_dimensions(result["frame_paths"][0])
    assert dimensions == {"width": 90, "height": 160}


def test_scene_threshold_rejects_nan() -> None:
    with pytest.raises(ExtractorError):
        _filter_chain("scene", math.nan, None, None)


def test_fixed_fps_rejects_infinity() -> None:
    with pytest.raises(ExtractorError):
        _filter_chain("fixed_fps", 0.1, math.inf, None)
