"""A context-manager wrapper around RemoteLabClient.

`RemoteLabClient` does not implement `__enter__` / `__exit__`; this wrapper
ensures `close()` runs on the way out, even when the lab body raises.
"""

import contextlib
from collections.abc import Iterator

from neops_remote_lab.client import RemoteLabClient


@contextlib.contextmanager
def remote_lab_client(**kwargs) -> Iterator[RemoteLabClient]:
    client = RemoteLabClient(**kwargs)
    try:
        yield client
    finally:
        client.close()
