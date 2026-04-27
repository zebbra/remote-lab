---
title: Your first PR
description: The 30-minute path to a green CI on your first contribution — clone, make check, find a good-first-issue, ship it.
tags: [contributing, tutorial]
crosslink_defines: []
crosslink_references: []
---

# Your first PR

*The 30-minute path: clone, run `make check` green, pick something small, ship it. Six checkboxes; the rest of Contributing is for once you're past these.*

## The path

- [ ] **`git clone` the repo.** `git clone git@github.com:zebbra/neops-remote-lab.git`. Branch from `develop`, not `main` — every PR targets `develop`.
- [ ] **Read [`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md).** One screen. Lists the conventions code review enforces — `*Dto` suffix, `_run_blocking()` for blocking I/O in async handlers, `connector.run_netlab()` as the only Netlab path, CVE-pinned deps. Skim this **before** your first commit.
- [ ] **Run `make check`.** Green on a fresh clone means your dev environment is set up. If it isn't, [Dev setup](10-dev-setup.md) walks the diagnose-and-fix path. *Do not skip this step* — you need it green to know whether your changes broke something.
- [ ] **Read [Invariants](20-invariants.md).** The eight rules a PR cannot violate. Each entry is 5–10 lines. Read all eight; the one that bites you on your first PR is rarely the one you'd guess.
- [ ] **Pick a [good-first-issue](https://github.com/zebbra/neops-remote-lab/labels/good%20first%20issue).** Or a typo, or a doc fix, or anything you've already noticed while reading these docs. The first PR is about the *flow*, not about a heroic feature.
- [ ] **Open a PR.** CI runs `make check` (lint + typecheck + tests). When it's green, ask for review.

## What CI is going to check

`make check` runs four things in sequence. If your local pre-push run is green, CI's run will be too.

```bash
make lint       # ruff format-check + ruff check
make typeCheck  # pyrefly
make test       # pytest -q (39 tests today)
make audit      # pip-audit --strict
```

??? info "If `make audit` fails on a pre-existing CVE"
    `make audit` failing on a transitive CVE you didn't introduce is a known state — track separately, don't block your PR on it. The maintainer pins these explicitly with `# CVE-*` comments in `pyproject.toml`. See [Invariants → CVE-pinned dependencies](20-invariants.md#cve-pinned-dependencies).

## Where to go next based on what you're touching

<div class="grid cards" markdown>

-   :material-tools:{ .lg .middle } &nbsp; **[Dev setup](10-dev-setup.md)**

    ---

    `make check` not green? The dev-setup page walks the install + diagnose + fix path.

-   :material-shield-check:{ .lg .middle } &nbsp; **[Invariants](20-invariants.md)**

    ---

    The eight load-bearing rules. Re-read the relevant one before any non-trivial change.

-   :material-sync:{ .lg .middle } &nbsp; **[Async discipline](30-internals-async.md)**

    ---

    Touching `server.py` and adding a new operation that calls Netlab? Read this first — the `_run_blocking` discipline is non-obvious.

-   :material-cog:{ .lg .middle } &nbsp; **[LabManager](40-internals-lab-manager.md)**

    ---

    Touching `lab_manager.py` or `connector.py`? Read this. `try_acquire` vs `acquire` is the easiest way to wedge the test suite.

-   :material-power-plug-off:{ .lg .middle } &nbsp; **[atexit & lifespan](50-internals-atexit.md)**

    ---

    Touching teardown? Read this — async in `atexit` deadlocks the interpreter.

-   :material-test-tube-empty:{ .lg .middle } &nbsp; **[Test stubbing](60-internals-test-stubbing.md)**

    ---

    Adding a test that needs `LabManager` but CI has no `netlab`? Subclass and override.

</div>

After your first PR is in, [Anti-patterns](70-anti-patterns.md) is the one-page grep target you'll want bookmarked for review.

## See also

- **[`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md)** — the same invariants in repo-root form, alongside agent-bootstrap context. Read this if you're working with an AI assistant.
- **[`README.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/README.md)** — project overview, install, quick orientation.
- **[Architecture](../10-concepts/10-architecture.md)** — the high-level picture. The Internals pages assume you've read this.
