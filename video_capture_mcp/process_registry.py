from __future__ import annotations

import asyncio
import json
import os
import signal
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from video_capture_mcp.backends import android


class ProcessLike(Protocol):
    returncode: int | None

    async def communicate(self) -> tuple[bytes, bytes]: ...

    async def wait(self) -> int: ...


CreateProcess = Callable[..., Awaitable[ProcessLike]]


class ProcessRegistry:
    def __init__(self, registry_dir: Path | None = None) -> None:
        self._server_pid = os.getpid()
        self._registry_dir = (
            registry_dir
            or Path.home() / "Library" / "Caches" / "video-capture-mcp" / "sessions"
        )
        self._registry_path = self._registry_dir / f"server-{self._server_pid}.json"

    def write(self, sessions: list[dict[str, Any]]) -> None:
        if not sessions:
            self.remove_current()
            return
        try:
            self._registry_dir.mkdir(parents=True, exist_ok=True)
            self._registry_dir.chmod(0o700)
        except OSError:
            return
        payload = {
            "server_pid": self._server_pid,
            "sessions": sessions,
        }
        tmp_path = self._registry_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            tmp_path.chmod(0o600)
            tmp_path.replace(self._registry_path)
            self._registry_path.chmod(0o600)
        except OSError:
            _unlink_quietly(tmp_path)

    def remove_current(self) -> None:
        try:
            self._registry_path.unlink(missing_ok=True)
        except OSError:
            pass

    async def cleanup_dead_servers(
        self, create_process: CreateProcess
    ) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        if not self._registry_dir.exists():
            return cleaned
        for path in sorted(self._registry_dir.glob("server-*.json")):
            payload = _load_registry(path)
            if payload is None:
                _unlink_quietly(path)
                continue
            server_pid = int(payload.get("server_pid") or 0)
            if server_pid == self._server_pid or _pid_is_alive(server_pid):
                continue
            for entry in payload.get("sessions", []):
                cleaned.append(await _cleanup_entry(entry, create_process))
            _unlink_quietly(path)
        return cleaned


def _load_registry(path: Path) -> dict[str, Any] | None:
    try:
        stat = path.stat()
        if stat.st_uid != os.getuid():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None


async def _cleanup_entry(
    entry: dict[str, Any], create_process: CreateProcess
) -> dict[str, Any]:
    target = str(entry.get("target") or "")
    pid = _optional_int(entry.get("pid"))
    result: dict[str, Any] = {
        "session_id": entry.get("session_id"),
        "target": target,
        "pid": pid,
    }
    if target in {"ios_simulator", "macos"} and pid is not None:
        result["signal_sent"] = _send_sigint(pid)
        return result
    if target == "android":
        options = dict(entry.get("options") or {})
        remote_path = entry.get("remote_path")
        result["android_stop_exit_code"] = await _run_command(
            android.stop_command(options), create_process
        )
        if isinstance(remote_path, str) and remote_path:
            video_path = str(entry.get("video_path") or "")
            if video_path:
                result["pull_exit_code"] = await _run_command(
                    android.pull_command(remote_path, video_path, options),
                    create_process,
                )
            result["cleanup_exit_code"] = await _run_command(
                android.cleanup_command(remote_path, options), create_process
            )
        return result
    result["skipped"] = "unsupported target"
    return result


async def _run_command(argv: list[str], create_process: CreateProcess) -> int:
    try:
        proc = await create_process(
            *argv,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc.returncode or 0
    except Exception:
        return -1


def _send_sigint(pid: int) -> bool:
    if not _pid_is_alive(pid):
        return False
    try:
        os.kill(pid, signal.SIGINT)
        return True
    except OSError:
        return False


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
