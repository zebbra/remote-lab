---
page_purpose: index
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Appendix

The three pages in this section exist to back up the rest of the documentation, not to teach anything new. Think of them as the place you bounce to when you hit an unfamiliar term, need a runnable snippet to paste, or want to follow a link out to upstream docs for Netlab, Containerlab, or Tailscale.

## What you will find, and why

**[Glossary](glossary.md)** — one page that gathers every load-bearing term the project uses, grouped by domain: session queuing, labs and topologies, locking and concurrency, data models, testing, and networking infrastructure. A second group at the bottom bridges to the wider [neops platform](https://github.com/zebbra) so that readers arriving from the worker SDK or workflow engine can see where Remote Lab's vocabulary diverges from (or aligns with) peer-project terms like `function block`, `blackboard`, or `worker`. If a term in the main docs seems under-defined, this is the first place to check.

**[Examples](examples.md)** — an index of the runnable snippets that live inside the tutorials and reference pages. Organised by audience (cURL for terminal walk-throughs, Python client for programmatic use, pytest fixtures for test authors) and by topology file. Each row points to the page the snippet lives on, so you are never looking at a snippet stripped of its surrounding narrative. Use it when you remember "there was a curl command for uploading extra files" but not which page.

**[Resources](resources.md)** — outbound links to the projects this service wraps (Netlab, Containerlab), the VPN layer (Headscale, Tailscale), the Python frameworks (FastAPI, pytest, `logging`), and the neops ecosystem. Nothing here is authored by this project; it is the map of where Remote Lab's authority ends and upstream documentation takes over.

## When to use which page

If you hit a word you do not recognise, go to the glossary. If you know what you want to do but not how the snippet starts, go to examples. If you need the authoritative reference for a tool Remote Lab depends on, go to resources.
