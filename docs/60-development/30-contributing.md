---
page_purpose: how-to
personas_served: [devops-engineer]
difficulty_level: intermediate
---

# Contributing

This guide covers setting up a development environment, the code quality toolchain, and the workflow for getting changes merged.

## Dev environment setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (the project's package manager and task runner)
- Git with access to the repository

### Install dependencies

```bash
git clone <repo-url> && cd neops-remote-lab
uv sync --group dev
```

The `--group dev` flag installs development dependencies (ruff, pyrefly, pytest, httpx, pip-audit, type stubs) alongside the main package.

### Verify the setup

```bash
make check
```

This runs the full quality pipeline: lint, type check, security audit, and tests. If everything passes, your environment is ready.

## Makefile targets

The `Makefile` provides the standard development commands:

| Target | What it runs | When to use |
|--------|-------------|-------------|
| `make lint` | `ruff format --check` + `ruff check` | Quick style and lint check (no auto-fix) |
| `make format` | `ruff format` + `ruff check --fix` | Auto-fix formatting and lint issues |
| `make typeCheck` | `pyrefly check` | Static type checking |
| `make test` | `pytest` | Run the test suite |
| `make audit` | `pip-audit --strict` | Check dependencies for known CVEs |
| `make check` | `lint` + `typeCheck` + `audit` + `test` | Full CI pipeline locally. This is what CI runs. |

Always run `make check` before pushing. CI runs the same command and will reject PRs that fail any step.

## Code style

### Ruff

The project uses [Ruff](https://docs.astral.sh/ruff/) for both formatting and linting. Configuration lives in `pyproject.toml`:

- **Line length**: 120 characters
- **Target version**: Python 3.12
- **Quote style**: Double quotes
- **Indent**: 4 spaces

Ruff enforces a broad rule set including Pyflakes, pycodestyle, isort, flake8-bugbear, pyupgrade, bandit (security), and more. See the `[tool.ruff.lint] select` list in `pyproject.toml` for the full set.

Notable per-file overrides:

- **`tests/**`**: Docstrings not required, asserts allowed, magic values allowed.
- **`server.py`**: FastAPI's `Depends()`/`File()` call defaults are excluded from the "mutable default" rule.

### Docstrings

Use Google-style docstrings (`[tool.ruff.lint.pydocstyle] convention = "google"`):

```python
def acquire(cls, topo: Path, *, reuse: bool = True) -> list[DeviceInfoDto]:
    """Return a list of DeviceInfoDto objects for the given topology.

    Args:
        topo: Path to the topology YAML file.
        reuse: If True, reuse an already running lab with the same topology content.
    """
```

### Naming conventions

- Pydantic models: `*Dto` suffix (e.g., `SessionInfoDto`, `LabStatusDto`)
- Private module-level state: underscore prefix (e.g., `_SESSIONS`, `_SESSION_QUEUE`)
- Loggers: `logging.getLogger(__name__)` for library modules, `logging.getLogger("remote-lab-server")` for the server module

## Type checking

The project uses [Pyrefly](https://github.com/pyrefly/pyrefly) for static type checking, configured in `pyproject.toml`:

- **Target**: Python 3.12
- **Scope**: `neops_remote_lab/**/*.py` (excludes tests, docs, vendor scripts)
- **Strictness**: `untyped-def-behavior = "check-and-infer-return-type"` -- unannotated functions are type-checked with inferred return types. Unannotated parameters and returns trigger errors.

Run type checking:

```bash
make typeCheck
```

## CI pipeline

CI is defined in `.github/workflows/ci.yml` and runs on every push to `main`/`develop` and on pull requests. It executes two jobs:

### `lint-test`

Runs on `ubuntu-latest`:

1. `uv sync --group dev --frozen` -- install dependencies from lockfile
2. `ruff format --check` -- verify formatting
3. `ruff check` -- run lint rules
4. `pyrefly check` -- type checking
5. `pip-audit --strict` -- CVE scan
6. `pytest` -- run test suite

All steps must pass. This is equivalent to `make check`.

!!! warning "CI does not install Netlab"
    The CI runner does not have `netlab` or Containerlab installed. Server tests that exercise lab operations use a stubbed `LabManager` (see [Internal Architecture > Test stubbing pattern](10-architecture.md#test-stubbing-pattern)). Any test requiring real Netlab must be gated accordingly.

### `wheel`

Runs after `lint-test` passes. Builds a Python wheel and uploads it as a CI artifact. This validates that the package builds cleanly but does not publish to any registry.

## CVE-pinned dependencies

Several dependencies in `pyproject.toml` carry `# CVE-*` comments explaining why a minimum version is pinned:

```toml
"starlette>=0.49.1",   # CVE-2025-62727 fix
"filelock>=3.20.1,<4", # CVE-2025-68146 fix
"pytest>=9.0.3,<10",   # CVE-2025-71176 fix
```

When upgrading dependencies, preserve these comments and re-run `make audit` to verify no new vulnerabilities are introduced.

## Branching and workflow

- **Branch from `develop`**, not `main`. The `main` branch receives merges from `develop` at release time.
- **Keep PRs focused.** One logical change per PR.
- **Run `make check` locally** before pushing. CI runs the same checks, but catching issues locally is faster.
- **Write tests** for new functionality. The test suite lives in `tests/` and uses `pytest` with `pytest-asyncio` for async tests. Use `httpx.AsyncClient` to test FastAPI endpoints.

## Testing approach

### What CI can test

- FastAPI endpoint behavior (session management, request validation, error responses)
- Session queue logic (promotion, cleanup, stale detection)
- Model serialization and validation
- Client-side logic (retry, timeout, session lifecycle)

These tests use a stubbed `LabManager` that returns fake devices without invoking `netlab`.

### What requires a real Netlab host

- Actual topology startup and teardown
- Device inspection and connectivity
- End-to-end remote lab workflows

These tests must run on a host with Netlab and Containerlab installed (e.g., the Remote Lab VM). Gate them with appropriate markers or skip conditions so they do not run in CI.

### Test configuration

pytest is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
addopts = ["--ignore=docs"]
```

- `asyncio_mode = "strict"` -- async tests must explicitly use `@pytest.mark.asyncio`.
- `--ignore=docs` -- the `docs/` directory contains symlinks to source code (for mkdocs) that pytest would otherwise try to collect.
