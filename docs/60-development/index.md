---
page_purpose: overview
personas_served: [devops-engineer]
difficulty_level: intermediate
---

# Development

Why the server holds one lab and only one lab, and what that costs you when the test suite grows -- that is what this section explains, together with the module graph, the Pydantic DTOs on the wire, and how to get changes landed.

| Page | What it covers |
|------|----------------|
| [Internal Architecture](10-architecture.md) | Module dependency graph, async/sync boundaries, state management patterns, lifecycle hooks |
| [Data Models](20-data-models.md) | All Pydantic DTOs and enums with field types, descriptions, and relationships |
| [Contributing](30-contributing.md) | Dev environment setup, code style, CI pipeline, testing approach |

If you are looking for the high-level component overview (server, client, request flow), start with [Concepts > Architecture](../10-concepts/10-architecture.md) instead. This section goes deeper into implementation details for contributors working on the codebase itself.
