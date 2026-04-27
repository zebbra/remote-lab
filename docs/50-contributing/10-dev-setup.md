---
title: Dev setup
description: Set up a development environment for neops-remote-lab — clone, install, the make check pipeline, code style, the CVE-pinned dependency convention, and the branch-to-PR flow.
tags: [contributing, how-to, tooling]
crosslink_defines: []
crosslink_references: []
---

# Dev setup

Get from a fresh clone to a green `make check` in five minutes. Then this page
is what you come back to when CI flags something you didn't expect.

## Prerequisites

- **Python 3.12+** — the project pins `requires-python = ">=3.12"`.
- **[uv](https://docs.astral.sh/uv/)** — the package manager and task runner
  used here. `pip`/`pip-tools` workflows will diverge from CI; use `uv`.
- **git** with push access if you intend to open PRs.

You do **not** need Netlab or Containerlab installed to develop the server
itself — CI doesn't have them either, and the test suite stubs `LabManager`
to keep tests host-agnostic. See
[Invariants → CI test stubbing](20-invariants.md#ci-test-stubbing).

## Clone and install

```bash
git clone git@github.com:zebbra/neops-remote-lab.git
cd neops-remote-lab
uv sync --group dev
```

The `--group dev` group brings in `ruff`, `pyrefly`, `pytest`, `pytest-asyncio`,
`httpx`, `pip-audit`, and the type stubs that `make check` needs.

## The `make check` pipeline

`make check` is what CI runs. Run it locally before every push:

```bash
make check
```

It chains four steps:

| Target | Command | Failure mode |
|---|---|---|
| `lint` | `ruff format --check` and `ruff check` | Formatting differences or lint rule violations. Run `make format` to auto-fix the easy ones. |
| `typeCheck` | `pyrefly check` | Missing type annotations on public functions, type mismatches, untyped `Any` leakage. |
| `audit` | `pip-audit --strict` | A dependency has a known CVE. Bump it, preserve the `# CVE-*` pin comment, re-run. |
| `test` | `pytest` | Anything in `tests/`. CI uses the same command. |

If any step fails, fix it locally before pushing — CI will not be more lenient.

!!! tip "What `make format` will and won't do"
    `make format` runs `ruff format` and `ruff check --fix`, which auto-fixes
    formatting and a subset of lint rules (import order, unused imports,
    obvious style). It will **not** add missing type annotations or fix
    rule classes that need human judgment (security, complexity).

## Code style at a glance

Defined in `pyproject.toml` under `[tool.ruff]`:

- **Line length 120**, double quotes, 4-space indent, target Python 3.12.
- **Docstrings**: Google style. The Pydocstyle convention is set to `"google"`.
- **Tests** (`tests/**`): docstrings not required, `assert` allowed, magic
  values allowed.
- **`server.py`**: FastAPI `Depends()`/`File()` defaults are exempt from the
  "mutable default arg" rule.

Naming conventions that code review enforces:

- Pydantic request/response models end in **`Dto`** (e.g., `SessionInfoDto`,
  `LabStatusDto`). This is invariant — see
  [Invariants → `*Dto` suffix](20-invariants.md#dto-suffix).
- Module-private state has a leading underscore: `_SESSIONS`,
  `_SESSION_QUEUE`, `_SHUTDOWN_EVENT`.
- Loggers: `logging.getLogger(__name__)` for library modules,
  `logging.getLogger("remote-lab-server")` for the server module.

## Type checking

[Pyrefly](https://github.com/pyrefly/pyrefly) does the static type analysis.
Configured in `pyproject.toml`:

- **Target**: Python 3.12.
- **Scope**: `neops_remote_lab/**/*.py`. Tests, docs, vendor scripts excluded.
- **`untyped-def-behavior = "check-and-infer-return-type"`** — unannotated
  functions are checked with inferred return types; missing parameter or
  return annotations on public surfaces fail the check.

Run it on its own:

```bash
make typeCheck
```

If pyrefly objects to a Pydantic v2 `BaseModel` subclass with a misc-type
warning, the established workaround is the `# type: ignore[misc]` comment on
the class line — see existing models for the pattern.

## CVE-pinned dependencies

Several pins in `pyproject.toml` carry a `# CVE-*` comment explaining why a
minimum version exists:

```toml
"starlette>=0.49.1",   # CVE-2025-62727 fix
"filelock>=3.20.1,<4", # CVE-2025-68146 fix
"pytest>=9.0.3,<10",   # CVE-2025-71176 fix
```

When you upgrade a dependency that has one of these comments:

1. Pick a version that still preserves the fix (a higher version that
   includes the CVE patch is fine; a lower version is not).
2. Keep the comment on the line, possibly updated if the CVE numbering
   changes.
3. Re-run `make audit` to confirm `pip-audit --strict` is still clean.
4. Mention the dep bump in your commit message.

This is one of the project's hard invariants. See
[Invariants → CVE-pinned dependencies](20-invariants.md#cve-pinned-dependencies).

## Branch and PR flow

- **Branch from `develop`**, never from `main`. `main` receives merges from
  `develop` at release time.
- **One logical change per PR.** A bug fix is a PR. A refactor is a PR.
  Bundling them creates review noise.
- **Run `make check` locally before pushing.** Anything CI catches is
  cheaper to fix before the push.
- **Write tests** for new functionality. The test suite lives in `tests/`
  and uses `pytest` plus `pytest-asyncio`. Use `httpx.AsyncClient` to
  exercise FastAPI endpoints; that's the established pattern.

A typical PR looks like this:

```bash
# 1. Branch from develop
git fetch origin
git switch -c feature/my-change origin/develop

# 2. Make changes, test locally
$EDITOR neops_remote_lab/server.py
make format            # auto-fix what's easy
make check             # the same thing CI will run

# 3. Commit, push, open PR against develop
git add -p
git commit -m "feat: short summary, why-not-what in the body"
git push -u origin feature/my-change
gh pr create --base develop
```

Reviewers will look for: invariants preserved, tests added or updated, no
`# type: ignore` introduced without a comment explaining why, CVE pin
comments still in place if you touched dependencies.

## Testing approach

CI cannot test paths that need a real Netlab installation; it runs on
`ubuntu-latest` without `netlab` or Containerlab on `PATH`.

What CI does test:

- FastAPI endpoint behavior — session management, request validation, error
  responses.
- Session queue logic — promotion, cleanup, stale detection.
- Model serialization and validation.
- Client-side logic — retry, timeout, session lifecycle.

These tests rely on `LabManager` being **stubbed** during the test run; see
[Invariants → CI test stubbing](20-invariants.md#ci-test-stubbing) for the
pattern.

What CI cannot test:

- Real `netlab up` and topology startup.
- Device inspection and connectivity through Netlab.
- End-to-end remote-lab workflows with actual containers.

These have to run on a host with Netlab and Containerlab installed (the
neops-labs VM, or a local Ubuntu machine that has been through
[Netlab host setup](../40-deployment/10-netlab-host-setup.md)). Gate them
with markers or skip conditions so they don't fail in CI.

### Pytest configuration

Configured in `pyproject.toml` under `[tool.pytest.ini_options]`:

- `asyncio_mode = "strict"` — async tests must be explicitly marked
  `@pytest.mark.asyncio`. Implicit asyncio mode hides ordering bugs;
  strict catches them.
- `asyncio_default_fixture_loop_scope = "function"` — each test gets its
  own loop. Don't mix scopes without a reason.
- `--ignore=docs` — the `docs/` tree contains symlinks back into source
  (`docs/neops_remote_lab/`, `docs/tests/`) so mkdocs snippets can resolve
  source paths. pytest would otherwise try to collect them.

## Pre-push checklist

Run this sequence before opening a PR:

```bash
make format            # auto-fix style issues
make check             # full CI pipeline (lint + type + audit + test)
git status             # confirm only intended changes staged
git diff origin/develop  # sanity-check the diff against the base branch
```

If `make check` is green and the diff is what you meant to write, push.

## Where to go next

- **[Invariants & internals](20-invariants.md)** — the rules a change cannot
  break, plus the internal mechanics that make the rules work. Read this
  before touching `server.py`, `lab_manager.py`, or anything in
  `netlab/connector.py`.
- **[Architecture](../10-concepts/10-architecture.md)** — the high-level
  component picture. Useful framing before the deep-dive in Invariants.
