from __future__ import annotations

import asyncio
import ctypes
import ctypes.util
from typing import Any, Iterable


class PointerError(RuntimeError):
    """Pointer movement failed."""


class CGPoint(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
    ]


_kCGEventMouseMoved = 5
_kCGMouseButtonLeft = 0
_kCGHIDEventTap = 0


def move_pointer(x: float | int, y: float | int) -> dict[str, float]:
    point = _point_from_values(x, y)
    _move_pointer_to(point)
    return {"x": point.x, "y": point.y}


async def hover_sequence(points: Iterable[Any], hold_seconds: float = 0.5) -> dict[str, Any]:
    return await move_sequence(points, hold_seconds=hold_seconds)


async def move_sequence(
    points: Iterable[Any],
    *,
    hold_seconds: float = 0.5,
    steps_per_segment: int = 12,
    step_delay_seconds: float = 0.02,
) -> dict[str, Any]:
    if hold_seconds < 0:
        raise PointerError("hold_seconds must be greater than or equal to zero.")
    if steps_per_segment < 1:
        raise PointerError("steps_per_segment must be greater than or equal to one.")
    if step_delay_seconds < 0:
        raise PointerError("step_delay_seconds must be greater than or equal to zero.")
    requested = [_point_from_raw(raw) for raw in points]
    if not requested:
        raise PointerError("points must contain at least one point.")
    moved_count = 0
    previous: CGPoint | None = None
    for point in requested:
        for next_point in _interpolated_points(previous, point, steps_per_segment):
            _move_pointer_to(next_point)
            moved_count += 1
            if step_delay_seconds:
                await asyncio.sleep(step_delay_seconds)
        if hold_seconds:
            await asyncio.sleep(hold_seconds)
        previous = point
    return {
        "points": [{"x": point.x, "y": point.y} for point in requested],
        "moved_count": moved_count,
    }


def _point_from_raw(raw: Any) -> CGPoint:
    if isinstance(raw, dict):
        return _point_from_values(raw.get("x"), raw.get("y"))
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        return _point_from_values(raw[0], raw[1])
    raise PointerError("each point must be a dict with x/y or a two-item list.")


def _point_from_values(x: Any, y: Any) -> CGPoint:
    try:
        point = CGPoint(float(x), float(y))
    except (TypeError, ValueError) as exc:
        raise PointerError("x and y must be numeric.") from exc
    return point


def _interpolated_points(previous: CGPoint | None, point: CGPoint, steps_per_segment: int) -> list[CGPoint]:
    if previous is None or steps_per_segment == 1:
        return [point]
    return [
        CGPoint(
            previous.x + ((point.x - previous.x) * step / steps_per_segment),
            previous.y + ((point.y - previous.y) * step / steps_per_segment),
        )
        for step in range(1, steps_per_segment + 1)
    ]


def _move_pointer_to(point: CGPoint) -> None:
    app_services = _load_application_services()
    _warp_pointer(app_services, point)
    _post_mouse_move(app_services, point)


def _load_application_services() -> ctypes.CDLL:
    app_services_path = ctypes.util.find_library("ApplicationServices")
    if app_services_path is None:
        raise PointerError("ApplicationServices framework was not found.")
    return ctypes.cdll.LoadLibrary(app_services_path)


def _warp_pointer(app_services: ctypes.CDLL, point: CGPoint) -> None:
    app_services.CGAssociateMouseAndMouseCursorPosition.argtypes = [ctypes.c_bool]
    app_services.CGWarpMouseCursorPosition.argtypes = [CGPoint]
    app_services.CGWarpMouseCursorPosition.restype = ctypes.c_int

    app_services.CGAssociateMouseAndMouseCursorPosition(True)
    error = app_services.CGWarpMouseCursorPosition(point)
    if error != 0:
        raise PointerError(f"failed to warp mouse cursor: CGError {error}.")


def _post_mouse_move(app_services: ctypes.CDLL, point: CGPoint) -> None:
    app_services.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    app_services.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    app_services.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    app_services.CFRelease.argtypes = [ctypes.c_void_p]

    event = app_services.CGEventCreateMouseEvent(
        None,
        _kCGEventMouseMoved,
        point,
        _kCGMouseButtonLeft,
    )
    if not event:
        raise PointerError("failed to create mouse move event.")
    try:
        app_services.CGEventPost(_kCGHIDEventTap, event)
    finally:
        app_services.CFRelease(event)
