"""Unit tests for `LabManager` helper functions that don't require Netlab."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from neops_remote_lab.netlab.lab_manager import prepare_workdir


@pytest.mark.parametrize("suffix", [".yml", ".yaml", ".YML", ".YAML"])
def test_prepare_workdir_accepts_yaml_and_yml(suffix: str, tmp_path: Path) -> None:
    """Both `.yml` and `.yaml` (case-insensitive) are valid topology suffixes.

    Historically only `.yml` was accepted; this test guards against regression.
    """
    src = tmp_path / f"topology{suffix}"
    src.write_text("provider: clab\nnodes: [r1]\n")

    workdir = prepare_workdir(src)
    try:
        assert (workdir / src.name).is_file()
    finally:
        # Cleanup the temp dir prepare_workdir created.
        shutil.rmtree(workdir, ignore_errors=True)


def test_prepare_workdir_rejects_other_extensions(tmp_path: Path) -> None:
    """Anything that is not `.yml` or `.yaml` raises ValueError."""
    src = tmp_path / "topology.json"
    src.write_text("{}")

    with pytest.raises(ValueError, match="Topology must be a"):
        prepare_workdir(src)
