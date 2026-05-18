from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *markers: str) -> list[str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    return [f"{path}: missing {marker}" for marker in markers if marker not in text]


def main() -> int:
    failures: list[str] = []
    failures += require(
        ".github/workflows/ci.yml",
        "ci-gate:",
        "needs.lint.result",
        "needs.test-macos.result",
        "needs.test-build.result",
    )
    failures += require(
        ".github/workflows/release-please.yml",
        "scripts/release_coordinator.py mirror-release-pr-ci",
        "scripts/release_coordinator.py publish-release",
        "actions: write",
        "statuses: write",
    )
    failures += require(
        ".github/workflows/update-homebrew.yml",
        "scripts/release_coordinator.py dispatch-homebrew-tap",
        "HOMEBREW_TAP_TOKEN",
    )
    failures += require(
        "scripts/release_coordinator.py",
        'CI_GATE_CONTEXT = "ci-gate"',
        "wait_for_pypi",
        "dispatch-homebrew-tap",
    )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
