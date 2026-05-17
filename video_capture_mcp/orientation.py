from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol


class ProcessLike(Protocol):
    async def communicate(self) -> tuple[bytes, bytes]: ...

    async def wait(self) -> int: ...


CreateProcess = Callable[..., Awaitable[ProcessLike]]


class OrientationError(RuntimeError):
    """Video orientation normalization failed."""


async def normalize_video_orientation(
    video_path: str,
    desired_orientation: str | None,
    *,
    create_process: CreateProcess = asyncio.create_subprocess_exec,
    rotate_degrees: int | None = None,
) -> dict[str, Any]:
    if desired_orientation is None and rotate_degrees is None:
        return {"normalized": False, "reason": "orientation not requested"}

    path = os.fspath(Path(video_path).expanduser())
    before = await probe_dimensions(path, create_process=create_process)
    degrees = _rotation_needed(before["width"], before["height"], desired_orientation, rotate_degrees)
    if degrees == 0:
        return {"normalized": False, "reason": "already matches orientation", "before": before, "after": before}

    output = _temporary_output_path(path)
    proc = await create_process(
        "ffmpeg",
        "-y",
        "-i",
        path,
        "-vf",
        _transpose_filter(degrees),
        "-metadata:s:v:0",
        "rotate=0",
        output,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    exit_code = await proc.wait()
    if exit_code != 0:
        Path(output).unlink(missing_ok=True)
        raise OrientationError(f"ffmpeg orientation normalization failed with exit code {exit_code}")
    Path(output).replace(path)
    after = await probe_dimensions(path, create_process=create_process)
    return {
        "normalized": True,
        "before": before,
        "after": after,
        "rotate_degrees": degrees,
    }


async def probe_dimensions(
    video_path: str,
    *,
    create_process: CreateProcess = asyncio.create_subprocess_exec,
) -> dict[str, int]:
    proc = await create_process(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _stderr = await proc.communicate()
    data = json.loads(stdout.decode("utf-8"))
    streams = data.get("streams") or []
    if not streams:
        raise OrientationError(f"ffprobe did not find a video stream in {video_path}")
    return {
        "width": int(streams[0]["width"]),
        "height": int(streams[0]["height"]),
    }


def _rotation_needed(width: int, height: int, desired_orientation: str | None, rotate_degrees: int | None) -> int:
    if rotate_degrees is not None:
        return _normalize_degrees(rotate_degrees)
    if desired_orientation is None:
        return 0
    orientation = desired_orientation.lower()
    if orientation == "landscape":
        return 90 if height > width else 0
    if orientation == "portrait":
        return 270 if width > height else 0
    raise OrientationError("orientation must be 'portrait' or 'landscape'.")


def _normalize_degrees(degrees: int) -> int:
    normalized = degrees % 360
    if normalized not in {0, 90, 180, 270}:
        raise OrientationError("rotate_degrees must be one of 0, 90, 180, or 270.")
    return normalized


def _transpose_filter(degrees: int) -> str:
    if degrees == 90:
        return "transpose=1"
    if degrees == 180:
        return "transpose=1,transpose=1"
    if degrees == 270:
        return "transpose=2"
    raise OrientationError("no rotation required")


def _temporary_output_path(path: str) -> str:
    source = Path(path)
    return os.fspath(source.with_name(f"{source.stem}.normalized-{uuid.uuid4().hex}{source.suffix}"))
