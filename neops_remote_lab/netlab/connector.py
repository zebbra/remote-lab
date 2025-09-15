from __future__ import annotations

import ast
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List
import os

import yaml

__all__ = [
    "run_netlab",
    "inspect_node",
    "list_nodes",
]

_log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# low-level helpers


def _run_streaming(cmd: List[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run subprocess while streaming output line-by-line to the logger."""
    output_lines: list[str] = []
    with subprocess.Popen(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        bufsize=1,  # Line buffered
    ) as proc:
        _log.debug("Subprocess PID: %d", proc.pid)

        try:
            if proc.stdout:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:  # Skip empty lines
                        _log.debug("[netlab] %s", line)
                        output_lines.append(line)

            proc.wait()
            _log.debug("Streamed process ended with return code: %d", proc.returncode)

            # Create a CompletedProcess-like object for compatibility
            full_output = "\n".join(output_lines)
            return subprocess.CompletedProcess(args=cmd, returncode=proc.returncode, stdout=full_output, stderr="")

        except Exception as e:  # noqa: BLE001 broad-except acceptable for subprocess cleanup
            _log.error("Exception while streaming subprocess output: %s", e)
            _log.debug("Killing subprocess PID %d", proc.pid)
            proc.kill()
            proc.wait()
            raise RuntimeError(f"netlab {' '.join(cmd[1:])} interrupted: {e}") from e


def _run_captured(cmd: List[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run subprocess and capture output at the end."""
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=None,  # No timeout for now, but we could add one
        )
        _log.debug("Subprocess completed with return code: %d", completed.returncode)
        if completed.stdout:
            _log.debug("Subprocess stdout:\n%s", completed.stdout.strip())
        return completed
    except subprocess.TimeoutExpired as e:
        _log.error("Subprocess for `netlab %s` timed out: %s", " ".join(cmd[1:]), e)
        raise
    except Exception as e:  # noqa: BLE001
        _log.error("Subprocess for `netlab %s` failed: %s", " ".join(cmd[1:]), e)
        raise


def run_netlab(
    args: List[str], *, cwd: Path, stream_output: bool = False, expected_failure: bool = False
) -> subprocess.CompletedProcess[str]:  # pylint: disable=too-many-branches, too-many-statements
    """Run a netlab command with enhanced logging and error handling.

    Args:
        args: Arguments to pass to netlab command
        cwd: Working directory to run command in
        stream_output: If True, stream stdout/stderr to console in real-time (for long operations)
        expected_failure: If True, log failures at debug level instead of error level (useful for cleanup operations that may fail when no lab is running)
    """
    cmd = ["netlab", *args]

    # Check for environment variable override to stream netlab output
    if os.environ.get("NEOPS_NETLAB_STREAM_OUTPUT") == "1":
        stream_output = True

    _log.debug("Running: %s (cwd=%s)", " ".join(cmd), cwd)
    start_time = time.time()

    completed = _run_streaming(cmd, cwd=cwd) if stream_output else _run_captured(cmd, cwd=cwd)

    duration = time.time() - start_time

    if completed.returncode:
        # Log stderr if available and not streamed (to avoid duplication)
        if not stream_output and completed.stderr:
            if expected_failure:
                _log.debug("`netlab %s` stderr (%.1fs):\n%s", " ".join(args), duration, completed.stderr.strip())
            else:
                _log.error("`netlab %s` stderr (%.1fs):\n%s", " ".join(args), duration, completed.stderr.strip())

        # Log the failure at appropriate level
        if expected_failure:
            _log.debug(
                "`netlab %s` failed with exit code %d (%.1fs) - expected failure",
                " ".join(args),
                completed.returncode,
                duration,
            )
            return completed
        _log.error("`netlab %s` failed with exit code %d (%.1fs)", " ".join(args), completed.returncode, duration)
        raise RuntimeError(f"netlab {' '.join(args)} failed with exit code {completed.returncode}")

    _log.info("`netlab %s` finished successfully (%.1fs)", " ".join(args), duration)

    return completed


def inspect_node(node: str, *, cwd: Path) -> Dict[str, Any]:
    out = run_netlab(
        [
            "inspect",
            "-q",  # quiet mode, this is important to avoid extra output, which breaks parsing
            "--instance",
            "default",
            "--node",
            node,
            "--format",
            "yaml",
        ],
        cwd=cwd,
    ).stdout
    return yaml.safe_load(out) or {}


def list_nodes(*, cwd: Path) -> List[str]:
    """Return all node names in the current lab (via YAML)."""

    out = run_netlab(
        ["inspect", "-q", "--instance", "default", "--format", "json", "list(nodes.keys())"],
        cwd=cwd,
    ).stdout
    _log.debug("`netlab inspect` output: %s", out.strip())
    # Parse the output from `netlab inspect` command. It sould be sth like: ['r1', 'r2']
    nodes = ast.literal_eval(out)
    if not isinstance(nodes, list):
        raise ValueError("Unexpected JSON structure from `netlab inspect`.")
    return nodes
