"""Netlab laboratory lifecycle manager used by both local and remote tests.

The **one-lab rule** (Netlab limitation) is enforced process-wide as well as
across multiple pytest worker processes via :pydata:`GLOBAL_LOCK`.

Key features
============
1. Exactly one active lab at any time per host.
2. Reference counting – optional *reuse* of the same topology (equality check by comparing hash of content) for faster tests.
3. Non-blocking :pyfunc:`try_acquire` used by the remote server to implement an
   HTTP 423 response while keeping the original blocking :pyfunc:`acquire` for
   local tests.
4. Helper :pyfunc:`status` for introspection without touching private
   attributes.
"""

from __future__ import annotations

import atexit
import hashlib
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from filelock import FileLock

from neops_remote_lab.netlab.connector import inspect_node, list_nodes, run_netlab
from neops_remote_lab.models import DeviceInfoDto, LabStatusDto as ApiLabStatus

__all__ = [
    "LabManager",
    "GLOBAL_LOCK",
]

WAIT_INTERVAL = 2  # seconds between acquire retries

_log = logging.getLogger(__name__)

# A system-wide file lock guarantees exclusivity across multiple processes.
GLOBAL_LOCK = FileLock(str(Path(tempfile.gettempdir()) / "netlab_pytest.lock"))


def _compute_file_sha256(path: Path, *, chunk_size: int = 1 << 20) -> str:
    """Return SHA-256 hex digest of the file at path (chunked, memory efficient)."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def prepare_workdir(src: Path) -> Path:
    """
    Copy src (file) into a brand-new temporary directory.

    netlab insists on operating in an empty directory; copying guarantees a
    clean workspace and avoids polluting your repo.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix=f"netlab_topo_{src.stem}_"))

    # only accept yml files
    if src.is_file() and src.suffix.lower() == ".yml":
        shutil.copy2(src, tmpdir / src.name)
    else:
        raise ValueError("Topology must be a .yml file")
    # TODO support directories with a `topology.yml` file inside

    _log.debug("Topology copied to %s", tmpdir)
    return tmpdir


# ──────────────────────────────────────────────────────────────────────────────
# LabManager
# ──────────────────────────────────────────────────────────────────────────────
#
# Netlab itself supports only a single running topology per host.  The
# LabManager therefore enforces **process-wide** and **cross-process**
# exclusivity:
#
# • At any instant there is at most one *active* lab ("current lab").
# • Tests that request the same topology may share that lab (opt-in via
#   `reuse=True`).  Reference counting keeps track of how many tests are still
#   using the lab.
# • As soon as a *different* topology is requested, the current lab is torn
#   down (if it is no longer in use) before a new one starts.
# • When a test signals it is done (`release()`), the lab becomes *idle* (but
#   still running) until either another test re-attaches or a different
#   topology is required.
# • A global `FileLock` serialises access across *multiple* pytest worker
#   processes.
#
# The implementation keeps a *single* handle instead of a dict – making the
# one-lab rule explicit in the code structure.


class LabManager:
    _current_topo: Path | None = None  # full resolved path of running lab (source file)
    _current_topo_hash: str | None = None  # SHA-256 fingerprint of topology content
    _handle: _Handle | None = None  # metadata + devices for the running lab

    class _Handle:
        """Internal record describing the currently running lab."""

        def __init__(self, workdir: Path, devices: List[DeviceInfoDto]) -> None:
            self.workdir = workdir
            self.devices = devices
            self.ref = 1  # how many tests are using this lab

    @classmethod
    def _start(cls, topo: Path) -> List[DeviceInfoDto]:
        """Start a new Netlab lab for *topo* and remember it as the current one."""
        # Ensure no stale 'default' instance from previous runs is still active. While the GLOBAL_LOCK
        # prevents concurrent *pytest* workers from stepping on each other, our CI runners are long-living and
        # might still have a lab that was started by an earlier job (e.g. if a previous test crashed before
        # teardown).  Trying to start a new topology while such a lab exists fails with
        #   "It looks like the lab instance 'default' is already running".
        # We therefore unconditionally try to clean up that default instance first. The call is made with
        # ``expected_failure=True`` so it silently succeeds when no lab is running.
        cls._terminate_default_netlab_instance(reason="startup-sanity-check")

        # Store topology identity (hash) for reuse detection
        cls._current_topo = topo
        cls._current_topo_hash = _compute_file_sha256(topo)

        workdir = prepare_workdir(topo)
        _log.info("Starting lab %s - this may take several minutes...", topo.name)
        run_netlab(["up", topo.name], cwd=workdir)

        node_names = list_nodes(cwd=workdir)
        devices = [DeviceInfoDto(name=n, raw=inspect_node(n, cwd=workdir)) for n in node_names]

        cls._handle = LabManager._Handle(workdir, devices)

        _log.info("Lab %s started (%d devices)", topo.name, len(devices))
        return devices

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def acquire(cls, topo: Path, *, reuse: bool = True) -> List[DeviceInfoDto]:
        """Return a list of `DeviceInfoDto` objects for *topo*.

        Parameters
        ----------
        topo
            Path to the topology YAML file.
        reuse
            If *True*, an already running lab for the *same* topology will be
            reused.  If *False*, the caller requests an exclusive lab and will
            therefore wait until the current lab (if any) is fully released
            before a fresh one is spun up.
        """

        topo = topo.resolve()

        while True:
            devices = cls.try_acquire(topo, reuse=reuse)
            if devices is not None:
                return devices

            _log.debug("Lab busy – waiting %.1fs", WAIT_INTERVAL)
            time.sleep(WAIT_INTERVAL)

    @classmethod
    def try_acquire(cls, topo: Path, *, reuse: bool = True) -> List[DeviceInfoDto] | None:
        """Non-blocking variant of acquire.

        Returns devices if the lab is available (reused or freshly started) or
        ``None`` if currently busy.
        """
        topo = topo.resolve()

        new_hash = _compute_file_sha256(topo)
        with GLOBAL_LOCK:
            # 1. No lab → start
            if cls._handle is None:
                _log.info("No active lab – starting %s", topo.name)
                return cls._start(topo)

            # 2. Same topology content --------------------------------------------------
            if cls._current_topo_hash == new_hash:
                if reuse:
                    cls._handle.ref += 1
                    _log.info("Re-using lab %s (ref=%d)", (cls._current_topo or topo).name, cls._handle.ref)
                    return cls._handle.devices

                if cls._handle.ref == 0:
                    _log.info("Exclusive request – restarting idle lab %s", (cls._current_topo or topo).name)
                    cls._terminate_current(reason="exclusive-request")
                    return cls._start(topo)

                return None  # busy

            # 3. Different topology content -------------------------------------------
            if cls._handle.ref == 0:
                current_name = cls._current_topo.name if cls._current_topo else "<unknown>"
                _log.info("Switching topology from %s to %s", current_name, topo.name)
                cls._terminate_current(reason="topology-switch")
                return cls._start(topo)

            return None  # busy

    @classmethod
    def status(cls, *, include_devices: bool = False) -> ApiLabStatus:
        """Return status information about the current lab."""

        running = cls._handle is not None
        devices: List[DeviceInfoDto] = cls._handle.devices if (include_devices and cls._handle) else []

        return ApiLabStatus(
            running=running,
            topology=str(cls._current_topo) if cls._current_topo else None,
            ref_count=cls._handle.ref if cls._handle else 0,
            devices=devices,
            netlab_status=None,
        )

    @classmethod
    def release(cls, topo: Path) -> None:
        topo = topo.resolve()
        with GLOBAL_LOCK:
            # If callers pass a different path with same content, accept it
            same_content = False
            try:
                same_content = cls._current_topo_hash == _compute_file_sha256(topo)
            except Exception:  # pragma: no cover - release on missing files should be no-op
                same_content = False

            if not same_content and cls._current_topo != topo:
                _log.error("Release called for non-current topo %s (current %s)", topo, cls._current_topo)
                return

            assert cls._handle is not None
            cls._handle.ref -= 1

            if cls._handle.ref < 0:
                _log.error("Reference counter underflow for topo %s", topo.name)
                cls._handle.ref = 0

            # When ref hits 0 the lab becomes idle. It remains running until a
            # different topology is requested or the interpreter exits.
            if cls._handle.ref == 0:
                _log.info("Lab %s became idle – awaiting next user or teardown (refcount=0)", topo.name)

    # ------------------------------------------------------------------ internal helpers
    @classmethod
    def _terminate_current(cls, reason: str | None = None) -> None:
        """Tear down the currently running lab unconditionally. Caller must hold GLOBAL_LOCK."""
        if cls._handle is None:
            return

        topo = cls._current_topo or Path("<unknown>")
        _log.info("Tearing down lab %s (reason: %s)", topo.name, reason or "unknown")
        try:
            run_netlab(["down", "--cleanup"], cwd=cls._handle.workdir)
        finally:
            shutil.rmtree(cls._handle.workdir, ignore_errors=True)
            cls._handle = None
            cls._current_topo = None
            cls._current_topo_hash = None

    @classmethod
    def _terminate_default_netlab_instance(cls, reason: str | None = None) -> None:
        """Tear down default netlab instance unconditionally. Caller must hold GLOBAL_LOCK."""
        _log.info("Tearing down default lab instance (reason: %s)", reason or "unknown")
        try:
            run_netlab(["down", "--instance", "default", "--cleanup"], cwd=Path.cwd(), expected_failure=True)
        except Exception as e:
            _log.debug("Default instance cleanup failed (this is normal if no instance was running): %s", e)
            # Don't re-raise - this is expected if no default instance exists

    # ------------------------------------------------------------------ cleanup helper
    @staticmethod
    def cleanup(*, default_instance: bool = False, silent: bool = False, reason: str = "manual-cleanup") -> None:
        """Tear down labs based on the specified target."""

        if silent:
            logging.disable(logging.CRITICAL)

        try:
            with GLOBAL_LOCK:
                if default_instance:
                    LabManager._terminate_default_netlab_instance(reason=reason)
                else:
                    LabManager._terminate_current(reason=reason)
        finally:
            if silent:
                logging.disable(logging.NOTSET)

    # ------------------------------------------------------------------ extras
    @classmethod
    def current_topology(cls) -> Optional[Path]:
        """Return the path of the currently running topology (or None)."""
        return cls._current_topo

    @classmethod
    def current_devices(cls) -> List[DeviceInfoDto]:
        """Return a copy of the current device list (empty if no lab)."""
        return list(cls._handle.devices) if cls._handle else []

    @classmethod
    def has_running_lab(cls) -> bool:
        return cls._handle is not None

    @classmethod
    def release_current(cls) -> None:
        """Release one reference to the current lab if one is running."""
        if cls._current_topo is None:
            raise RuntimeError("No lab running")
        cls.release(cls._current_topo)


# atexit: last-resort cleanup (silent to avoid closed-stream errors)
def _atexit_cleanup() -> None:  # registered below
    LabManager.cleanup(silent=True, reason="atexit")


atexit.register(_atexit_cleanup)
