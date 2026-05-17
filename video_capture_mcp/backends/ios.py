from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any


class BackendError(RuntimeError):
    """iOS Simulator backend failed."""


async def precheck() -> None:
    proc = await asyncio.create_subprocess_exec(
        "xcrun",
        "simctl",
        "list",
        "devices",
        "booted",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    text = stdout.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise BackendError(f"xcrun simctl list devices booted failed: {message}")
    if "Booted" not in text:
        raise BackendError("no booted simulator")


def build_command(
    output_path: str,
    duration_seconds: float | int | None,
    options: dict[str, Any] | None = None,
) -> list[str]:
    Path(output_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    device = (options or {}).get("device") or (options or {}).get("udid") or "booted"
    args = [
        "xcrun",
        "simctl",
        "io",
        str(device),
        "recordVideo",
        "--codec",
        "h264",
    ]
    display = (options or {}).get("display")
    if display is not None:
        if display not in {"internal", "external"}:
            raise BackendError("options.display must be 'internal' or 'external'.")
        args.extend(["--display", display])
    args.extend(["--force", os.fspath(Path(output_path).expanduser())])
    return args
