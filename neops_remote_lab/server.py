"""FastAPI remote Netlab lab manager service."""

from __future__ import annotations

import asyncio
import functools
import logging
import shutil
import tempfile
import time
import signal
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, List, TypeVar, cast
from types import FrameType
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status, Response

from neops_remote_lab.netlab.lab_manager import LabManager
from neops_remote_lab import __version__

from neops_remote_lab.models import (
    ActiveSessionResponseDto,
    AcquireResponseDto,
    CreateSessionResponseDto,
    DeviceInfoDto,
    LabStatusDto,
    SessionInfoDto,
    SessionState,
    SessionStatusResponseDto,
)

_log = logging.getLogger("remote-lab-server")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown"""
    # Startup
    _log.info("Remote Lab Manager starting up...")

    # Clean up any stale netlab instances from previous server runs
    _log.info("Performing startup cleanup of stale netlab instances...")
    try:
        await _run_blocking(LabManager.cleanup, default_instance=True, reason="server-startup")
        _log.info("Startup cleanup completed successfully")
    except Exception as e:
        _log.warning("Startup cleanup encountered an error (this is normal if no default instance was running): %s", e)

    cleanup_task = asyncio.create_task(_cleanup_loop_async())
    _log.info("Remote Lab Manager startup complete")

    yield

    # Shutdown
    _log.info("Remote Lab Manager shutting down...")
    _SHUTDOWN_EVENT.set()
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        _log.info("Cleanup task was cancelled.")

    # Clean up any remaining sessions
    if _SESSIONS:
        _log.info("Cleaning up %d remaining sessions...", len(_SESSIONS))
        # Force cleanup of active labs
        for session_id in list(_SESSIONS.keys()):
            _delete_session(session_id, reason="server-shutdown")
        try:
            await _run_blocking(LabManager.cleanup, reason="server-shutdown")
        except Exception as e:
            _log.error("Error during final cleanup: %s", e)

    _log.info("Remote Lab Manager shutdown complete")


app = FastAPI(
    title="Netlab Remote Lab Manager",
    version=__version__,
    description="Manages a queue of exclusive sessions for Netlab topologies.",
    lifespan=lifespan,
)


# --- Global State Tracking ---
_SERVER_START_TIME = time.time()
_SHUTDOWN_EVENT = asyncio.Event()

# --- Session & Queue State ---
_SESSION_QUEUE: list[str] = []
_SESSIONS: dict[str, SessionInfoDto] = {}
_SESSION_CLEANUP_INTERVAL = 5  # seconds between cleanup runs
_WAITING_SESSION_TIMEOUT = 600  # seconds until a waiting session is dropped (lab start can take minutes)
_ACTIVE_SESSION_STALE = 300  # seconds of heartbeat inactivity

# Header constant used by client for session propagation
HEADER_SESSION_ID = "X-Session-ID"


# --- Server Lifecycle Events ---


# Signal handlers are now set up at module level for immediate effect
def signal_handler(signum: int, frame: FrameType | None) -> None:
    _log.warning("Received signal %d, shutting down gracefully...", signum)
    _log.info("Active sessions at shutdown: %s", list(_SESSIONS.keys()))
    _SHUTDOWN_EVENT.set()


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


@app.get("/debug/health", status_code=status.HTTP_200_OK)
async def debug_health() -> dict[str, float | int | str]:
    """Detailed health endpoint for debugging server responsiveness."""
    current_time = time.time()
    uptime = current_time - _SERVER_START_TIME

    return {
        "status": "ok",
        "timestamp": current_time,
        "uptime": uptime,
        "sessions": len(_SESSIONS),
        "queue_length": len(_SESSION_QUEUE),
    }


# --- Helper Functions --------------------------------------------------------


def _tmp_upload_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="remote_netlab_upload_"))


def _save_uploads(topology_file: UploadFile, extra_files: list[UploadFile]) -> Path:
    workdir = _tmp_upload_dir()
    if topology_file.filename is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Topology file must have a filename")
    topo_dest = workdir / cast(str, topology_file.filename)
    with topo_dest.open("wb") as f:
        shutil.copyfileobj(topology_file.file, f)

    for item in extra_files:
        if item.filename is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Extra file must have a filename")
        dest = workdir / cast(str, item.filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            shutil.copyfileobj(item.file, f)

    return topo_dest


# ------------------------------------------------------------------ Async helpers

T = TypeVar("T")


async def _run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run *func* in a thread so it does not block the event loop.

    Only heavyweight operations that ultimately call *netlab* (e.g. `LabManager.try_acquire`,
    `LabManager.cleanup`) should use this helper.  Lightweight metadata look-ups such as
    `LabManager.status()` are left synchronous to avoid the overhead of thread hopping.
    """
    _log.debug("Running blocking operation: %s", func.__name__)
    start_time = time.time()
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
        duration = time.time() - start_time
        _log.debug("Blocking operation %s succeeded in %.3fs", func.__name__, duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        _log.error("Blocking operation %s failed after %.3fs: %s", func.__name__, duration, e)
        raise


# Promotion helper keeps queue FIFO: first element must be ACTIVE
def _promote_if_needed() -> None:
    """Ensure the first session in the queue is marked ACTIVE.

    * FIFO semantics preserved – order of `_SESSION_QUEUE` never changes.
    * Orphaned IDs are popped.
    * When a new ACTIVE session is promoted log the topology (if available).
    """
    _log.debug("_promote_if_needed: queue=%s", _SESSION_QUEUE)

    while _SESSION_QUEUE:
        sid = _SESSION_QUEUE[0]
        sess = _SESSIONS.get(sid)
        if sess is None:
            _log.debug("Dropping orphaned session %s from queue head", sid)
            _SESSION_QUEUE.pop(0)
            continue

        if sess.status == SessionState.ACTIVE:
            # Invariant satisfied
            _log.debug("_promote_if_needed: session %s already active", sid[:8])
            return

        # Promote waiting session to active
        sess.status = SessionState.ACTIVE
        topo = sess.topology_name or "<unknown>"
        _log.info("Session %s promoted to ACTIVE (topology=%s)", sid[:8], topo)
        return


# ------------------------------------------------------------------ Session helpers


def _delete_session(sid: str, *, reason: str) -> None:
    """Remove session from tracking structures and log."""
    _log.debug("_delete_session: %s reason=%s", sid[:8], reason)

    if sid in _SESSION_QUEUE:
        _SESSION_QUEUE.remove(sid)
        _log.debug("Removed session %s from queue", sid[:8])

    sess = _SESSIONS.pop(sid, None)
    if sess:
        _log.info("Session %s removed (%s, topology=%s)", sid[:8], reason, sess.topology_name)
    else:
        _log.warning("Attempted to delete non-existent session %s", sid[:8])


# --- Session Management ---


async def _cleanup_stale_sessions_async() -> None:
    # Skip cleanup entirely if no sessions exist
    if not _SESSIONS:
        return

    _log.debug("Running session cleanup, %d sessions tracked", len(_SESSIONS))

    now = time.time()
    stale_ids: list[str] = []
    for sid, sess in _SESSIONS.items():
        timeout = _WAITING_SESSION_TIMEOUT if sess.status == SessionState.WAITING else _ACTIVE_SESSION_STALE
        age = now - sess.last_seen_at

        if age > timeout:
            stale_ids.append(sid)
            _log.debug("Session %s is stale (age=%.1fs, timeout=%.1fs)", sid[:8], age, timeout)

    for sid in stale_ids:
        _log.warning("Removing stale session %s due to inactivity", sid[:8])
        session = _SESSIONS.get(sid)
        if not session:
            continue
        was_active = session.status == SessionState.ACTIVE
        _delete_session(sid, reason="stale")
        if was_active:
            _log.info("Cleaning up lab for stale active session %s", sid[:8])
            await _run_blocking(LabManager.cleanup, reason=f"stale-session-{sid}")
            _promote_if_needed()


async def _cleanup_loop_async() -> None:
    """Background task: periodically purge stale sessions and labs."""
    _log.info("Starting session cleanup task (interval=%ds)", _SESSION_CLEANUP_INTERVAL)
    while not _SHUTDOWN_EVENT.is_set():
        try:
            await _cleanup_stale_sessions_async()
        except Exception as e:
            _log.error("Error in cleanup loop: %s", e)

        # Use adaptive sleep interval: longer when no sessions, shorter when active
        if not _SESSIONS:
            sleep_interval = _SESSION_CLEANUP_INTERVAL * 6  # 30 seconds when idle
        elif len(_SESSIONS) == 1 and list(_SESSIONS.values())[0].status == SessionState.ACTIVE:
            sleep_interval = _SESSION_CLEANUP_INTERVAL * 3  # 15 seconds with one active session
        else:
            sleep_interval = _SESSION_CLEANUP_INTERVAL  # 5 seconds when busy

        try:
            await asyncio.sleep(sleep_interval)
        except asyncio.CancelledError:
            _log.info("Session cleanup task cancelled.")
            break


# --- API Endpoints ---


@app.post("/session", response_model=CreateSessionResponseDto, status_code=status.HTTP_201_CREATED)
async def create_session() -> CreateSessionResponseDto:
    sid = str(uuid.uuid4())
    now = time.time()
    position = len(_SESSION_QUEUE)
    session = SessionInfoDto(
        id=sid,
        status=SessionState.WAITING,
        position=position,
        created_at=now,
        last_seen_at=now,
    )
    _SESSIONS[sid] = session
    _SESSION_QUEUE.append(sid)
    _promote_if_needed()

    _log.info("Created session %s at queue position %d", sid[:8], position)
    return CreateSessionResponseDto(session_id=sid, position=position)


@app.get("/session/{session_id}", response_model=SessionStatusResponseDto)
async def get_session_status(session_id: str) -> SessionStatusResponseDto:
    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    session.last_seen_at = time.time()
    # Calculate position from the queue (active session is position 0)
    try:
        session.position = _SESSION_QUEUE.index(session_id)
    except ValueError:
        session.position = -1  # Session not in queue (should not happen normally)
        _log.error("Session %s not found in queue!", session_id[:8])

    return SessionStatusResponseDto(status=session.status, position=session.position)


@app.get("/active-session", response_model=ActiveSessionResponseDto)
async def get_active_session() -> ActiveSessionResponseDto:
    """Get the currently active session (first in queue)."""
    if not _SESSION_QUEUE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active session")

    active_session_id = _SESSION_QUEUE[0]
    session = _SESSIONS.get(active_session_id)
    if not session:
        # Clean up orphaned queue entry
        _log.warning("Found orphaned session %s in queue, cleaning up", active_session_id[:8])
        _SESSION_QUEUE.pop(0)
        _promote_if_needed()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active session")

    session.last_seen_at = time.time()
    return ActiveSessionResponseDto(session_id=active_session_id, status=session.status, position=0)


@app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str) -> Response:
    # Check if server is shutting down
    if _SHUTDOWN_EVENT.is_set():
        _log.warning("Server is shutting down, handling session deletion gracefully")
        # Still try to delete the session but don't fail if cleanup fails
        if session_id in _SESSIONS:
            _delete_session(session_id, reason="client-end-during-shutdown")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    is_active = session.status == SessionState.ACTIVE
    _delete_session(session_id, reason="client-end")

    if is_active:
        _log.info("Active session %s ended, cleaning up lab.", session_id[:8])
        try:
            await _run_blocking(LabManager.cleanup, reason=f"session-end-{session_id}")
            _promote_if_needed()
        except Exception as e:
            _log.error("Error during lab cleanup for session %s: %s", session_id[:8], e)
            # Don't raise the error - still return success since session was deleted
            # The client doesn't need to know about cleanup failures

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Lab Management Endpoints (Session-Protected) ---


def _get_active_session(x_session_id: str = Header(..., alias=HEADER_SESSION_ID)) -> SessionInfoDto:
    _log.debug("_get_active_session check for %s", x_session_id[:8])

    session = _SESSIONS.get(x_session_id)
    if not session:
        _log.warning("Session %s not found in _get_active_session", x_session_id[:8])
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if session.status != SessionState.ACTIVE:
        _log.warning("Session %s not active (status=%s) in _get_active_session", x_session_id[:8], session.status.value)
        raise HTTPException(status.HTTP_423_LOCKED, "Session is not active")

    _log.debug("Session %s validated as active", x_session_id[:8])
    return session


@app.post("/lab", response_model=AcquireResponseDto)
async def acquire_lab(
    session: SessionInfoDto = Depends(_get_active_session),
    topology: UploadFile = File(...),
    reuse: bool = Form(True),
    extra_files: List[UploadFile] = File(default_factory=list),
) -> AcquireResponseDto:
    session.last_seen_at = time.time()
    if topology.filename is None or not topology.filename.lower().endswith((".yml", ".yaml")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Topology must be a .yml or .yaml file")

    filename = cast(str, topology.filename)
    try:
        saved_topo = _save_uploads(topology, extra_files)
        _log.info("Saved topology %s to %s", filename, saved_topo)
    finally:
        topology.file.close()
        for f in extra_files:
            f.file.close()

    # Store topology name for logging
    session.topology_name = filename

    # Run potentially long-running netlab operations in a background thread
    _log.info("Starting lab acquisition for session %s (topology=%s, reuse=%s)", session.id[:8], filename, reuse)

    devices = await _run_blocking(LabManager.try_acquire, saved_topo, reuse=reuse)
    if devices is None:
        raise HTTPException(status.HTTP_423_LOCKED, "Lab currently busy")

    reused = LabManager.status().ref_count > 1
    return AcquireResponseDto(reused=reused, devices=devices)


@app.get("/lab", response_model=LabStatusDto)
async def get_lab_status(session: SessionInfoDto = Depends(_get_active_session)) -> LabStatusDto:
    session.last_seen_at = time.time()
    return LabManager.status(include_devices=True)


@app.post("/lab/release", status_code=status.HTTP_204_NO_CONTENT)
async def release_lab(session: SessionInfoDto = Depends(_get_active_session)) -> Response:
    session.last_seen_at = time.time()
    if not LabManager.has_running_lab():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No lab running")

    LabManager.release_current()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/lab", status_code=status.HTTP_202_ACCEPTED)
async def destroy_lab(
    force: bool = True,
    session: SessionInfoDto = Depends(_get_active_session),
) -> Response:
    session.last_seen_at = time.time()
    if not LabManager.has_running_lab():
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if not force and LabManager.status().ref_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Lab still in use")

    await _run_blocking(LabManager.cleanup, reason="api-destroy")
    return Response(status_code=status.HTTP_202_ACCEPTED)


@app.get("/lab/devices", response_model=list[DeviceInfoDto])
async def list_devices(session: SessionInfoDto = Depends(_get_active_session)) -> list[DeviceInfoDto]:
    session.last_seen_at = time.time()
    if not LabManager.has_running_lab():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No lab running")

    devices = LabManager.current_devices()
    return devices


@app.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
async def healthz() -> Response:
    """Liveness probe – returns 204 with zero body if service is up."""
    # Don't log healthz requests as they're too frequent
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------- Heartbeat


@app.post("/session/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def heartbeat(x_session_id: str = Header(..., alias=HEADER_SESSION_ID)) -> Response:
    """Heartbeat endpoint – updates `last_seen_at` of a session.

    The session ID **must** be provided in the `X-Session-ID` header to keep the
    URL space clean (no path parameters). Returns 204 on success.
    """
    session = _SESSIONS.get(x_session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    session.last_seen_at = time.time()
    _log.debug("Heartbeat for session %s (topology=%s)", x_session_id[:8], session.topology_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
