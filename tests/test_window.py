from __future__ import annotations

import pytest

from video_capture_mcp.window import WindowError
from video_capture_mcp.window import _escape_applescript


def test_app_name_rejects_applescript_string_injection() -> None:
    with pytest.raises(WindowError):
        _escape_applescript('"; do shell script "harm')


def test_app_name_rejects_newline() -> None:
    with pytest.raises(WindowError):
        _escape_applescript("foo\nharm")
