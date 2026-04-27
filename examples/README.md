# Examples

Runnable code samples that the documentation pulls in via mkdocs `--8<--`
snippets. Editing one of these files updates the corresponding docs page
on the next build.

## Convention

Per the project convention, **any code block longer than ~5 lines that
appears in the documentation lives here** (or as a reference to a real
file in the source tree) — not inline in markdown. Drift is therefore
visible in the diff, and CI exercises every example.

## Layout

| Directory | Contents |
|---|---|
| `quickstart/` | The two-router FRR demo from `docs/getting-started/10-quickstart.md` — a topology, a `conftest.py`, and a test. |
| `pytest_fixtures/` | The end-to-end example from `docs/20-client/10-pytest-fixtures.md` — a `conftest.py` plus a small test module exercising `reuse_lab=True`. |
| `topologies/` | Standalone Netlab YAML topologies referenced from `docs/10-concepts/40-topology-format.md`. |
| `scripts/` | Standalone Python and bash scripts (the `RemoteLabClient` smoke test, the contextmanager wrapper, the force-cleanup runbook). |
| `curl/` | Bash walkthroughs of the REST surface using `curl` (end-to-end session, poll-until-active). |
| `systemd/` | The `neops-remote-lab.service` unit file from `docs/30-server/30-administration.md`. |

## CI

`tests/test_examples.py` exercises every file here:

- Python files are imported (catches syntax errors, missing imports).
- Bash files are syntax-checked with `bash -n`.
- YAML files are loaded with `yaml.safe_load`.
- The `systemd` unit is structure-checked.

Tests that require a real Netlab installation are gated behind a
`REMOTE_LAB_E2E=1` environment variable so CI doesn't try to run them.

## Updating an example

Edit the file, then run `mkdocs build --strict` locally (or `make doc-build`)
to confirm the snippet still resolves cleanly in the documentation. Commit
both the example change and any documentation changes together so the diff
shows the relationship.
