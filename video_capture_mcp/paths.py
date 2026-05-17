from __future__ import annotations

import os
import tempfile
from pathlib import Path


OUTPUT_DIR_ENV = "VIDEO_CAPTURE_MCP_OUTPUT_DIR"


def default_output_root() -> Path:
    configured = os.environ.get(OUTPUT_DIR_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "video-capture-mcp"
