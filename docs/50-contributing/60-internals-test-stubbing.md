---
title: "Internals: CI test stubbing"
description: How LabManager is shaped to make CI tests possible without a Netlab install — the StubLabManager pattern and the pytest plugin entry point.
tags: [contributing, internals, testing]
crosslink_defines: []
crosslink_references: []
---

# Internals: CI test stubbing {#ci-test-stubbing}

CI runs on `ubuntu-latest` without `netlab` or Containerlab installed. The test suite stays useful because `LabManager` is a class with class-level state and only class methods — easy to subclass and override.

## The StubLabManager pattern

Create a `StubLabManager` that overrides the methods that would call `netlab` (`_start`, `_terminate_current`, `_terminate_default_netlab_instance`) to return synthetic device data and no-op the cleanup paths. Then monkeypatch `server` to use the stub:

```python
class StubLabManager(LabManager):
    """LabManager that doesn't touch netlab."""

    @classmethod
    def _start(cls, topo: Path) -> list[DeviceInfoDto]:
        cls._current_topo = topo
        cls._current_topo_hash = _compute_file_sha256(topo)
        cls._handle = LabManager._Handle(
            workdir=Path(tempfile.mkdtemp()),
            devices=[DeviceInfoDto(name="stub-r1", raw={"kind": "stub"})],
        )
        return cls._handle.devices
```

The stub inherits the state-management logic — refcount, hash comparison, filelock — and only replaces the Netlab-dependent parts. That means tests exercise the **same** queue and lifecycle code that production runs, just without booting containers.

This is exactly why [the singleton design](40-internals-lab-manager.md#the-singleton-pattern) is the way it is: subclassing class-level state is trivial; subclassing instance state would have meant a more elaborate factory dance.

## Tests that need real Netlab

Tests that need a real Netlab installation (end-to-end, container connectivity, real `netlab inspect` output) must be gated with a marker or skip condition so they don't fire in CI. The convention is to assume CI unless the test is explicitly opt-in.

Don't write a test that "just so happens to work" with the stub but relies on production-only behaviour — the stub diverges from real Netlab at the boundary, and a test that hides that divergence will pass in CI and fail mysteriously in local dev (or vice versa).

## The pytest plugin entry point

`pyproject.toml` declares:

```toml
[project.entry-points.pytest11]
neops-remote-lab = "neops_remote_lab.pytest_plugins"
```

`neops_remote_lab.pytest_plugins` is a stub module that lists the real plugins:

```python
pytest_plugins: list[str] = [
    "neops_remote_lab.testing.fixture",
    "neops_remote_lab.testing.pytest_order_plugin",
]
```

pytest's `pytest_plugins` mechanism then loads both modules. The indirection means a single entry-point name (`neops-remote-lab`) registers the fixture factory **and** the collection-time ordering plugin without forcing consumers to know about either module path.

If you add a new pytest-side module, append its dotted path to `pytest_plugins` rather than declaring a new entry point — the entry point is the public surface, and changing its name is a breaking change for anyone who has it in a `pytest --no-cov -p no:neops-remote-lab` invocation.

## See also

- **[Invariants → One `remote_lab_fixture` per test](20-invariants.md#one-remote_lab_fixture-per-test-collection-time)** — the collection-time guard the ordering plugin enforces.
- **[Internals: LabManager singleton & locking](40-internals-lab-manager.md)** — why the singleton shape is the thing that makes stubbing easy.
- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — the consumer-facing surface the entry point publishes.
