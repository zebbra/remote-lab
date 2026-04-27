# Project purpose — neops-remote-lab

<!-- Owned by the project maintainer. Read by docs-improve v3 writers as preamble. -->
<!-- Last interview: 2026-04-21. To refresh: /neops-ai-toolkit:docs-improve-v3 neops-remote-lab --refine -->

## Audience

neops-remote-lab has three co-equal audiences. Each needs its own framing in the docs; do not collapse them into a generic "developer" voice.

### 1. SDK consumer (primary by volume)

Python developers writing pytest-based tests for neops function blocks. Intermediate pytest and fixture fluency, comfortable with environment variables, often first-time users of Netlab, Headscale/Tailscale, and the one-lab-per-host model.

- **Arrival context:** onboarding to neops-worker-sdk-py; debugging a specific test failure (`REMOTE_LAB_URL` unset, `423 Locked`, hang in queue, `filelock` error, containers unreachable); or an occasional deep-dive by a senior who wants to understand session queueing and refcounting before trusting the system.
- **What they know walking in:** pytest, fixtures, pydantic, how worker-sdk function blocks work.
- **What they don't know:** Netlab orchestration internals, Headscale/Tailscale tailnet behavior, the one-lab-per-host invariant, the content-hash topology identity model.
- **What they expect from docs:** crosslinks to worker-sdk docs and to the external tooling (Netlab, Tailscale) rather than re-explanation; clear front-page wayfinding that tells them where to go for what.

### 2. Operator (primary by impact)

Engineers who deploy, maintain, and debug the Remote Lab host. Comfortable with Docker Compose, systemd, VPN configuration, and Linux administration.

- **Arrival context:** standing up a new Remote Lab VM; responding to an incident (stuck queue, stale lock, wedged lab); enrolling new VPN clients; configuring subnet routing; upgrading the service.
- **What they know walking in:** server operation, Docker, Linux networking basics.
- **What they don't know:** remote-lab's internal queue semantics, refcount + content-hash interactions, the exact filelock / atexit recovery rules.
- **What they expect from docs:** structured reference material, tables, architecture diagrams, runbooks, and dense outbound links to Netlab, Containerlab, Headscale, Tailscale. They greatly value deep-dive content and will read it.

Operator scope spans the service itself **and** the surrounding plumbing — Netlab / Containerlab on the host, Headscale / Headplane (or an alternative VPN like WireGuard), subnet routing, node enrollment.

### 3. Contributor (zebbra-internal)

Python engineers on the zebbra team modifying the `neops-remote-lab` codebase itself. External contribution is not actively invited at this time.

- **Arrival context:** opening a PR to fix a bug, add a capability, refactor, or bump a dependency.
- **What they know walking in:** FastAPI, async Python, pytest, Pydantic 2; zebbra's internal conventions.
- **What they don't know (until they read):** the invariants around queue / session / filelock / atexit / `_run_blocking()`; which Netlab invocation paths are allowed; which dependencies carry CVE pins.
- **What they expect from docs:** an invariants reference and contribution-flow content inside the docs tree, not only in AGENTS.md. They may arrive via the user-facing docs as well as AGENTS.md.

### 4. External API user (any stack)

Network-automation engineer at a non-neops organization, mid-to-senior, who reaches the project through OSS channels (a SwiNOG-style conference talk, GitHub discovery, a colleague's recommendation, a search for "Netlab as a service" / "remote lab broker" / "lab-as-a-service") and wants to drive a real Netlab topology from whatever automation harness they already run — possibly Python without pytest, possibly Go, possibly shell, possibly Robot Framework. Test/QA engineers and platform/DevX engineers also self-identify here. Existing three audiences keep their primary positions; this audience is appended, not promoted.

- **Arrival context:** cold-start. No neops context, no familiarity with `neops-worker-sdk-py`, possibly no familiarity with pytest patterns. Found the project, read the README, wants to evaluate whether the HTTP surface fits their existing pipeline.
- **What they know walking in:** networking deeply (BGP, OSPF, vendor configs, the difference between FRR and a real NOS); Netlab and Containerlab as concepts; HTTP/REST APIs at general competence; at least one of Python / Go / shell at scripting depth; their own CI tooling (Jenkins, GitLab CI, GitHub Actions, Drone, etc.).
- **What they don't know:** the neops worker-SDK and function-block model (and don't need to); the session-queue / heartbeat semantics (need to learn); the SHA-256 content-hash topology identity rule; the `.yml` extension trap; the no-auth security posture and why a VPN is non-negotiable.
- **What they expect from docs:** a landing page that reads value-prop-first without forcing them through neops vocabulary; the REST API treated as a first-class consumer surface, not just an internal mechanism; concrete examples in shapes other than pytest (cURL minimum; light pointers to "any HTTP client works"); a quickstart they can complete in their stack of choice without installing the Python client; CI integration guidance (pipeline examples, queue tuning) for when they wire it into their existing harness; a debugging reference they can grep when something breaks.

## Job-to-be-done

The three audiences have genuinely different JTBDs. Writers must pick the frame that matches the page.

**SDK consumer** uses remote-lab to get pytest — local and CI — talking to a running remote lab so function-block tests pass against real topologies. The local task flavors into onboarding, debugging, or deepening understanding. **Outer motivator: ship a working function block to production with confidence it survives real networking, not mocks.** Green CI is a facet of this, not a separate motivator. Senior readers additionally want reference-grade internal knowledge so they can reason about edge cases before they hit them.

**Operator** runs a Remote Lab host smoothly, maintains it, debugs it when something breaks, and handles the surrounding VPN / Netlab plumbing. **Outer motivator: provide remote-lab as reliable team-scoped infrastructure** so SDK consumers and CI can actually run their tests, and so the operator is not the bottleneck during incidents.

**Contributor** extends or fixes remote-lab without breaking (a) the SDK consumer's `remote_lab_fixture` contract or (b) the stability operators depend on. **Outer motivator: keep remote-lab trustworthy as the SDK's test substrate.**

**External API user** wants exclusive, programmatic access to a real Netlab topology over HTTP, callable from whatever automation harness they already run. The framing is plural by design — this audience came in via a SwiNOG-style talk where the room contained "make integration tests routine in CI", "centralize per-developer Netlab installs", "pre-deploy config validation", and "general lab-as-a-service" all at once. **Outer motivator: get real-network behavior into their existing automation pipeline without standing up and operating Netlab themselves.**

## Role in neops

`neops-remote-lab` is **strictly dev/test infrastructure today**. It is not on the production runtime path (CMS → workflow engine → worker → device). It is the **testing surface** that lets developers validate worker-SDK function blocks against real network topologies before those blocks are trusted in production.

- **Consumed by:** `neops-worker-sdk-py` — imports `remote_lab_fixture` from `neops_remote_lab.testing.fixture`. AGENTS.md treats that call signature as a stable public API. The integration is library-level (Python import), not over the wire.
- **Consumes (neops projects):** none at runtime.
- **External neighbors treated as first-class dependencies in the docs:** Netlab / Containerlab (lab orchestration on the host), Headscale / Tailscale (VPN between lab subnets and clients). Operator docs must cross into these tools with confidence and link out rather than re-explain them.
- **Not coupled to:** neops-core, workflow-engine (at runtime), web stack, gateways, storage, helm.

**Aspiration, not current state (frame as such):** workflow-level testing — where a test drives a whole neops workflow against an acquired topology rather than just owning a lab — is an idea under discussion. It is not implemented today and may never be. Docs should frame this as future direction, not current capability.

## Canonical user journeys

Eight journeys. Three per primary audience, two for contributors. Consumer and operator journeys are co-equal; contributor journeys are narrower but present.

### A. First-time onboarding (SDK consumer)
- **Trigger:** Writing tests for a function block; need remote-lab working from a laptop and from CI.
- **Steps:** Install the package → set `REMOTE_LAB_URL` → connect to the VPN (or start a local server) → declare a `remote_lab_fixture` pointing at a topology → run `pytest`.
- **Success signal:** `pytest` passes against a real topology, from both locations.

### B. Debugging a failing test (SDK consumer)
- **Trigger:** A specific symptom — hang in queue, `423 Locked`, containers unreachable, `filelock` error, stale session.
- **Steps:** Identify the failure class → check the matching recovery path → confirm root cause against server logs or queue state.
- **Success signal:** User can classify and act on the failure without reading server source.

### C. Going deeper — reference (SDK consumer)
- **Trigger:** Senior engineer wants to understand session queueing, one-lab-per-host, ref-counting, heartbeat semantics, atexit cleanup, content-hash identity — before trusting the system.
- **Steps:** Read architecture / invariants pages → trace the fixture-to-server flow → follow outbound links to Netlab for orchestration-layer details.
- **Success signal:** Engineer can predict server behavior in edge cases without running it.

### D. Setup a new Remote Lab (operator)
- **Trigger:** Standing up a new VM; occasionally a local Ubuntu dev machine for local-only work.
- **Steps:** Rootless Netlab + Containerlab install → Headscale/Headplane deployment (or alternative VPN) → start the service → validate with `netlab test clab` and a remote `curl /healthz` → confirm a client can reach lab subnets.
- **Success signal:** Server up, `netlab test clab` passes, VPN connecting clients, `REMOTE_LAB_URL` works from a laptop. For the local-dev variant: server runs locally and `REMOTE_LAB_URL=http://localhost:8000` makes tests pass.
- **Note:** Primarily VM-focused; include an explicit "Ubuntu developers can run this locally" side-path.

### E. Keep it running / recover from incidents (operator)
- **Trigger:** Stale lab, stuck filelock, wedged queue, someone can't release, crashed prior process.
- **Steps:** Classify the incident → apply the matching recovery (stale-lock removal, `netlab down --cleanup`, force-destroy lab with `X-Session-ID`, restart server) → verify health.
- **Success signal:** Service restored; operator knows what happened and why.

### F. VPN-specific (operator)
- **Trigger:** Enroll a new client, fix routing, swap Headscale for WireGuard, debug why a client can't reach the lab subnet.
- **Steps:** Inspect tailnet state → confirm subnet routes are advertised and approved → verify forwarding / Docker iptables settings on the host → validate from a peer.
- **Success signal:** Clients can reach lab subnets.

### G. Making any substantive change (contributor)
- **Trigger:** Bug fix, new feature, refactor, or larger restructure.
- **Steps:** Branch from `develop` → read AGENTS.md invariants → implement → `make check` → open PR.
- **Success signal:** `make check` green, invariants preserved, PR merged. This is the **main** contributor journey; it scales from small fixes to large refactors.

### H. Upgrading a dep safely (contributor)
- **Trigger:** CVE alert or scheduled dep bump.
- **Steps:** Identify pin reason (`# CVE-*` comments in `pyproject.toml`) → bump to a version that preserves the fix → regenerate `uv.lock` → `make audit` → `make check`.
- **Success signal:** Pin comments preserved or updated, `make audit` clean, no behavior regression.

### I. Driving a remote lab from a non-Python automation harness (External API user)
- **Trigger:** Existing CI/CD or test harness in Go, Bash, Robot Framework, Ansible, or another stack needs exclusive access to a Netlab topology.
- **Steps:** Find/stand up a Remote Lab Manager → set the base URL → POST /session → poll until ACTIVE → POST /lab with a topology → drive the devices → POST /lab/release → DELETE /session.
- **Success signal:** Their existing pipeline gets a fresh-or-shared lab on every run; teardown is automatic; they never imported a Python package.

## Non-obvious truths

Invariants and gotchas that are not obvious from code or a README skim. Classified by audience — show each audience only what affects them.

### For SDK consumers
- **Topology identity is the SHA-256 of file content, not the filename.** Two files with different names and identical content are the same topology; `reuse=True` matches. Edit one byte and it is a new topology; `reuse=True` will not match. Most systems key on filename — this one does not.
- **One `remote_lab_fixture` per test — enforced at *collection* time.** `pytest_order_plugin` rejects the test during collection, so a two-fixture test does not appear as a runtime failure.
- **Authentication is stubbed.** `X-Session-ID` is the only gate on `/lab/*`; non-active sessions receive `423 Locked`. The `REMOTE_LAB_TOKEN` / Bearer path in `client.py` is commented out. Treat the service as internal-trust.
- **Heartbeat timing is invisible but load-bearing.** Waiting sessions drop after 600 s of no movement; active sessions go stale after 300 s without a heartbeat. A debugger breakpoint mid-test can cost the lab.

### For operators
- **The filelock is cross-process and survives crashes.** A crashed prior server leaves a stale lockfile; the new server refuses to start with "another instance is running." Recovery is investigate-and-remove, not restart-and-hope. Lock path is in AGENTS.md → Invariants.
- **Netlab `default` instance leaks across crashes.** The server clears it at startup, but if you have been running `netlab` by hand, `netlab down --cleanup` is required before the next run.

### For contributors
- **CI does not install Netlab.** Server tests use a stubbed `LabManager`. Any test path that actually needs Netlab must be explicitly gated; otherwise it silently fails to exercise real behavior.
- **`atexit` cleanup is a real path.** Registered silently with logging disabled — deliberate, to avoid closed-stream errors. Never add async code; it will deadlock at process exit.
- **`try_acquire()` vs `acquire()` matters.** Non-blocking from the server, blocking-poll from local fixtures. Wrong one from wrong context = deadlock or busy-spin.
- **CVE-pinned dependencies.** Several pins in `pyproject.toml` carry `# CVE-*` comments. Upgrades must preserve them (or replace with a newer safe version) and re-run `make audit`.
- **Blocking I/O in async handlers must go through `_run_blocking()`** (see `server.py`) — lands on the thread-pool executor instead of the event loop.
- **Netlab is only invoked via `neops_remote_lab.netlab.connector.run_netlab()`** — never shell out directly.
- **Pydantic 2 request/response models are suffixed `*Dto`.** Convention is load-bearing for code review.

## Differentiators

**Core differentiator:** an **on-demand, lifecycle-managed, queue-brokered Netlab broker** with a **pytest-native fixture** baked in, designed for the neops function-block testing flow. The SDK consumer does not write `up`/`down` scripts; the fixture handles spawn, teardown, and exclusivity. Tests don't know about infrastructure.

**Why not the alternatives:**
- **Run Netlab locally.** Requires Netlab install and real compute per machine; does not scale to CI; does not share the expensive setup across a team.
- **Docker Compose with Containerlab directly.** Valid, but you own the up/down scripts, the teardown timing, the exclusive-access handshaking, and the pytest integration. Remote-lab makes this disappear behind a fixture — that is the leverage.
- **Kubernetes operator for labs.** CRDs, RBAC, orchestration. Overkill for one topology at a time on one VM. Remote-lab is deliberately small.
- **Commercial network-lab services (EVE-NG, Cisco Modeling Labs, GNS3 Server).** Commercial licensing, not pytest-integrated, not tied to the neops function-block contract.
- **Mock the network.** Already rejected by the neops testing philosophy. Function blocks need real topology behavior before production.
- **One Netlab host per CI run or developer.** `netlab up` takes minutes and images are large. Remote-lab's `reuse=True` + content-hash identity + refcounting means a fleet of tests sharing one topology pays setup cost once.

**Concrete "nothing else like this":**
- `remote_lab_fixture` is a stable, library-level public API. Declare a topology file, get exclusive access on a shared remote host, share across tests via refcount — this signature is not present elsewhere in the neops ecosystem or the wider network-automation-testing space that we have seen.
- Topology identity = SHA-256 of content. Rename → same lab; edit → new lab.

**Supporting: deliberately simple.** One FastAPI service, one filelock, one pytest plugin. That simplicity is part of why lifecycle management stays lightweight.

## Anti-patterns

### SDK consumer — don't
- **Declare two `remote_lab_fixture`s in one test** — rejected at collection.
- **Rely on filename identity** — content hash is the key.
- **Hardcode `X-Session-ID`** — let the session fixture manage it.
- **Let a test stall mid-run** — heartbeat-dependent; a 300 s breakpoint loses the lab.
- **Talk to the service over a public network** — no auth; inside the VPN boundary or localhost only.

### Operator — don't
- **Expose port 8000 publicly** — same reason, no auth layer.
- **"Fix" stale locks without investigating** — they signal a crash; blind removal hides recurring problems.
- **Upgrade Netlab without re-running `netlab test clab`** — Netlab is the dependency most likely to silently break the host.
- **Run two remote-lab servers on one host** — filelock catches this; don't work around it.
- **Run `netlab` by hand while the server is running** — state divergence, default-instance conflicts.

### Contributor — don't
- **Shell out to `netlab` directly** — always via `connector.run_netlab()`.
- **Do blocking I/O in an async handler without `_run_blocking()`**.
- **Add async code to the `atexit` cleanup path** — deadlock at exit.
- **Drop the `*Dto` suffix on Pydantic request/response models**.
- **Remove `# CVE-*` comments on dep upgrades** — preserve or replace with a newer safe version and re-run `make audit`.

### External API user — don't
- **Skip the heartbeat in long-running clients** — a 5-minute pause without polling/heartbeat means the session goes stale and the lab gets reaped from under you.
- **Talk to the service over a public network** — there's no auth; the `X-Session-ID` is not a secret. Internal-trust only; deploy behind a VPN or trusted network.
- **Treat `reuse=true` as cheap when your test mutates device configs** — reuse means another caller may attach to the same lab and see your mutations.
- **Hardcode the SHA-256 topology hash anywhere** — it's a server-side identity; clients never need to compute or send it.

## Voice and tone

- **Second-person, active voice.** Address the reader directly.
- **Opinionated, not deferential.** "One-lab rule," not "we recommend running at most one lab." The invariants are real; the writing should sound like we know them.
- **Tight for task-flow, structured for reference.** SDK consumer onboarding and CI-green paths are short, scannable, code-forward. Operator deep-dives are structured with headers, tables, sequence diagrams — operators value structure and will read it.
- **Contributor register is tighter and more technical.** Same voice, assumes the reader has read the overview, links back to AGENTS.md where relevant. Think "AGENTS.md as a chapter inside the docs," not a separate dialect.
- **Dense outbound linking.** Link to Netlab, Containerlab, Headscale, Tailscale, and worker-sdk docs. Treat external docs as first-class references; link out rather than re-explain.
- **Primary example style: `remote_lab_fixture` + Python pytest code.** Use curl to *showcase* the REST surface (what endpoints look like, what happens under the hood), not as the teaching onramp.
- **No emojis.** The opinionated-tight register drops them.
- **Placeholders over hard-coded internal IPs in the mkdocs site.** Use `<REMOTE_LAB_VM_IP>` / `$HEADSCALE_HOST` consistently. The zebbra Hetzner IP may remain in the `README.md` only — not in the docs tree.

Reference points, not gold standards: the neops-worker-sdk-py docs are close cousins; remote-lab's voice may echo them but should not copy them slavishly. Zebbra's docs-writing conventions exist but are being reworked — treat them as useful signal rather than canonical.

## What existing docs get wrong

The docs on this branch are at a strong v2-ish level — near-complete coverage (index, quickstart, architecture, session-queue, lab-lifecycle, topology-format, pytest-fixtures, remote-lab-client, rest-api, configuration, administration, netlab_configuration, headscale_headplane), already second-person / opinionated / code-forward / no-emoji, trace-comment annotated, generally factually grounded. This is **not a greenfield rewrite** — it is targeted fill-in plus a few bugs plus reconciliation to this purpose.md.

### Structural gaps — what must be added for Monday

- **Contributor content is still missing from the docs tree.** SDK consumers have `quickstart.md` + `pytest-fixtures.md`; operators have `administration.md`; contributors have `AGENTS.md` and nothing else inside `docs/`. The invariants a contributor needs before touching queue / session / filelock / atexit code are not surfaced in the user-facing docs. An **"Invariants" or "Contributing" page** is the missing piece — enforced conventions (`_run_blocking()`, `connector.run_netlab()`, `*Dto` suffix, CVE pin comments, no-async-in-atexit), the G + H contributor journeys, branch/`make check`/PR flow.
- **`index.md`'s audience mapping drifts from this purpose.md.** The "Who uses this?" grid has four cards (test authors, concepts explorers, integrators, operators); this purpose.md names three audiences (SDK consumer, operator, contributor). "Concepts explorers" is better modeled as **Journey C** on the SDK consumer path, not a separate audience. "Integrators" overlaps SDK consumer. **No contributor card.** Reconcile to three audiences; point the contributor card at the new Invariants / Contributing page.
- **Journey D's local-dev side-path is not explicit anywhere.** The purpose.md calls out that Ubuntu developers can run the server locally and point `REMOTE_LAB_URL=http://localhost:8000`. `configuration.md` lists `REMOTE_LAB_URL` as "required" with no default; `quickstart.md` assumes a reachable `$LAB_HOST`; neither teaches the localhost path. Add the side-path to `quickstart.md` (before-you-start) and to `configuration.md` or `administration.md` (install).

### Link / reference bugs to fix

- `docs/index.md` line 29 (`[neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py)`) and the "External references" section at the bottom — `README.md` and `AGENTS.md` link to `https://github.com/zebbra/neops` (not the `neops-remote-lab` repo). Broken / wrong repo. Fix to the actual URLs.
- `docs/netlab_configuration.md` troubleshooting table contains a meta entry ("Forward link to `testing-framework.md` is broken — update references to point at [Pytest fixtures] and [Quickstart]") — this is a message to external callers, not a user troubleshooting item. Remove from the user-facing troubleshooting table; retain the forwarding links in the page body.

### Content drift to reconcile

- `docs/architecture.md` ecosystem diagram shows `fb_tests` (function-block test suites) as a direct consumer alongside `worker_tests`. This purpose.md + AGENTS.md name `neops-worker-sdk-py` as *the* primary consumer. Either tighten the diagram to match (fb_tests are downstream of worker-sdk, not direct consumers) or explicitly note why the two paths exist. Current shape reads as overselling direct consumption.
- `docs/headscale_headplane.md` correctly warns about the shipped zebbra dev IP in `headscale/config/config.yaml:13` and `headscale/headplane.config.yaml`. The docs are honest; the **source config files still carry the baked-in IP**. Scope call, not a docs fix: clean up the shipped config in this pass, or only fix the docs.
- `docs/index.md` reading-path time estimates ("~15 min", "~25 min", "~45 min", "~20 min") are unverified commitments. Consider softening to "a focused read" / "a deep read" unless someone actually timed these.

### Minor polish

- The pytest plugin check in `quickstart.md` (`pytest --trace-config 2>&1 | grep remote_lab`) matches but the pytest entry-point name is `neops-remote-lab` (from `pyproject.toml` `[project.entry-points.pytest11]`). Slight disconnect between expected and actual match text; worth a one-line note or a better grep string.
- Trace comments reference specific source line numbers (`server.py:390`, `lab_manager.py:172`, etc.). These will drift if the source changes. Not a bug today; a maintenance concern for the next refactor. v3-insights: consider whether trace comments should be generated / validated by a pipeline step rather than hand-maintained.

### Tonal / style — what is already right

Voice is opinionated second-person. No emojis. Curl is used where it belongs (end-to-end REST walkthroughs in `rest-api.md`, not as the teaching onramp in `quickstart.md`). Admonitions are consistent across pages. This matches the Area 8 frame — do not regress it.

---

## Meta

- **Interview conducted:** 2026-04-21
- **Interview mode:** fresh
- **Area 9 rewritten after reading this branch's existing docs** — initial draft (on branch `docs/v3-purpose-test-2026-04-21`) assumed basically-all-missing; target branch already has a strong docs set.
- **Uncertain sections (revisit next refinement):** none — all nine coverage areas were answered substantively. Remaining uncertainty is downstream; writers will surface per-page gaps the interview could not.
- **Interviewer model:** claude-opus-4-7
- **Cleanup task flagged during interview (for the user, not this skill):** `neops-workflow-engine-client` is pinned in `pyproject.toml` and locked in `uv.lock`, but unused in source (greps of `workflow_engine`, `workflow-engine`, `neops_workflow_engine`, `blackboard`, `WorkflowEngine`, `WorkflowClient` across `*.py` return zero imports). Remove the pin, regenerate the lock, re-run `make audit`.
