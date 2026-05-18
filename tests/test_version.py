from __future__ import annotations

import tomllib
from importlib.metadata import version as metadata_version
from pathlib import Path

from video_capture_mcp import __version__
from video_capture_mcp.version import PACKAGE_NAME


def test_runtime_version_matches_pyproject_source() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"

    with pyproject_path.open("rb") as file:
        pyproject_version = tomllib.load(file)["project"]["version"]

    assert __version__ == pyproject_version


def test_installed_metadata_matches_runtime_version() -> None:
    assert metadata_version(PACKAGE_NAME) == __version__
