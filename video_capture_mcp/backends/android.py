from __future__ import annotations

import asyncio
import os
import re
import uuid
from pathlib import Path
from typing import Any


class BackendError(RuntimeError):
    """Android backend failed."""


async def precheck() -> None:
    proc = await asyncio.create_subprocess_exec(
        "adb",
        "devices",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise BackendError(f"adb devices failed: {message}")
    lines = stdout.decode("utf-8", errors="replace").splitlines()
    if not any(line.strip().endswith("\tdevice") for line in lines):
        raise BackendError("no Android device")


def build_command(
    output_path: str,
    duration_seconds: float | int | None,
    options: dict[str, Any] | None = None,
) -> list[str]:
    Path(output_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    remote_path = remote_path_from_options(options)
    args = ["adb"]
    serial = (options or {}).get("serial")
    if serial:
        args.extend(["-s", str(serial)])
    args.extend(["shell", "screenrecord", "--time-limit", "0"])
    size = (options or {}).get("size")
    if size is not None:
        args.extend(["--size", _format_size(size)])
    bit_rate = (options or {}).get("bit_rate")
    if bit_rate is not None:
        args.extend(["--bit-rate", str(int(bit_rate))])
    args.append(remote_path)
    return args


def remote_path_from_options(options: dict[str, Any] | None = None) -> str:
    remote_path = (options or {}).get("_remote_path")
    if remote_path:
        return str(remote_path)
    return f"/sdcard/video_capture_{uuid.uuid4().hex}.mp4"


def pull_command(
    remote_path: str, output_path: str, options: dict[str, Any] | None = None
) -> list[str]:
    args = ["adb"]
    serial = (options or {}).get("serial")
    if serial:
        args.extend(["-s", str(serial)])
    args.extend(["pull", remote_path, os.fspath(Path(output_path).expanduser())])
    return args


def cleanup_command(
    remote_path: str, options: dict[str, Any] | None = None
) -> list[str]:
    args = ["adb"]
    serial = (options or {}).get("serial")
    if serial:
        args.extend(["-s", str(serial)])
    args.extend(["shell", "rm", remote_path])
    return args


def stop_command(options: dict[str, Any] | None = None) -> list[str]:
    args = ["adb"]
    serial = (options or {}).get("serial")
    if serial:
        args.extend(["-s", str(serial)])
    args.extend(["shell", "pkill", "-2", "screenrecord"])
    return args


def _format_size(size: Any) -> str:
    if isinstance(size, str):
        if not re.fullmatch(r"\d+x\d+", size):
            raise BackendError("options.size must be formatted as WIDTHxHEIGHT.")
        return size
    if isinstance(size, dict):
        width = size.get("width")
        height = size.get("height")
    elif isinstance(size, (list, tuple)) and len(size) == 2:
        width, height = size
    else:
        raise BackendError(
            "options.size must be a WIDTHxHEIGHT string, dict, or two-item list."
        )
    if width is None or height is None:
        raise BackendError("options.size must contain width and height.")
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise BackendError("options.size width and height must be greater than zero.")
    return f"{width}x{height}"
