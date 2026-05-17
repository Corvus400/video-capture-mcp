from __future__ import annotations

import stat

from video_capture_mcp.process_registry import ProcessRegistry


def test_registry_file_is_0600(tmp_path) -> None:
    registry = ProcessRegistry(tmp_path)

    registry.write([
        {
            "session_id": "session-1",
            "target": "macos",
            "started_at": "2026-05-18T00:00:00+00:00",
            "video_path": "/tmp/video.mov",
            "mode": "scheduled",
            "pid": 1234,
        }
    ])

    registry_file = next(tmp_path.glob("server-*.json"))

    assert stat.S_IMODE(registry_file.stat().st_mode) == 0o600
