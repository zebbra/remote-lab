---
page_purpose: overview
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: beginner
---

# Concepts

Remote Lab's design follows from a single Netlab constraint: only one topology can run per host at any time. Everything else -- the session queue, reference counting, content hashing -- exists to make that constraint safe and efficient in a multi-user, multi-test environment.

## Which page do you need?

- **Debugging a timeout, queue stall, or "why is my test waiting forever" problem** -> start at [Lab Lifecycle](30-lab-lifecycle.md) for acquire/reuse/teardown mechanics, then [Session Queue](20-session-queue.md) for the promotion rules.
- **Understanding a specific session ID, `status=waiting` vs `active`, or heartbeat behavior** -> go straight to [Session Queue](20-session-queue.md). It covers the FIFO queue, the WAITING -> ACTIVE transitions, the three promotion call sites, and the stale-session cleanup path.
- **Writing or editing a topology YAML** -> [Topology Format](40-topology-format.md) is the contract. It enumerates supported providers, modules, device kinds, the `extra_files` upload mechanism, and the Netlab features explicitly not available through Remote Lab.
- **New to the project, looking for the component map** -> [Architecture](10-architecture.md) has the two-component picture (remote server + client/fixtures) and the request flow from pytest through to `netlab up`.

## The four pages

- **[Architecture](10-architecture.md)** -- Two-component design (remote server + client/fixtures), request flow from pytest to Netlab, and the internal trust model.
- **[Session Queue](20-session-queue.md)** -- FIFO queue that serializes access to the lab, session states and promotion logic, heartbeat-based liveness detection, and stale session cleanup.
- **[Lab Lifecycle](30-lab-lifecycle.md)** -- How labs are acquired, reused, and torn down; topology identity via SHA-256 content hashing; reference counting; and the cross-process `FileLock` that enforces the one-lab rule.
- **[Topology Format](40-topology-format.md)** -- The contract for topology files Remote Lab accepts: Netlab YAML envelope, supported providers and modules, device kinds, the `extra_files` upload mechanism, and Netlab features explicitly out of scope.

## Who Should Read This

Test authors using `remote_lab_fixture` can usually get by with [Architecture](10-architecture.md) alone. [Session Queue](20-session-queue.md) and [Lab Lifecycle](30-lab-lifecycle.md) matter more if you are operating the server, debugging queue stalls, or contributing to the codebase. [Topology Format](40-topology-format.md) is the right first stop when planning what you can (and cannot) build on top of Remote Lab.
