---
title: Client
description: The two public consumer surfaces — the pytest fixture factory (stable API) and the Python HTTP client (lower-level, for scripts and notebooks).
tags: [reference, client, testing, api]
crosslink_defines: []
crosslink_references: []
---

# Client

The Remote Lab Manager is reached from test code and scripts via two
Python surfaces, both installed by `pip install neops-remote-lab`.

`remote_lab_fixture` is the **stable public API**. It is imported
directly by `neops-worker-sdk-py`; its signature is part of a contract
that survives minor and patch releases. If you are writing tests, this
is the surface you want.

`RemoteLabClient` is the **lower-level HTTP client** that the fixture
wraps. Use it when you need to drive a lab from a script, a notebook,
or any non-pytest context.

## In this section

| Guide | What you'll learn |
|---|---|
| [Pytest Fixtures](10-pytest-fixtures.md) | `remote_lab_fixture` factory arguments, the `remote_lab_client` session-scoped fixture, the one-fixture-per-test rule, and end-to-end reuse patterns. |
| [Python Client](20-python-client.md) | `RemoteLabClient` constructor, session lifecycle, `acquire` / `release` / `destroy` / `close`, retry behaviour, and the swallow-and-log quirks. |

## What to read next

- **[Architecture](../concepts/10-architecture.md)** — where the client
  sits relative to the server and `LabManager`.
- **[Lab Lifecycle](../concepts/30-lab-lifecycle.md)** — reference
  counting and reuse semantics that `reuse_lab=True` opts into.
- **[REST API](../server/10-rest-api.md)** — the authoritative endpoint
  reference the Python client wraps.
- **[Configuration](../server/20-configuration.md)** — the environment
  variables the client reads (`REMOTE_LAB_URL` and the three timeouts).
