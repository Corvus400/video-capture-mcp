from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


class BackendError(RuntimeError):
    """Backend precheck or command construction failed."""


async def precheck() -> None:
    probe_path = Path(tempfile.gettempdir()) / f"_video_capture_tcc_probe_{uuid.uuid4().hex}.mov"
    proc = await asyncio.create_subprocess_exec(
        "screencapture",
        "-V",
        "1",
        str(probe_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    size = probe_path.stat().st_size if probe_path.exists() else 0
    try:
        probe_path.unlink(missing_ok=True)
    except OSError:
        pass

    if proc.returncode != 0 or size == 0:
        python_path = sys.executable
        message = stderr.decode("utf-8", errors="replace").strip()
        raise BackendError(
            "TCC permission required for "
            f"{python_path}. Open System Settings > Privacy & Security > "
            "Screen Recording and add this Python binary. "
            f"screencapture stderr: {message}"
        )


def build_command(
    output_path: str,
    duration_seconds: float | int | None,
    options: dict[str, Any] | None = None,
) -> list[str]:
    if duration_seconds is None:
        raise BackendError("macOS recording requires duration_seconds because screencapture uses -V.")
    if duration_seconds <= 0:
        raise BackendError("duration_seconds must be greater than zero.")

    Path(output_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    args = ["screencapture", "-V", str(int(duration_seconds))]
    region = (options or {}).get("region")
    if region is not None:
        args.extend(["-R", _format_region(region)])
    display = (options or {}).get("display")
    if display is not None:
        args.extend(["-D", str(display)])
    if (options or {}).get("include_clicks"):
        args.append("-k")
    if (options or {}).get("include_audio"):
        args.append("-g")
    args.append(os.fspath(Path(output_path).expanduser()))
    return args


def _format_region(region: Any) -> str:
    if isinstance(region, dict):
        values = [region.get(key) for key in ("x", "y", "width", "height")]
    elif isinstance(region, (list, tuple)):
        values = list(region)
    else:
        raise BackendError("options.region must be a dict or a four-item list.")
    if len(values) != 4 or any(value is None for value in values):
        raise BackendError("options.region must contain x, y, width, and height.")
    ints = [int(value) for value in values]
    if ints[2] <= 0 or ints[3] <= 0:
        raise BackendError("region width and height must be greater than zero.")
    return ",".join(str(value) for value in ints)
