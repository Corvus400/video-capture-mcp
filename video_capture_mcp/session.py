from __future__ import annotations

import asyncio
import os
import signal
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, cast

from video_capture_mcp.backends import android, ios, macos
from video_capture_mcp.extractor import extract_frames
from video_capture_mcp.orientation import normalize_video_orientation
from video_capture_mcp.paths import default_output_root
from video_capture_mcp.process_registry import ProcessRegistry


class ProcessLike(Protocol):
    pid: int | None
    returncode: int | None

    async def communicate(self) -> tuple[bytes, bytes]: ...

    def send_signal(self, sig: signal.Signals) -> None: ...

    async def wait(self) -> int: ...


CreateProcess = Callable[..., Awaitable[ProcessLike]]
DEFAULT_CREATE_PROCESS = cast(CreateProcess, asyncio.create_subprocess_exec)


@dataclass
class ActiveSession:
    session_id: str
    session_key: str
    target: str
    started_at: datetime
    video_path: str
    mode: str
    process: ProcessLike
    options: dict[str, Any]
    remote_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "target": self.target,
            "started_at": self.started_at.isoformat(),
            "video_path": self.video_path,
            "mode": self.mode,
            "pid": self.process.pid,
        }


class Session:
    def __init__(
        self,
        *,
        create_process: CreateProcess | None = None,
        run_precheck: bool = True,
        registry_dir: Path | None = None,
    ) -> None:
        self._create_process: CreateProcess = create_process or DEFAULT_CREATE_PROCESS
        self._run_precheck = run_precheck
        self._sessions: dict[str, ActiveSession] = {}
        self._target_index: dict[str, str] = {}
        self._start_lock = asyncio.Lock()
        self._registry = ProcessRegistry(registry_dir)
        self._startup_cleanup_done = False

    async def start_recording(
        self,
        target: str,
        output_path: str | None = None,
        duration_seconds: float | int | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        await self.cleanup_stale_processes()
        self._reap_finished_sessions()
        target = _normalize_target(target)
        recording_options = dict(options or {})
        session_key = _session_key(target, recording_options)
        async with self._start_lock:
            existing_id = self._target_index.get(session_key)
            if existing_id is not None:
                return {
                    "error": "already recording",
                    "existing_session_id": existing_id,
                }

            video_path = (
                _default_output_path(target)
                if output_path is None
                else os.fspath(Path(output_path).expanduser())
            )
            remote_path = None
            if target == "android":
                remote_path = f"/sdcard/video_capture_{uuid.uuid4().hex}.mp4"
                recording_options["_remote_path"] = remote_path
            backend = _backend_for_target(target)
            try:
                if self._run_precheck:
                    await backend.precheck()
                argv = backend.build_command(
                    video_path, duration_seconds, recording_options
                )
                process = await self._create_process(
                    *argv,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception as exc:
                return {"error": str(exc), "target": target}
            mode = "scheduled" if target == "macos" else "manual_stop"
            session_id = uuid.uuid4().hex
            active = ActiveSession(
                session_id=session_id,
                session_key=session_key,
                target=target,
                started_at=datetime.now(timezone.utc),
                video_path=video_path,
                mode=mode,
                process=process,
                options=recording_options,
                remote_path=remote_path,
            )
            self._sessions[session_id] = active
            self._target_index[session_key] = session_id
            self._write_registry()
            return {
                "session_id": session_id,
                "video_path": video_path,
                "mode": mode,
            }

    async def stop_recording(self, session_id: str) -> dict[str, Any]:
        active = self._sessions.get(session_id)
        if active is None:
            return {"error": "unknown session_id", "session_id": session_id}

        try:
            android_stop_exit_code = None
            if active.target == "ios_simulator" and active.process.returncode is None:
                active.process.send_signal(signal.SIGINT)
            if active.target == "android" and active.process.returncode is None:
                android_stop_exit_code = await self._run_command(
                    android.stop_command(active.options)
                )
            await active.process.communicate()
            exit_code = active.process.returncode
            pull_exit_code = None
            cleanup_exit_code = None
            if active.target == "android" and active.remote_path is not None:
                pull_exit_code = await self._run_command(
                    android.pull_command(
                        active.remote_path, active.video_path, active.options
                    )
                )
                cleanup_exit_code = await self._run_command(
                    android.cleanup_command(active.remote_path, active.options)
                )
            orientation_result = await normalize_video_orientation(
                active.video_path,
                active.options.get("orientation"),
                create_process=self._create_process,
                rotate_degrees=active.options.get("rotate_degrees"),
            )
            duration = (datetime.now(timezone.utc) - active.started_at).total_seconds()
            result = {
                "video_path": active.video_path,
                "duration_seconds": duration,
                "exit_code": exit_code,
                "orientation": orientation_result,
            }
            if active.target == "android":
                result["remote_path"] = active.remote_path
                result["android_stop_exit_code"] = android_stop_exit_code
                result["pull_exit_code"] = pull_exit_code
                result["cleanup_exit_code"] = cleanup_exit_code
            return result
        finally:
            self._forget_session(active)

    def list_active_sessions(self) -> dict[str, list[dict[str, Any]]]:
        self._reap_finished_sessions()
        return {"sessions": [session.as_dict() for session in self._sessions.values()]}

    async def cleanup_stale_processes(self) -> dict[str, list[dict[str, Any]]]:
        if self._startup_cleanup_done:
            return {"cleaned": []}
        self._startup_cleanup_done = True
        cleaned = await self._registry.cleanup_dead_servers(self._create_process)
        return {"cleaned": cleaned}

    async def close(self) -> None:
        for session_id in list(self._sessions):
            await self.stop_recording(session_id)
        self._registry.remove_current()

    async def record_and_extract(
        self,
        target: str,
        duration_seconds: float | int,
        output_dir: str,
        *,
        options: dict[str, Any] | None = None,
        extract_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        output = Path(output_dir).expanduser()
        output.mkdir(parents=True, exist_ok=True)
        normalized = _normalize_target(target)
        suffix = ".mp4" if normalized == "android" else ".mov"
        video_path = os.fspath(output / f"recording{suffix}")
        started = await self.start_recording(
            normalized, video_path, duration_seconds, options
        )
        if "error" in started:
            return started
        await asyncio.sleep(duration_seconds)
        stopped = await self.stop_recording(started["session_id"])
        frames = await extract_frames(
            stopped["video_path"],
            os.fspath(output / "frames"),
            **(extract_options or {}),
        )
        return {
            **frames,
            "video_path": stopped["video_path"],
            "recording": stopped,
        }

    async def _run_command(self, argv: list[str]) -> int:
        proc = await self._create_process(
            *argv,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc.returncode or 0

    def _forget_session(self, active: ActiveSession) -> None:
        self._sessions.pop(active.session_id, None)
        if self._target_index.get(active.session_key) == active.session_id:
            self._target_index.pop(active.session_key, None)
        self._write_registry()

    def _reap_finished_sessions(self) -> None:
        for active in list(self._sessions.values()):
            if active.process.returncode is not None:
                self._forget_session(active)

    def _write_registry(self) -> None:
        self._registry.write(
            [
                session.as_dict()
                | {
                    "options": session.options,
                    "remote_path": session.remote_path,
                }
                for session in self._sessions.values()
            ]
        )


def _normalize_target(target: str) -> str:
    normalized = target.strip().lower()
    aliases = {
        "ios": "ios_simulator",
        "ios-simulator": "ios_simulator",
        "simulator": "ios_simulator",
        "mac": "macos",
        "desktop": "macos",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"macos", "ios_simulator", "android"}:
        raise ValueError(f"unsupported target: {target}")
    return normalized


def _backend_for_target(target: str) -> Any:
    if target == "macos":
        return macos
    if target == "ios_simulator":
        return ios
    if target == "android":
        return android
    raise ValueError(f"unsupported target: {target}")


def _session_key(target: str, options: dict[str, Any]) -> str:
    if target == "ios_simulator":
        device = options.get("device") or options.get("udid") or "booted"
        return f"ios_simulator:{device}"
    if target == "android":
        serial = options.get("serial") or "default"
        return f"android:{serial}"
    return target


def _default_output_path(target: str) -> str:
    suffix = ".mp4" if target == "android" else ".mov"
    path = default_output_root() / f"video_capture_{target}_{uuid.uuid4().hex}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.fspath(path)
