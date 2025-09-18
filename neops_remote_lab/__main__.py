"""Run the remote lab server via `poetry run remote_lab` or `python -m neops_remote_lab`"""

from __future__ import annotations

import argparse
import logging
import logging.config
import os
from pathlib import Path
import shutil
import subprocess
import sys
import json
import time
import getpass
import platform
import tempfile

import uvicorn
import yaml
from importlib import resources as _resources
from filelock import FileLock, Timeout

from neops_remote_lab.server import app
from neops_remote_lab import __version__

_logger = logging.getLogger("remote-lab-server")


def setup_logging(config_path: str, log_level: str) -> None:
    """Setup logging configuration from YAML file or fallback to basic config."""
    # Try filesystem path first
    try:
        log_config_path = Path(config_path)
        if log_config_path.exists():
            with open(log_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        else:
            # Fallback to packaged default file inside the module
            with _resources.files("neops_remote_lab").joinpath("logging_config.yaml").open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

        level = log_level.upper()
        if level != "INFO":
            # For non-INFO levels, update all logger levels.
            # For DEBUG, also switch to the debug_console handler.
            for logger_config in config.get("loggers", {}).values():
                logger_config["level"] = level
                if level == "DEBUG":
                    logger_config["handlers"] = ["debug_console"]

            # Set the root logger level, and if DEBUG, also switch to the debug_console handler.
            if "root" in config:
                config["root"]["level"] = level
                if level == "DEBUG":
                    config["root"]["handlers"] = ["debug_console"]

        logging.config.dictConfig(config)
        _logger.info("Loaded logging config (level: %s)", level)

    except (yaml.YAMLError, IOError, KeyError) as e:
        _logger.error("Error processing logging config: %s", e)
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), "INFO"),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


def _instance_paths() -> tuple[Path, Path]:
    tmpdir = Path(tempfile.gettempdir())
    return (tmpdir / "neops_remote_lab_server.lock", tmpdir / "neops_remote_lab_server.meta.json")


def _read_instance_meta(meta_path: Path) -> dict[str, object] | None:
    try:
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _logger.warning("Failed to read instance metadata from %s: %s", meta_path, exc)
        return None


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)  # Unix: signal 0 checks process existence
        return True
    except Exception:
        return False


def _acquire_single_instance_lock() -> tuple[FileLock, Path]:
    """Acquire the global single-instance lock or exit after logging details.

    Returns the acquired FileLock and the metadata path.
    """
    lock_path, meta_path = _instance_paths()
    lock = FileLock(str(lock_path))

    try:
        lock.acquire(timeout=0)
        return lock, meta_path
    except Timeout:
        # Another instance is running – log details if available
        _logger.error("Another Remote Lab Manager instance is already running.")
        data = _read_instance_meta(meta_path)

        if data is not None:
            raw_pid = data.get("pid", 0)
            pid = int(raw_pid) if isinstance(raw_pid, (int, str)) else 0
            if not _pid_is_alive(pid):
                _logger.warning("Stale instance metadata detected – cleaning up...")
                try:
                    meta_path.unlink()
                except Exception:
                    pass
                # Retry acquiring the lock
                try:
                    lock.acquire(timeout=0)
                    _logger.info("Recovered from stale state – proceeding to start server.")
                    return lock, meta_path
                except Timeout:
                    _logger.error("Lock still held but metadata was stale – another process likely took the lock.")
            else:
                _logger.error("Running instance details:")
                _logger.error("  PID:        %s", data.get("pid", "?"))
                _logger.error("  User:       %s@%s", data.get("user", "?"), data.get("host", "?"))
                _logger.error("  Version:    %s", data.get("version", "?"))
                started_raw = data.get("started_at", 0)
                try:
                    started_ts = float(started_raw)  # type: ignore[arg-type]
                except Exception:
                    started_ts = 0.0
                _logger.error("  Started:    %s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_ts)))
                _logger.error("  Bind:       %s:%s", data.get("host_bind", "?"), data.get("port", "?"))
                _logger.error("  Log level:  %s", data.get("log_level", "?"))
                _logger.error("  Log config: %s", data.get("log_config", "?"))
                _logger.error("  CWD:        %s", data.get("cwd", "?"))
                _logger.error("  Command:    %s", data.get("cmd", "?"))
        else:
            _logger.error("No metadata file found for existing instance (%s).", meta_path)

        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Remote Lab Manager")
    default_logger_config_path = Path("logging_config.yaml")  # user may override; packaged default is auto-loaded
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and stream netlab output.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--log-config",
        default=str(default_logger_config_path),
        help="Path to logging config file",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.debug:
        args.log_level = "DEBUG"
        _logger.info("Debug mode enabled. Netlab output will be streamed to console and loglevel set to DEBUG.")
        os.environ["NEOPS_NETLAB_STREAM_OUTPUT"] = "1"

    setup_logging(args.log_config, args.log_level)

    # ------------------------------------------------------------------ single-instance guard
    lock, meta_path = _acquire_single_instance_lock()

    # We own the lock from here on. Ensure release and metadata cleanup on exit
    def _cleanup_lock() -> None:
        try:
            if meta_path.exists():
                meta_path.unlink()
        finally:
            try:
                lock.release()
            except Exception:
                pass

    # Write metadata file for user visibility and diagnostics
    try:
        meta = {
            "pid": os.getpid(),
            "user": getpass.getuser(),
            "host": platform.node(),
            "started_at": time.time(),
            "port": args.port,
            "host_bind": args.host,
            "log_level": args.log_level,
            "log_config": args.log_config,
            "version": __version__,
            "cwd": str(Path.cwd()),
            "cmd": " ".join(sys.argv),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _logger.warning("Failed to write instance metadata: %s", exc)

    _logger.info("Starting Remote Lab Manager on %s:%d", args.host, args.port)

    # Pre-flight: ensure netlab CLI is available
    if shutil.which("netlab") is None:
        _logger.error("'netlab' CLI not found in PATH. The Remote Lab Manager requires Netlab to orchestrate labs.")
        _logger.error("Install Netlab: https://netlab.tools/install/ubuntu/")
        _logger.error("After installation, ensure your shell can find 'netlab' (relogin or reload your shell).")
        raise SystemExit(1)

    # Optional: verify netlab responds
    try:
        completed = subprocess.run(
            ["netlab", "version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _logger.debug("Detected %s", completed.stdout.strip())
    except Exception as exc:  # noqa: BLE001
        _logger.error("Failed to execute 'netlab version': %s", exc)
        _logger.error("Please verify your Netlab installation: https://netlab.tools/install/ubuntu/")
        raise SystemExit(1) from exc

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            access_log=True,
            log_config=None,  # Don't let uvicorn override our logging config
        )
    finally:
        _cleanup_lock()


if __name__ == "__main__":
    main()
