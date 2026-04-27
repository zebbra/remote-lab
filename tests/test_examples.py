"""Validate every file under examples/ — runs in CI to catch drift.

The pages under docs/ pull these files in via mkdocs `--8<--` snippets
(see examples/README.md). If they break here, the published site also
breaks; the convention is "anything more than ~5 lines in the docs lives
in examples/". This test enforces that the examples stay valid.

What we check (no real Netlab required):

- Python files: parsed and imported (catches syntax errors and broken
  imports).
- YAML files: parsed with `yaml.safe_load` (catches yaml syntax errors).
- Bash files: syntax-checked with `bash -n` (catches shell syntax
  errors); shebang is required.
- The systemd unit: required `[Unit]`, `[Service]`, `[Install]` sections
  with `ExecStart=` present.

What we deliberately don't do: actually *run* the examples. Most need
either a running Remote Lab Manager or a Netlab installation, neither of
which CI has. End-to-end execution belongs behind an opt-in marker on a
host that has them.
"""

from __future__ import annotations

import ast
import configparser
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

EXAMPLES = Path(__file__).parent.parent / "examples"


def _all(suffix: str) -> list[Path]:
    return sorted(p for p in EXAMPLES.rglob(f"*{suffix}") if p.is_file())


# ──────────────────────────────────────────────────────────────────────────────
# Python examples
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", _all(".py"), ids=lambda p: str(p.relative_to(EXAMPLES)))
def test_python_example_parses(path: Path) -> None:
    """Every .py example is syntactically valid Python."""
    src = path.read_text()
    ast.parse(src, filename=str(path))


@pytest.mark.parametrize(
    "path",
    [
        p
        for p in _all(".py")
        # conftest.py / test_*.py rely on fixtures defined elsewhere; importing
        # them at module load-time is meaningful only inside a pytest run that
        # has the lab fixture available. Syntax-check above is enough.
        if p.name not in {"conftest.py"} and not p.name.startswith("test_")
    ],
    ids=lambda p: str(p.relative_to(EXAMPLES)),
)
def test_python_example_imports(path: Path) -> None:
    """Importable .py examples load without ImportError or NameError."""
    spec = importlib.util.spec_from_file_location(f"_example_{path.stem}", path)
    assert spec is not None, f"could not create import spec for {path}"
    assert spec.loader is not None, f"import spec for {path} has no loader"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)


# ──────────────────────────────────────────────────────────────────────────────
# YAML examples
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    _all(".yml") + _all(".yaml"),
    ids=lambda p: str(p.relative_to(EXAMPLES)),
)
def test_yaml_example_parses(path: Path) -> None:
    """Every .yml/.yaml example loads as valid YAML."""
    yaml.safe_load(path.read_text())


# ──────────────────────────────────────────────────────────────────────────────
# Bash examples
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    _all(".sh"),
    ids=lambda p: str(p.relative_to(EXAMPLES)),
)
def test_bash_example_syntax(path: Path) -> None:
    """Every .sh example passes `bash -n` syntax check and starts with a shebang."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available on this host")

    first_line = path.read_text().splitlines()[0]
    assert first_line.startswith("#!"), f"{path} is missing a shebang"

    # bash binary resolved via shutil.which; path is a known examples file under
    # tests/../examples — no untrusted input here.
    result = subprocess.run(  # noqa: S603
        [bash, "-n", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


# ──────────────────────────────────────────────────────────────────────────────
# systemd unit
# ──────────────────────────────────────────────────────────────────────────────


def test_systemd_unit_has_required_sections() -> None:
    """The shipped systemd unit declares [Unit], [Service], [Install] and ExecStart."""
    unit_path = EXAMPLES / "systemd" / "neops-remote-lab.service"
    assert unit_path.is_file(), f"missing {unit_path}"

    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.read(unit_path)

    for section in ("Unit", "Service", "Install"):
        assert parser.has_section(section), f"systemd unit missing [{section}]"

    assert parser.has_option("Service", "ExecStart"), "systemd unit [Service] missing ExecStart="
