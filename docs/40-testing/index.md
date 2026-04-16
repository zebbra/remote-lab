---
page_purpose: overview
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Testing

Remote Lab supports two testing modes: **local** (Netlab runs directly on your machine) and **remote** (Netlab runs on a shared server). The same `remote_lab_fixture` factory works in both modes -- the `REMOTE_LAB_URL` environment variable controls which path executes. This section covers setup, workflows for each mode, and debugging techniques.

## Guides in This Section

| Page | When to read |
|------|-------------|
| [Test Environment Setup](10-setup.md) | First time setting up a project that uses Remote Lab fixtures |
| [Local Lab Testing](20-local-testing.md) | Running tests against Netlab on your own machine (no server needed) |
| [Remote Lab Testing](30-remote-testing.md) | Running tests against a shared Remote Lab server, including CI |
| [Debugging and Troubleshooting](40-debugging.md) | Something broke -- logs, HTTP errors, common failure patterns |

## Who Should Read What

**Test authors** writing or maintaining network tests should start with [Test Environment Setup](10-setup.md) and then read the guide matching your mode (local or remote). Skim the other mode's page for awareness.

**CI/CD engineers** integrating Remote Lab into pipelines should focus on [Remote Lab Testing](30-remote-testing.md) for timeout tuning and ordering strategies, then [Debugging and Troubleshooting](40-debugging.md) for interpreting failures in headless runs.

**Server operators** who also write tests should read all four pages -- particularly [Local Lab Testing](20-local-testing.md) to understand how the `LabManager` behaves when there is no server in the picture.
