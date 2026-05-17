from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Image


class ExtractorError(RuntimeError):
    """Frame extraction failed."""


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
    source = os.fspath(Path(video_path).expanduser())
    destination = Path(output_dir).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    for old_frame in destination.glob("frame_*.png"):
        old_frame.unlink()

    filter_chain = _filter_chain(mode, scene_threshold, fps, rotate_degrees)
    pattern = os.fspath(destination / "frame_%04d.png")
    argv = [
        "ffmpeg",
        "-y",
        "-i",
        source,
        "-vf",
        filter_chain,
        "-vsync",
        "vfr",
        pattern,
    ]
    await _run_ffmpeg(argv)
    frame_paths = sorted(os.fspath(path) for path in destination.glob("frame_*.png"))
    if not frame_paths:
        frame_paths = await _extract_first_frame(source, destination, rotate_degrees)

    original_count = len(frame_paths)
    frame_paths = _limit_frames(frame_paths, max_frames)
    dropped_for_max = original_count - len(frame_paths)
    if dropped_for_max:
        keep = set(frame_paths)
        for path in destination.glob("frame_*.png"):
            if os.fspath(path) not in keep:
                path.unlink(missing_ok=True)

    images = [Image(path=path) for path in frame_paths] if inline_images else []
    return {
        "images": images,
        "frame_paths": frame_paths,
        "dropped_for_max": dropped_for_max,
    }


def _filter_chain(
    mode: str,
    scene_threshold: float,
    fps: float | None,
    rotate_degrees: int | None,
) -> str:
    scene_threshold = _finite_float(scene_threshold, "scene_threshold")
    filters: list[str] = []
    if mode == "scene":
        if scene_threshold < 0:
            raise ExtractorError("scene_threshold must be greater than or equal to zero.")
        filters.extend([f"select='gt(scene,{scene_threshold})'", "showinfo"])
    elif mode == "fixed_fps":
        if fps is None:
            raise ExtractorError("fps must be greater than zero for fixed_fps mode.")
        fps = _finite_float(fps, "fps")
        if fps <= 0:
            raise ExtractorError("fps must be greater than zero for fixed_fps mode.")
        filters.append(f"fps={fps}")
    else:
        raise ExtractorError("mode must be 'scene' or 'fixed_fps'.")

    rotate_filter = _rotate_filter(rotate_degrees)
    if rotate_filter is not None:
        filters.append(rotate_filter)
    return ",".join(filters)


def _finite_float(value: float | int, name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ExtractorError(f"{name} must be a finite number.") from exc
    if not math.isfinite(normalized):
        raise ExtractorError(f"{name} must be a finite number.")
    return normalized


def _rotate_filter(rotate_degrees: int | None) -> str | None:
    if rotate_degrees is None or rotate_degrees % 360 == 0:
        return None
    normalized = rotate_degrees % 360
    if normalized == 90:
        return "transpose=1"
    if normalized == 180:
        return "transpose=1,transpose=1"
    if normalized == 270:
        return "transpose=2"
    raise ExtractorError("rotate_degrees must be one of 0, 90, 180, or 270.")


async def _run_ffmpeg(argv: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ExtractorError(
            "ffmpeg failed with exit code "
            f"{proc.returncode}: {stderr.decode('utf-8', errors='replace') or stdout.decode('utf-8', errors='replace')}"
        )


async def _extract_first_frame(source: str, destination: Path, rotate_degrees: int | None) -> list[str]:
    frame = destination / "frame_0001.png"
    filters = []
    rotate_filter = _rotate_filter(rotate_degrees)
    if rotate_filter is not None:
        filters.extend(["-vf", rotate_filter])
    argv = ["ffmpeg", "-y", "-i", source, *filters, "-frames:v", "1", os.fspath(frame)]
    await _run_ffmpeg(argv)
    return [os.fspath(frame)] if frame.exists() else []


def _limit_frames(frame_paths: list[str], max_frames: int) -> list[str]:
    if max_frames <= 0:
        raise ExtractorError("max_frames must be greater than zero.")
    if len(frame_paths) <= max_frames:
        return frame_paths
    if max_frames == 1:
        return [frame_paths[0]]
    last_index = len(frame_paths) - 1
    selected_indexes = {
        round(index * last_index / (max_frames - 1))
        for index in range(max_frames)
    }
    return [path for index, path in enumerate(frame_paths) if index in selected_indexes]
