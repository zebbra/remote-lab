from __future__ import annotations

import atexit
import logging
import os
from itertools import count
from pathlib import Path
from typing import Callable, Iterator, List

import pytest

from neops_remote_lab.client import RemoteLabClient
from neops_remote_lab.models import DeviceInfoDto

REMOTE_LAB_ORDER: dict[str, int] = {}  # fixture_name → rank
_counter = count()  # monotonically increasing

REMOTE_LAB_FIXTURE_META: dict[str, dict[str, object]] = {}

__all__ = [
    "remote_lab_fixture",
    "REMOTE_LAB_ORDER",
    "REMOTE_LAB_FIXTURE_META",
]

_log = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def remote_lab_client() -> Iterator[RemoteLabClient]:
    """Session-scoped RemoteLabClient; fails fast if REMOTE_LAB_URL is missing."""
    url = os.getenv("REMOTE_LAB_URL")
    if not url:
        raise RuntimeError("REMOTE_LAB_URL not set. Set it to the Remote Lab Manager base URL to run Remote Lab tests.")

    client_kwargs: dict[str, int] = {}
    if timeout_str := os.getenv("REMOTE_LAB_REQUEST_TIMEOUT"):
        client_kwargs["request_timeout"] = int(timeout_str)
    if timeout_str := os.getenv("REMOTE_LAB_SESSION_TIMEOUT"):
        client_kwargs["session_timeout"] = int(timeout_str)
    if timeout_str := os.getenv("REMOTE_LAB_ACQUISITION_TIMEOUT"):
        client_kwargs["lab_acquisition_timeout"] = int(timeout_str)

    if client_kwargs:
        _log.debug("Overriding default timeouts with: %s", client_kwargs)

    _log.info("Connecting to remote lab at: %s", url)
    client = RemoteLabClient(base_url=url, **client_kwargs)
    atexit.register(client.close)
    try:
        yield client
    finally:
        client.close()


def remote_lab_fixture(
    topology: str | Path, *, name: str | None = None, reuse_lab: bool = False
) -> Callable[[], Iterator[List[DeviceInfoDto]]]:
    """Create a remote lab pytest fixture that yields NetlabDevice objects.

    Args:
        topology: Path to netlab topology .yml file
        name: Custom fixture name (defaults to topology file stem)
        reuse_lab: Share lab instance across multiple tests
        remote_url: Remote server URL (overrides REMOTE_LAB_URL env var)

    Returns:
        Pytest fixture function
    """
    topo_path = Path(topology).expanduser().resolve()
    if not topo_path.exists():
        raise FileNotFoundError(f"Topology not found: {topo_path}")

    # Determine mode: local vs remote
    remote_url = os.getenv("REMOTE_LAB_URL")
    use_remote = bool(remote_url)

    if use_remote:
        _log.debug("Fixture mode: remote (URL: %s)", remote_url)
    else:
        _log.debug("Fixture mode: local (no remote URL found)")

    # Register fixture metadata for ordering
    fixture_name = name or topo_path.stem
    rank = next(_counter)
    REMOTE_LAB_ORDER[fixture_name] = rank

    try:
        relative_path = topo_path.relative_to(Path.cwd())
    except ValueError:
        relative_path = topo_path

    REMOTE_LAB_FIXTURE_META[fixture_name] = {
        "rank": rank,
        "reuse": reuse_lab,
        "topology": str(relative_path),
        "remote": use_remote,
    }

    _log.debug(
        "Created fixture '%s' (rank=%d, reuse=%s, remote=%s) for topology: %s",
        fixture_name,
        rank,
        reuse_lab,
        use_remote,
        relative_path,
    )

    def fixture_impl(remote_lab_client: RemoteLabClient) -> Iterator[List[DeviceInfoDto]]:
        _log.debug("Acquiring remote lab for %s (reuse=%s)", topo_path.name, reuse_lab)
        device_infos = remote_lab_client.acquire(topo_path, reuse=reuse_lab)

        _log.debug(
            "Remote Lab Fixture %s acquired with %d devices: %s",
            fixture_name,
            len(device_infos),
            [d.name for d in device_infos],
        )

        try:
            yield device_infos
        finally:
            _log.info("Releasing remote lab for %s", topo_path.name)
            remote_lab_client.release()

    fixture_impl.__name__ = fixture_name
    return pytest.fixture(scope="function")(fixture_impl)
