"""Smoke test for `RemoteLabClient` — acquire a lab, list devices, release.

Usage:
    export REMOTE_LAB_URL=http://lab.example.com:8000
    python examples/scripts/smoke.py path/to/topology.yml
"""

import os
import pathlib
import sys

from neops_remote_lab.client import RemoteLabClient


def main(topology_path: str) -> None:
    client = RemoteLabClient(
        base_url=os.environ["REMOTE_LAB_URL"],
        session_timeout=120,  # fail fast if queue is deep
    )
    try:
        devices = client.acquire(
            topology=pathlib.Path(topology_path),
            reuse=False,
        )
        print(f"Acquired lab with {len(devices)} devices:")
        for d in devices:
            print(f"  {d.name}")
        client.release()
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: smoke.py <topology.yml>")
    main(sys.argv[1])
