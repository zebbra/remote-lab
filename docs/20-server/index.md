---
page_purpose: overview
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: intermediate
---

# Server

The Remote Lab server is a FastAPI application that manages exclusive access to Netlab topologies on a remote host. It exposes a REST API for session management, lab acquisition, and health monitoring, and enforces the one-lab-per-host rule through a FIFO session queue.

## What the Server Does

- **Session queue** -- Serializes access so only one client operates the lab at a time. See [Session Queue](../10-concepts/20-session-queue.md) for how queuing and promotion work.
- **Lab lifecycle** -- Acquires, reuses, releases, and destroys Netlab topologies on behalf of clients. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md) for reference counting and teardown details.
- **Heartbeat and cleanup** -- Tracks client liveness via heartbeats and automatically reclaims stale sessions through a background cleanup loop.
- **Single-instance guard** -- Prevents multiple server processes from running concurrently on the same host using a file lock.

## Section Contents

| Page | Purpose |
|------|---------|
| [REST API](10-rest-api.md) | Complete endpoint reference with request/response schemas, status codes, and cURL examples |
| [Configuration](20-configuration.md) | CLI flags, environment variables, server constants, and logging configuration |
| [Administration](30-administration.md) | Starting the server, monitoring, single-instance recovery, and troubleshooting |

## How It Fits Together

The server sits between [clients](../30-client/index.md) (or raw HTTP callers) and the Netlab CLI on the remote host. The [Architecture](../10-concepts/10-architecture.md) page describes this relationship in full. For deployment on a remote VM, see the [Deployment](../50-deployment/index.md) section.
