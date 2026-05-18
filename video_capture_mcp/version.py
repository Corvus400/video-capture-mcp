from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from pathlib import Path

PACKAGE_NAME = "video-capture-mcp"


def source_root() -> Path | None:
    root = Path(__file__).resolve().parents[1]
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        return root
    return None


def source_version() -> str | None:
    root = source_root()
    if root is None:
        return None
    with (root / "pyproject.toml").open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


def installed_version() -> str | None:
    try:
        return metadata_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def current_version() -> str:
    return source_version() or installed_version() or "0+unknown"
