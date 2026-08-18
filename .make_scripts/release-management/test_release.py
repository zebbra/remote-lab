#!/usr/bin/env python3
"""
Tests for release.py -- SemVer tag generation with graph-integrity guard.

Uses real temporary git repositories. The guard's remote fetch is disabled via
RELEASE_MGMT_NO_FETCH so tests run offline and deterministically.
"""
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import release  # noqa: E402

os.environ["RELEASE_MGMT_NO_FETCH"] = "1"


@dataclass
class GitRepo:
    path: Path

    def run(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.path, text=True, capture_output=True, check=True
        ).stdout.strip()

    def commit(self, message: str = "c") -> str:
        self.run("commit", "--allow-empty", "-m", message)
        return self.run("rev-parse", "HEAD")

    def tag(self, name: str, ref: str | None = None) -> None:
        self.run("tag", name, *( [ref] if ref else [] ))

    def tags(self) -> set[str]:
        out = self.run("tag")
        return {t for t in out.splitlines() if t}

    def branch(self, name: str) -> None:
        self.run("checkout", "-b", name)

    def checkout(self, ref: str) -> None:
        self.run("checkout", ref)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> GitRepo:
    r = GitRepo(tmp_path)
    r.run("init", "-b", "main")
    r.run("config", "user.email", "t@t.com")
    r.run("config", "user.name", "T")
    r.commit("initial")
    monkeypatch.chdir(tmp_path)  # release.py operates on the current working dir
    return r


# --- version computation -----------------------------------------------------

class TestNextStable:
    def test_bumps(self, repo: GitRepo):
        repo.tag("v1.2.3")
        assert str(release.next_stable("patch")) == "1.2.4"
        assert str(release.next_stable("minor")) == "1.3.0"
        assert str(release.next_stable("major")) == "2.0.0"

    def test_seeds_on_empty(self, repo: GitRepo):
        assert str(release.next_stable("patch")) == "0.0.1"
        assert str(release.next_stable("minor")) == "0.1.0"
        assert str(release.next_stable("major")) == "1.0.0"

    def test_ignores_betas_and_build(self, repo: GitRepo):
        repo.tag("v1.2.3")
        repo.tag("v1.3.0-beta.1")
        repo.tag("v9.9.9+build.1")
        assert str(release.next_stable("minor")) == "1.3.0"


# --- stable happy path -------------------------------------------------------

class TestStableHappyPath:
    def test_patch_minor_major(self, repo: GitRepo):
        repo.tag("v1.2.3")
        repo.commit("work")
        release.main(["minor"])
        assert "v1.3.0" in repo.tags()

    def test_first_ever_tag(self, repo: GitRepo):
        release.main(["major"])
        assert "v1.0.0" in repo.tags()


# --- integrity guard ---------------------------------------------------------

class TestGuard:
    def test_refuses_on_old_commit(self, repo: GitRepo):
        """HEAD is an ancestor of a higher stable tag -> refuse."""
        first = repo.run("rev-parse", "HEAD")
        repo.tag("v1.0.0", first)
        repo.commit("second")
        repo.tag("v1.1.0")
        repo.checkout(first)  # detach onto the old commit
        with pytest.raises(SystemExit) as exc:
            release.main(["minor"])  # would be v1.2.0 on an ancestor of v1.1.0
        assert exc.value.code == 1
        assert "v1.2.0" not in repo.tags()  # nothing created

    def test_allows_divergent_branch(self, repo: GitRepo):
        """A side branch whose tag is neither ancestor nor descendant is fine."""
        repo.tag("v1.0.0")
        repo.branch("feature")
        repo.commit("feature work")
        # highest stable repo-wide is still 1.0.0 -> minor => 1.1.0 on feature tip,
        # which is not related to any higher tag -> allowed.
        release.main(["minor"])
        assert "v1.1.0" in repo.tags()

    def test_refuses_equal_to_descendant(self, repo: GitRepo):
        first = repo.run("rev-parse", "HEAD")
        repo.tag("v1.0.0", first)
        repo.commit("second")
        repo.tag("v1.1.0")
        repo.checkout(first)
        with pytest.raises(SystemExit):
            release.main(["patch"])  # v1.1.1 vs descendant v1.1.0 <= it


# --- branch restriction ------------------------------------------------------

class TestPatchBranchRestriction:
    def test_patch_refused_off_allowed_branches(self, repo: GitRepo):
        repo.tag("v1.0.0")
        repo.branch("feature")
        repo.commit("work")
        with pytest.raises(SystemExit) as exc:
            release.main(["patch"])
        assert exc.value.code == 1
        assert "v1.0.1" not in repo.tags()

    def test_patch_allowed_on_hotfix(self, repo: GitRepo):
        repo.tag("v1.0.0")
        repo.branch("hotfix/x")
        repo.commit("fix")
        release.main(["patch"])
        assert "v1.0.1" in repo.tags()


# --- beta (unguarded) --------------------------------------------------------

class TestBeta:
    def test_seed_then_increment(self, repo: GitRepo):
        repo.tag("v1.2.3")
        repo.commit("work")
        release.main(["patch-beta"])
        assert "v1.2.4-beta.1" in repo.tags()
        repo.commit("more")
        release.main(["patch-beta"])
        assert "v1.2.4-beta.2" in repo.tags()

    def test_beta_not_guarded_on_old_commit(self, repo: GitRepo):
        """Beta tags are exempt from the integrity guard."""
        first = repo.run("rev-parse", "HEAD")
        repo.tag("v1.0.0", first)
        repo.commit("second")
        repo.tag("v1.1.0")
        repo.checkout(first)
        release.main(["minor-beta"])  # must NOT raise (betas are unguarded)
        # base is repo-wide (1.1.0 -> 1.2.0), unaffected by HEAD position
        assert "v1.2.0-beta.1" in repo.tags()
