# neops-remote-lab

Read AGENTS.md for full project context.

## Branch Workflow

Branch from `develop`. PRs target `develop`.

## Quick Reference

- Server: `neops_remote_lab/server.py` (FastAPI app with 12 endpoints)
- Client: `neops_remote_lab/client.py` (RemoteLabClient with session lifecycle)
- Lab manager: `neops_remote_lab/netlab/lab_manager.py` (one-lab-at-a-time with content-hash reuse)
- Netlab wrapper: `neops_remote_lab/netlab/connector.py` (subprocess calls to netlab CLI)
- pytest plugin: `neops_remote_lab/testing/fixture.py` (remote_lab_fixture factory)
- Run checks: `make check` (lint + typeCheck + audit + test)
- Topology files must use `.yml` extension; identity is SHA-256 of content, not filename
