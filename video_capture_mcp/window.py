from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol


class WindowError(RuntimeError):
    """Window visibility or bounds lookup failed."""


class ProcessLike(Protocol):
    returncode: int | None

    async def communicate(self) -> tuple[bytes, bytes]: ...


CreateProcess = Callable[..., Awaitable[ProcessLike]]


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def area(self) -> int:
        return self.width * self.height

    def as_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "width": self.width,
            "height": self.height,
        }


async def get_window_region(
    app_name: str,
    *,
    padding: int = 0,
    min_visible_ratio: float = 0.8,
    activate: bool = False,
    activation_delay_seconds: float = 0.2,
    create_process: CreateProcess = asyncio.create_subprocess_exec,
) -> dict[str, Any]:
    if not app_name.strip():
        raise WindowError("app_name must not be empty.")
    if min_visible_ratio <= 0 or min_visible_ratio > 1:
        raise WindowError("min_visible_ratio must be greater than 0 and less than or equal to 1.")
    if activation_delay_seconds < 0:
        raise WindowError("activation_delay_seconds must be greater than or equal to zero.")
    if activate:
        await activate_app(app_name, create_process=create_process)
        if activation_delay_seconds:
            await asyncio.sleep(activation_delay_seconds)
    window = await _front_window_bounds(app_name, create_process)
    desktop = await _desktop_bounds(create_process)
    padded = _pad_bounds(window, padding)
    visible = _intersect(padded, desktop)
    visible_ratio = (visible.area / padded.area) if padded.area else 0.0
    is_visible = visible.area > 0 and visible_ratio >= min_visible_ratio
    return {
        "app_name": app_name,
        "window_bounds": window.as_dict(),
        "desktop_bounds": desktop.as_dict(),
        "visible_bounds": visible.as_dict(),
        "visible_ratio": visible_ratio,
        "visible": is_visible,
        "activated": activate,
        "region": {
            "x": visible.left,
            "y": visible.top,
            "width": visible.width,
            "height": visible.height,
        },
    }


async def activate_app(
    app_name: str,
    *,
    create_process: CreateProcess = asyncio.create_subprocess_exec,
) -> dict[str, Any]:
    if not app_name.strip():
        raise WindowError("app_name must not be empty.")
    await _run_osascript(f'tell application "{_escape_applescript(app_name)}" to activate', create_process)
    return {"app_name": app_name, "activated": True}


async def _front_window_bounds(app_name: str, create_process: CreateProcess) -> Bounds:
    script = f'tell application "{_escape_applescript(app_name)}" to get bounds of front window'
    return _parse_bounds(await _run_osascript(script, create_process), "front window")


async def _desktop_bounds(create_process: CreateProcess) -> Bounds:
    return _parse_bounds(
        await _run_osascript('tell application "Finder" to get bounds of window of desktop', create_process),
        "desktop",
    )


async def _run_osascript(script: str, create_process: CreateProcess) -> str:
    proc = await create_process(
        "osascript",
        "-e",
        script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise WindowError(f"osascript failed: {message}")
    return stdout.decode("utf-8", errors="replace").strip()


def _parse_bounds(text: str, label: str) -> Bounds:
    values = [int(match) for match in re.findall(r"-?\d+", text)]
    if len(values) != 4:
        raise WindowError(f"could not parse {label} bounds: {text!r}")
    left, top, right, bottom = values
    if right <= left or bottom <= top:
        raise WindowError(f"{label} bounds must have positive width and height: {text!r}")
    return Bounds(left, top, right, bottom)


def _pad_bounds(bounds: Bounds, padding: int) -> Bounds:
    padding = int(padding)
    return Bounds(
        bounds.left - padding,
        bounds.top - padding,
        bounds.right + padding,
        bounds.bottom + padding,
    )


def _intersect(a: Bounds, b: Bounds) -> Bounds:
    return Bounds(
        max(a.left, b.left),
        max(a.top, b.top),
        max(min(a.right, b.right), max(a.left, b.left)),
        max(min(a.bottom, b.bottom), max(a.top, b.top)),
    )


def _escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
