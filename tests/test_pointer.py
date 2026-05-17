from __future__ import annotations

import pytest

from video_capture_mcp import pointer


def test_move_pointer_uses_normalized_coordinates(monkeypatch) -> None:
    moved: list[tuple[float, float]] = []

    def fake_move(point: pointer.CGPoint) -> None:
        moved.append((point.x, point.y))

    monkeypatch.setattr(pointer, "_move_pointer_to", fake_move)

    result = pointer.move_pointer("10.5", 20)

    assert result == {"x": 10.5, "y": 20.0}
    assert moved == [(10.5, 20.0)]


@pytest.mark.asyncio
async def test_move_sequence_rejects_empty_points() -> None:
    with pytest.raises(pointer.PointerError):
        await pointer.move_sequence([])


@pytest.mark.asyncio
async def test_move_sequence_rejects_bad_timing() -> None:
    with pytest.raises(pointer.PointerError):
        await pointer.move_sequence([{"x": 1, "y": 2}], hold_seconds=-1)
    with pytest.raises(pointer.PointerError):
        await pointer.move_sequence([{"x": 1, "y": 2}], steps_per_segment=0)
    with pytest.raises(pointer.PointerError):
        await pointer.move_sequence([{"x": 1, "y": 2}], step_delay_seconds=-1)


def test_point_from_raw_rejects_bad_shape() -> None:
    with pytest.raises(pointer.PointerError):
        pointer._point_from_raw(["x"])


def test_point_from_values_rejects_non_numeric() -> None:
    with pytest.raises(pointer.PointerError):
        pointer._point_from_values("left", 1)


def test_interpolated_points() -> None:
    start = pointer.CGPoint(0, 0)
    end = pointer.CGPoint(10, 20)

    points = pointer._interpolated_points(start, end, 2)

    assert [(point.x, point.y) for point in points] == [(5.0, 10.0), (10.0, 20.0)]
