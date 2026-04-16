---
page_purpose: tutorial
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Setup

Before you can run tests against a remote lab, you need the `neops-remote-lab` Python package installed and one environment variable set. This page walks through both.

!!! info "Server already running?"
    This guide assumes your team already has a Remote Lab server running on a shared VM. If that is not the case, see [Deployment](../50-deployment/index.md) first.

!!! info "Going local instead?"
    If you don't have a Remote Lab server available and don't want to set one up, skip this page and go straight to [Local Lab Testing](../40-testing/20-local-testing.md). Local mode runs Netlab directly on your machine via `LabManager` — no server, no VPN. Come back here when you're ready to use a shared server.

## Prerequisites

- **Python 3.12 or later** -- check with `python3 --version`
- **pip** or **uv** -- any recent version
- **`curl`** and **[`jq`](https://jqlang.org/)** -- used in the next tutorial's cURL walkthrough; install via `apt install jq` / `brew install jq` if missing
- **Network access** to the Remote Lab server (typically via a [Tailscale/Headscale VPN](../99-appendix/glossary.md#headscale) or direct connectivity)

## Install the package

=== "pip"

    ```bash
    pip install neops-remote-lab
    ```

=== "uv"

    ```bash
    uv add neops-remote-lab
    ```

Verify the installation:

```bash
python -c "import neops_remote_lab; print(neops_remote_lab.__version__)"
```

You should see a version string like `0.5.0` (the exact number will differ).

## Configure the server URL

Remote Lab needs to know where the server lives. Set the `REMOTE_LAB_URL` environment variable to the base URL of your team's server:

```bash
export REMOTE_LAB_URL=http://<host>:8000
```

Replace `<host>` with the IP address or hostname your team uses. For example:

```bash
export REMOTE_LAB_URL=http://91.99.184.46:8000
```

!!! tip "Make it permanent"
    Add the export to your shell profile (`~/.bashrc`, `~/.zshrc`) or keep settings in a project-local `.env` file. A minimal `.env` for this guide:

    ```bash title=".env"
    REMOTE_LAB_URL=http://91.99.184.46:8000
    # REMOTE_LAB_SESSION_TIMEOUT=600       # uncomment to override defaults
    # REMOTE_LAB_ACQUISITION_TIMEOUT=600
    ```

    Load it into the current shell:

    ```bash
    set -a && source .env && set +a
    # or, equivalently:
    export $(grep -v '^#' .env | xargs)
    ```

    For Python-only loading, pair the file with [python-dotenv](https://pypi.org/project/python-dotenv/); for shell-level auto-load on `cd`, use [direnv](https://direnv.net/).

### Optional timeout variables

The client ships with sensible defaults, but you can override them if your environment needs different values:

| Variable | What it controls | Default |
|----------|-----------------|---------|
| `REMOTE_LAB_REQUEST_TIMEOUT` | Per-HTTP-request timeout (seconds) | 30 |
| `REMOTE_LAB_SESSION_TIMEOUT` | How long the client waits in the session queue (seconds) | 600 |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Max wait for lab topology to come up (seconds) | 600 |

The session and acquisition timeouts are deliberately long because `netlab up` can take minutes to bring up a full topology.

## Verify connectivity

A quick way to confirm you can reach the server:

```bash
curl -s $REMOTE_LAB_URL/healthz -w "\nHTTP %{http_code}\n"
```

Expected output:

```
HTTP 204
```

If you get a connection error, confirm your VPN is up and the server is running.

## Next step

Your environment is ready. Head to [Your First Lab Session](20-first-lab.md) to walk through the full lifecycle with cURL before integrating with pytest.
