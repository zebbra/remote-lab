---
title: Use from Python
description: Pytest fixture and Python HTTP client for Remote Lab — the 60-second easy-start, then the four reference pages for the full surface.
tags: [reference, client, testing, api]
crosslink_defines: []
crosslink_references: []
---

# Use from Python

*The pytest fixture and the lower-level HTTP client both ship in `neops-remote-lab`. Sixty seconds end-to-end below; deeper pages follow.*

## 60-second start

```bash
pip install neops-remote-lab
export REMOTE_LAB_URL=http://lab.example.com:8000
```

```python title="tests/conftest.py"
from neops_remote_lab.testing.fixture import remote_lab_fixture

demo = remote_lab_fixture("demo.yml")
```

```python title="tests/test_demo.py"
def test_demo_lab_has_two_devices(demo):
    assert len(demo) == 2
```

```bash
pytest tests/ -v
```

That's the **stable public API** in three lines of test code. The fixture handles session creation, queue waiting, topology upload, and teardown. When the test ends — pass or fail — the lab is released cleanly.

!!! tip "Using this from the Worker SDK?"
    The [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/) imports `remote_lab_fixture` directly to give [function-block](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/) tests a real topology. Two-step setup, then read [Plug into Worker SDK](../getting-started/15-worker-sdk.md) and the SDK's [Remote lab testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/).

## In this section

<div class="grid cards" markdown>

-   :material-test-tube:{ .lg .middle } &nbsp; **[Pytest fixtures](10-pytest-fixtures.md)**

    ---

    The full `remote_lab_fixture` API: factory arguments, the `remote_lab_client` session-scoped fixture, the one-fixture-per-test rule, fixture-rank ordering, end-to-end `reuse_lab=True` examples.

-   :material-puzzle-outline:{ .lg .middle } &nbsp; **[With Worker SDK](15-worker-sdk.md)**

    ---

    Remote-Lab-side notes for Worker SDK consumers — where to declare fixtures in the worker test layout, multi-vendor patterns, links into [docs.neops.io](https://docs.neops.io/neops-worker-sdk-py/).

-   :material-language-python:{ .lg .middle } &nbsp; **[Python client](20-python-client.md)**

    ---

    `RemoteLabClient` for non-pytest contexts — scripts, notebooks, harnesses. Constructor, lifecycle, retry behaviour, swallow-and-log quirks of `release()` and `destroy()`.

-   :material-tune:{ .lg .middle } &nbsp; **[Client config](30-configuration.md)**

    ---

    `REMOTE_LAB_URL` plus three timeout overrides. When to raise each; the timeout-coordination warning that prevents confusing CI failures.

</div>

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — where the client sits relative to the server and `LabManager`.
- **[Lab lifecycle](../10-concepts/30-lab-lifecycle.md)** — reference counting and reuse semantics that `reuse_lab=True` opts into.
- **[REST API](../30-server/40-rest-api.md)** — the authoritative endpoint reference the Python client wraps.
- **[Wire into CI](../getting-started/40-ci.md)** — set the same env vars in GitHub Actions, GitLab CI, or Jenkins.
