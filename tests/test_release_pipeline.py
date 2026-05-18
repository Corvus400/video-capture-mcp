from __future__ import annotations

from pathlib import Path

from scripts import release_coordinator


ROOT = Path(__file__).resolve().parents[1]


def test_release_pr_selection_uses_json_prefix(monkeypatch) -> None:
    payload = [
        {
            "number": 1,
            "title": "docs: unrelated",
            "headRefName": "docs/example",
            "headRefOid": "a" * 40,
        },
        {
            "number": 2,
            "title": "chore(main): release 0.5.0",
            "headRefName": "release-please--branches--main",
            "headRefOid": "b" * 40,
        },
    ]

    def fake_run_json(args: list[str]):
        assert "--search" not in args
        return payload

    monkeypatch.setattr(release_coordinator, "gh_json", fake_run_json)

    release_pr = release_coordinator.find_release_pr("owner/repo")
    assert release_pr is not None
    assert release_pr["headRefName"] == "release-please--branches--main"


def test_release_lookup_is_sha_scoped(monkeypatch) -> None:
    releases = [
        {
            "tag_name": "v0.4.0",
            "target_commitish": "old",
            "draft": False,
            "prerelease": False,
        },
        {
            "tag_name": "v0.5.0",
            "target_commitish": "new",
            "draft": False,
            "prerelease": False,
        },
    ]
    monkeypatch.setattr(release_coordinator, "gh_json", lambda args: releases)

    assert (
        release_coordinator.find_release_for_sha("owner/repo", "new")["tag_name"]
        == "v0.5.0"
    )
    assert release_coordinator.find_release_for_sha("owner/repo", "missing") is None


def test_required_check_surface_is_stable_ci_gate_only() -> None:
    workflow = (ROOT / ".github/workflows/release-please.yml").read_text(
        encoding="utf-8"
    )
    coordinator = (ROOT / "scripts/release_coordinator.py").read_text(encoding="utf-8")

    assert "ci-gate" in coordinator
    assert "test-macos (3.11)" not in workflow
    assert "test-macos (3.12)" not in workflow
    assert 'test-build"' not in workflow


def test_release_audit_script_imports() -> None:
    from scripts import release_audit

    assert release_audit.main() == 0
