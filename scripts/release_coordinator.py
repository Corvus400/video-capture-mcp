from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


RELEASE_PR_PREFIX = "chore(main): release "
CI_WORKFLOW = "ci.yml"
CI_GATE_CONTEXT = "ci-gate"
PUBLISH_WORKFLOW = "publish.yml"
HOMEBREW_WORKFLOW = "update-homebrew.yml"
TAP_WORKFLOW = "update-formula.yml"


@dataclass(frozen=True)
class Run:
    database_id: int
    url: str


def run_text(args: list[str], *, check: bool = True) -> str:
    completed = subprocess.run(args, check=check, text=True, capture_output=True)
    return completed.stdout.strip()


def run_json(args: list[str]) -> Any:
    output = run_text(args)
    if not output:
        return None
    return json.loads(output)


def gh_json(args: list[str]) -> Any:
    return run_json(["gh", *args])


def gh(args: list[str]) -> str:
    return run_text(["gh", *args])


def find_release_pr(repo: str) -> dict[str, Any] | None:
    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "number,title,headRefName,headRefOid",
        ],
    )
    for pr in prs:
        if pr["title"].startswith(RELEASE_PR_PREFIX):
            return pr
    return None


def find_release_for_sha(repo: str, sha: str) -> dict[str, Any] | None:
    releases = gh_json(["api", f"repos/{repo}/releases"])
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        if release.get("target_commitish") == sha:
            return release
    return None


def dispatch_workflow(
    repo: str, workflow: str, ref: str, fields: list[str] | None = None
) -> None:
    args = ["workflow", "run", workflow, "--repo", repo, "--ref", ref]
    for field in fields or []:
        args.extend(["-f", field])
    gh(args)


def find_dispatched_run(repo: str, workflow: str, sha: str) -> Run | None:
    runs = gh_json(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            workflow,
            "--event",
            "workflow_dispatch",
            "--limit",
            "30",
            "--json",
            "databaseId,headSha,url,createdAt",
        ],
    )
    for run in runs:
        if run.get("headSha") == sha:
            return Run(database_id=int(run["databaseId"]), url=str(run["url"]))
    return None


def wait_for_dispatched_run(
    repo: str, workflow: str, sha: str, *, attempts: int, delay: int
) -> Run:
    for _ in range(attempts):
        found = find_dispatched_run(repo, workflow, sha)
        if found is not None:
            return found
        time.sleep(delay)
    raise RuntimeError(
        f"could not find {workflow} workflow_dispatch run for {repo}@{sha}"
    )


def wait_for_run_success(repo: str, run_id: int, *, attempts: int, delay: int) -> None:
    for _ in range(attempts):
        run = gh_json(
            [
                "run",
                "view",
                str(run_id),
                "--repo",
                repo,
                "--json",
                "status,conclusion,url",
            ],
        )
        if run["status"] != "completed":
            time.sleep(delay)
            continue
        if run["conclusion"] == "success":
            return
        run_text(
            ["gh", "run", "view", str(run_id), "--repo", repo, "--log-failed"],
            check=False,
        )
        raise RuntimeError(
            f"workflow run failed: {run['url']} conclusion={run['conclusion']}"
        )
    raise RuntimeError(f"workflow run did not complete: {repo} run {run_id}")


def set_success_status(
    repo: str, sha: str, context: str, url: str, description: str
) -> None:
    gh(
        [
            "api",
            f"repos/{repo}/statuses/{sha}",
            "-f",
            "state=success",
            "-f",
            f"context={context}",
            "-f",
            f"target_url={url}",
            "-f",
            f"description={description}",
        ],
    )


def wait_for_pypi(project: str, version: str, *, attempts: int, delay: int) -> None:
    for _ in range(attempts):
        if pypi_version_visible(project, version):
            return
        time.sleep(delay)
    raise RuntimeError(
        f"PyPI project version did not become visible: {project} {version}"
    )


def pypi_version_visible(project: str, version: str) -> bool:
    url = f"https://pypi.org/pypi/{project}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False
    return payload["info"]["version"] == version


def mirror_release_pr_ci(args: argparse.Namespace) -> int:
    release_pr = find_release_pr(args.repo)
    if release_pr is None:
        print("No open release-please PR found; nothing to mirror.")
        return 0

    branch = release_pr["headRefName"]
    sha = release_pr["headRefOid"]
    if args.dry_run:
        print(f"Would dispatch {CI_WORKFLOW} for release PR branch {branch} at {sha}.")
        print(f"Would mirror successful {CI_GATE_CONTEXT} status to {sha}.")
        return 0
    dispatch_workflow(args.repo, CI_WORKFLOW, branch)
    run = wait_for_dispatched_run(
        args.repo, CI_WORKFLOW, sha, attempts=args.find_attempts, delay=args.delay
    )
    wait_for_run_success(
        args.repo, run.database_id, attempts=args.wait_attempts, delay=args.delay
    )
    set_success_status(
        args.repo,
        sha,
        CI_GATE_CONTEXT,
        run.url,
        "ci.yml workflow_dispatch succeeded for release PR",
    )
    return 0


def publish_release(args: argparse.Namespace) -> int:
    release = find_release_for_sha(args.repo, args.sha)
    if release is None:
        print(f"No published release targets {args.sha}; nothing to publish.")
        return 0

    tag = release["tag_name"]
    version = tag.removeprefix("v")
    if args.dry_run:
        pypi_state = (
            "visible" if pypi_version_visible(args.pypi_project, version) else "missing"
        )
        print(f"Found release {tag} for {args.sha}; PyPI state is {pypi_state}.")
        print(
            f"Would dispatch {PUBLISH_WORKFLOW} if PyPI is missing, "
            f"then {HOMEBREW_WORKFLOW}."
        )
        return 0
    if pypi_version_visible(args.pypi_project, version):
        print(
            f"PyPI already has {args.pypi_project} {version}; skipping publish dispatch."
        )
    else:
        dispatch_workflow(args.repo, PUBLISH_WORKFLOW, tag)
        publish_run = wait_for_dispatched_run(
            args.repo,
            PUBLISH_WORKFLOW,
            args.sha,
            attempts=args.find_attempts,
            delay=args.delay,
        )
        wait_for_run_success(
            args.repo,
            publish_run.database_id,
            attempts=args.wait_attempts,
            delay=args.delay,
        )
    wait_for_pypi(
        args.pypi_project, version, attempts=args.pypi_attempts, delay=args.delay
    )

    dispatch_workflow(args.repo, HOMEBREW_WORKFLOW, "main", fields=[f"version={tag}"])
    homebrew_run = wait_for_dispatched_run(
        args.repo,
        HOMEBREW_WORKFLOW,
        args.sha,
        attempts=args.find_attempts,
        delay=args.delay,
    )
    wait_for_run_success(
        args.repo,
        homebrew_run.database_id,
        attempts=args.wait_attempts,
        delay=args.delay,
    )
    return 0


def dispatch_homebrew_tap(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(f"Would dispatch {TAP_WORKFLOW} in {args.tap_repo} for {args.version}.")
        return 0
    dispatch_workflow(
        args.tap_repo, TAP_WORKFLOW, "main", fields=[f"version={args.version}"]
    )
    runs = gh_json(
        [
            "run",
            "list",
            "--repo",
            args.tap_repo,
            "--workflow",
            TAP_WORKFLOW,
            "--event",
            "workflow_dispatch",
            "--limit",
            "10",
            "--json",
            "databaseId,url,createdAt",
        ],
    )
    if not runs:
        raise RuntimeError(f"could not find dispatched tap workflow for {args.version}")
    run = Run(database_id=int(runs[0]["databaseId"]), url=str(runs[0]["url"]))
    wait_for_run_success(
        args.tap_repo, run.database_id, attempts=args.wait_attempts, delay=args.delay
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=None)
    parser.add_argument("--delay", type=int, default=10)
    parser.add_argument("--find-attempts", type=int, default=18)
    parser.add_argument("--wait-attempts", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    mirror = subparsers.add_parser("mirror-release-pr-ci")
    mirror.add_argument("--repo", required=True)
    mirror.set_defaults(func=mirror_release_pr_ci)

    publish = subparsers.add_parser("publish-release")
    publish.add_argument("--repo", required=True)
    publish.add_argument("--sha", required=True)
    publish.add_argument("--pypi-project", required=True)
    publish.add_argument("--pypi-attempts", type=int, default=60)
    publish.set_defaults(func=publish_release)

    tap = subparsers.add_parser("dispatch-homebrew-tap")
    tap.add_argument("--tap-repo", required=True)
    tap.add_argument("--version", required=True)
    tap.set_defaults(func=dispatch_homebrew_tap)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
