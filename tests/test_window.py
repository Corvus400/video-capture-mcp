from __future__ import annotations

import pytest

from video_capture_mcp import window
from video_capture_mcp.window import WindowError
from video_capture_mcp.window import _escape_applescript


def test_app_name_rejects_applescript_string_injection() -> None:
    with pytest.raises(WindowError):
        _escape_applescript('"; do shell script "harm')


def test_app_name_rejects_newline() -> None:
    with pytest.raises(WindowError):
        _escape_applescript("foo\nharm")


def test_parse_bounds() -> None:
    bounds = window._parse_bounds("100, -1302, 1300, -26", "front window")

    assert bounds.as_dict() == {
        "left": 100,
        "top": -1302,
        "right": 1300,
        "bottom": -26,
        "width": 1200,
        "height": 1276,
    }


def test_intersect_calculates_visible_bounds() -> None:
    result = window._intersect(
        window.Bounds(3000, 100, 3800, 700),
        window.Bounds(0, 0, 3440, 1440),
    )

    assert result.as_dict() == {
        "left": 3000,
        "top": 100,
        "right": 3440,
        "bottom": 700,
        "width": 440,
        "height": 600,
    }


@pytest.mark.asyncio
async def test_activate_app_runs_escaped_osascript() -> None:
    scripts: list[str] = []

    class FakeCommunicateProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_create_process(*args, **kwargs):
        scripts.append(args[2])
        return FakeCommunicateProcess()

    result = await window.activate_app("Finder", create_process=fake_create_process)

    assert result == {"app_name": "Finder", "activated": True}
    assert scripts == ['tell application "Finder" to activate']
