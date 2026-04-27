---
title: How Remote Lab fits with neops
description: For Neops devs and External API users alike — which neops concepts apply to Remote Lab, which don't, and how Remote Lab connects to the wider platform.
tags: [reference, appendix, ecosystem]
crosslink_defines: []
crosslink_references: []
---

# How Remote Lab fits with neops

If you arrived here from a peer neops project, you'll have words like *function block*, *worker*, *workflow* in your mental model. **Most of them don't apply to Remote Lab itself.** Remote Lab is the test substrate the rest of the platform runs network-automation tests against; it doesn't run workflows, it doesn't host workers, it doesn't read the blackboard. This page maps the shared vocabulary so you don't trip on shape-mismatches.

If you arrived from outside neops entirely, this page is a guided tour of the surrounding pieces — safely skippable if you only care about driving the lab.

## What Remote Lab actually is

A FastAPI service plus a pytest11 plugin. The service runs on a Netlab host and serializes lab access via a FIFO queue. The plugin (`remote_lab_fixture`) is the **stable public API** consumed directly by [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/) test suites.

Remote Lab consumes nothing at runtime: it has no workflow engine to call, no blackboard to read, no upstream service to register with. The Worker SDK consumes it, and the Worker SDK is the only neops project that does.

## Peer-project terminology

| Term | What neops uses it for | Remote Lab's stance |
|---|---|---|
| **Function block** | A typed Python class implementing one unit of automation work — read configs, push templates, check compliance, discover inventory — orchestrated by the workflow engine. ([Worker SDK → Function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/), [Workflow Engine → Function blocks](https://docs.neops.io/neops-workflow-engine/docs/10-concepts/20-function-blocks/)) | **Consumer of**, not part of. Remote Lab gives function-block tests a real topology to run against. |
| **Worker** | A Python process that registers with the workflow engine, polls for jobs from the blackboard, executes function blocks, and writes results back. ([Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/)) | **Not applicable** to the Remote Lab service. The Worker SDK *imports* `remote_lab_fixture` for its own tests. |
| **Workflow** | A versioned, declarative description of an ordered sequence of operations on network entities. Authored as YAML, executed by the workflow engine. ([Workflow Engine → Workflows](https://docs.neops.io/neops-workflow-engine/docs/10-concepts/10-workflow/)) | **Not applicable.** Remote Lab does not run workflows. |
| **Workflow engine** | The NestJS service that validates, schedules, and orchestrates workflow execution. ([Workflow Engine](https://docs.neops.io/neops-workflow-engine/docs/)) | **Not applicable.** Remote Lab runs independently of it. |
| **Blackboard** | The shared job queue between the workflow engine and workers — the engine writes jobs, workers read and return results. ([Workflow Engine → Blackboard](https://docs.neops.io/neops-workflow-engine/docs/10-concepts/60-blackboard/)) | **Different mechanism, different scope.** Remote Lab's [session queue](../10-concepts/20-session-queue.md) serializes exclusive lab access; the blackboard decouples workers from the engine. Same word "queue", unrelated systems. |
| **Provider** | In neops-core's legacy automation-class sense, a provider is a vendor-driver abstraction. | **Defines its own.** In a Remote Lab topology, `provider:` is [Netlab](https://netlab.tools/)'s runtime selector (`clab`, `libvirt`, …). Unrelated to the neops-core sense. |
| **Context** (`WorkflowContext`) | The typed object that carries entity data between function-block steps within a running workflow. ([Workflow Engine → Context](https://docs.neops.io/neops-workflow-engine/docs/10-concepts/30-context/)) | **Defines its own shape.** Remote Lab returns device data via flat `DeviceInfoDto` objects — different shape, different scope. |
| **Heartbeat** | A worker→engine liveness ping. | **Different scope.** Remote Lab's `POST /session/heartbeat` is a client→server session keepalive ([Session Queue → The heartbeat](../10-concepts/20-session-queue.md#the-heartbeat)). Same word, different relationship. |
| **Checks / Scope** | neops-platform terms for compliance verification and entity-set scoping. | **Not applicable.** Remote Lab has no compliance or entity model — it manages lab sessions. |

## Consumed-by, consumes

```
neops-worker-sdk-py  ──────► neops-remote-lab  ──────► Netlab + Containerlab
       (consumes the                                        (host-local
        fixture as a                                         orchestrator)
        stable API)
```

- **Consumed by:** the [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/) imports `remote_lab_fixture` directly. Its [Remote lab testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) is the integration entry point.
- **Consumes (at runtime):** nothing. Netlab is a subprocess, not a service.
- **Consumes (at test time):** the same Netlab host the service runs on top of.

## See also

- **[Glossary](glossary.md)** — Remote-Lab-specific terminology, cross-linked to the page where the concept is fully explained.
- **[Architecture](../10-concepts/10-architecture.md)** — the three components and their coordination, with the Ecosystem-position diagram.
- **[neops platform docs](https://docs.neops.io/)** — the umbrella site hosting all neops project docs.
- **[Worker SDK → Remote lab testing](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/)** — the canonical consumer integration path.
