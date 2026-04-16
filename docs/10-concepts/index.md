---
page_purpose: overview
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: beginner
---

# Concepts

Remote Lab's design follows from a single Netlab constraint: only one topology can run per host at any time. Everything else -- the session queue, reference counting, content hashing -- exists to make that constraint safe and efficient in a multi-user, multi-test environment.

These pages explain the core ideas you need before working with the server or writing tests.

## In This Section

- **[Architecture](10-architecture.md)** -- Two-component design (remote server + client/fixtures), request flow from pytest to Netlab, and the internal trust model.

- **[Session Queue](20-session-queue.md)** -- FIFO queue that serializes access to the lab, session states and promotion logic, heartbeat-based liveness detection, and stale session cleanup.

- **[Lab Lifecycle](30-lab-lifecycle.md)** -- How labs are acquired, reused, and torn down; topology identity via SHA-256 content hashing; reference counting; and the cross-process `FileLock` that enforces the one-lab rule.

## Who Should Read This

If you are writing tests that use `remote_lab_fixture`, the [Architecture](10-architecture.md) page gives you enough context to understand what happens when your tests run. The [Session Queue](20-session-queue.md) and [Lab Lifecycle](30-lab-lifecycle.md) pages matter more if you are operating the server, debugging queue stalls, or contributing to the codebase.
