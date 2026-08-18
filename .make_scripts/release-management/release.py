# /// script
# requires-python = ">=3.12"
# dependencies = ["semver>=3"]
# ///
"""
release.py -- SemVer git tag generation with a graph-integrity guard.

Replaces the tag_*.sh scripts; invoked by the `make tag-*` targets via `uv run`.

Subcommands:
    patch | minor | major            -> stable release, guarded
    patch-beta | minor-beta | major-beta | latest-beta -> prerelease, not guarded

Version numbering is unchanged from the shell scripts: the next stable version is
the repo-wide highest stable tag bumped at the requested level. The new behaviour
is the guard: before a STABLE tag is created it is checked against HEAD's commit
graph and REFUSED if it would violate SemVer ordering (an ancestor with a
greater-or-equal version, or a descendant with a lower-or-equal version). Beta tags
are not graph-ordered and are never guarded.

The guarantee holds relative to local tag state. The guard does a best-effort
`git fetch --tags` first (skip with RELEASE_MGMT_NO_FETCH=1); run `git fetch --all`
beforehand for a fully up-to-date graph.
"""
import argparse
import os
import subprocess
import sys

import semver

SEEDS = {"patch": "0.0.1", "minor": "0.1.0", "major": "1.0.0"}


def git(*args: str, check: bool = True) -> str:
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git", *args], text=True, capture_output=True, check=check
    )
    return result.stdout.strip()


def all_tags() -> list[str]:
    return [t.strip() for t in git("tag").splitlines() if t.strip()]


def parse_tag(tag: str) -> semver.Version | None:
    """Parse a git tag (optional v/V prefix) as SemVer, or None if invalid."""
    name = tag[1:] if tag[:1] in ("v", "V") and tag[1:2].isdigit() else tag
    try:
        return semver.Version.parse(name)
    except ValueError:
        return None


def stable_versions(tags: list[str]) -> list[semver.Version]:
    """Valid stable versions (no prerelease, no build metadata) among `tags`."""
    out = []
    for t in tags:
        v = parse_tag(t)
        if v is not None and not v.prerelease and not v.build:
            out.append(v)
    return out


def highest_stable() -> semver.Version | None:
    versions = stable_versions(all_tags())
    return max(versions) if versions else None


def next_stable(level: str) -> semver.Version:
    base = highest_stable()
    if base is None:
        return semver.Version.parse(SEEDS[level])
    return {
        "patch": base.bump_patch,
        "minor": base.bump_minor,
        "major": base.bump_major,
    }[level]()


# ---------------------------------------------------------------------------
# Integrity guard (stable tags only)
# ---------------------------------------------------------------------------

def _refuse(new: semver.Version, reason: str, max_anc, min_desc) -> None:
    lo = f"v{max_anc}" if max_anc is not None else "(none)"
    hi = f"v{min_desc}" if min_desc is not None else "(none)"
    print(f"🚫 Refusing to create v{new}: it would violate SemVer graph integrity.")
    print(f"   Reason: {reason}.")
    print(f"   HEAD's highest stable ancestor: {lo}; lowest stable descendant: {hi}.")
    print(f"   Allowed: strictly greater than {lo} and strictly less than {hi}.")
    print("   Check out the intended commit/branch, run `git fetch --all`, and retry.")
    sys.exit(1)


def assert_integrity(new: semver.Version) -> None:
    """Refuse `new` if it would break ancestor<current<descendant ordering."""
    if os.environ.get("RELEASE_MGMT_NO_FETCH") != "1":
        git("fetch", "--tags", "--force", check=False)  # best-effort

    ancestors = stable_versions(git("tag", "--merged", "HEAD").split())
    descendants = stable_versions(git("tag", "--contains", "HEAD").split())

    too_high = [v for v in ancestors if v >= new]
    if too_high:
        hi = max(too_high)
        _refuse(new, f"ancestor v{hi} has a version >= v{new}", hi, min(descendants, default=None))

    too_low = [v for v in descendants if v <= new]
    if too_low:
        lo = min(too_low)
        _refuse(new, f"descendant v{lo} has a version <= v{new}", max(ancestors, default=None), lo)


# ---------------------------------------------------------------------------
# Tag creation
# ---------------------------------------------------------------------------

def _create(tag: str, message: str, label: str) -> None:
    git("tag", tag, "-m", message)
    print(f"✅ Created new tag({label}): {tag}")


def cmd_stable(level: str) -> None:
    if level == "patch":
        branch = git("branch", "--show-current")
        allowed = branch == "main" or branch.startswith(("hotfix/", "patch/"))
        if not allowed:
            print(
                "🚫 A patch may only be created on hotfix/*, patch/* or main to "
                f"prevent accidental breaking changes. Current branch: {branch}"
            )
            sys.exit(1)
    new = next_stable(level)
    assert_integrity(new)
    _create(f"v{new}", f"{level} release", level)


def _existing_betas_for(base: semver.Version) -> list[semver.Version]:
    result = []
    for t in all_tags():
        v = parse_tag(t)
        if (
            v is not None
            and (v.major, v.minor, v.patch) == (base.major, base.minor, base.patch)
            and v.prerelease
            and v.prerelease.startswith("beta.")
        ):
            result.append(v)
    return sorted(result)


def _bump_beta(v: semver.Version) -> semver.Version:
    n = int(v.prerelease.split(".")[-1])
    return v.replace(prerelease=f"beta.{n + 1}")


def cmd_beta(level: str) -> None:
    base = next_stable(level)
    betas = _existing_betas_for(base)
    new = _bump_beta(betas[-1]) if betas else base.replace(prerelease="beta.1")
    _create(f"v{new}", f"{level}-beta release", f"{level}-beta")


def cmd_latest_beta() -> None:
    betas = sorted(
        v for t in all_tags()
        if (v := parse_tag(t)) is not None and v.prerelease and "beta" in v.prerelease
    )
    if betas:
        new = _bump_beta(betas[-1])
    else:
        parsed = sorted(v for t in all_tags() if (v := parse_tag(t)) is not None)
        top = parsed[-1] if parsed else semver.Version.parse("0.1.0")
        new = semver.Version(top.major, top.minor, top.patch, prerelease="beta.1")
    _create(f"v{new}", "beta release", "beta")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="release.py")
    parser.add_argument(
        "command",
        choices=[
            "patch", "minor", "major",
            "patch-beta", "minor-beta", "major-beta", "latest-beta",
        ],
    )
    cmd = parser.parse_args(argv).command
    if cmd in ("patch", "minor", "major"):
        cmd_stable(cmd)
    elif cmd == "latest-beta":
        cmd_latest_beta()
    else:
        cmd_beta(cmd.split("-")[0])


if __name__ == "__main__":
    main()
