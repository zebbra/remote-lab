#!/usr/bin/env bash
# End-to-end Remote Lab Manager session via the REST API.
#
# Walks: create a session -> wait for ACTIVE -> upload topology -> release ->
# delete session. Use as a copy-pasteable reference; for production the Python
# client is preferred (examples/scripts/smoke.py).
#
# Usage:
#   BASE_URL=http://lab.example.com:8000 \
#     ./examples/curl/end_to_end_session.sh tests/topologies/simple_frr.yml

set -euo pipefail

: "${BASE_URL:?BASE_URL must be set, e.g. BASE_URL=http://lab.example.com:8000}"
TOPOLOGY="${1:?Usage: $0 <topology.yml>}"

# 1. Create a session (blocks only if the queue is non-empty on the server)
SESSION_ID=$(curl -s -X POST "$BASE_URL/session" | jq -r .session_id)

# 2. Wait for ACTIVE
while true; do
  STATUS=$(curl -s "$BASE_URL/session/$SESSION_ID" | jq -r .status)
  [[ "$STATUS" == "active" ]] && break
  sleep 2
done

# 3. Acquire the lab
curl -s -X POST "$BASE_URL/lab" \
  -H "X-Session-ID: $SESSION_ID" \
  -F "topology=@${TOPOLOGY}" \
  -F "reuse=true" | jq .

# 4. Run your automation against the devices listed in the response...

# 5. Release the ref-count, then end the session
curl -s -X POST "$BASE_URL/lab/release" -H "X-Session-ID: $SESSION_ID"
curl -s -X DELETE "$BASE_URL/session/$SESSION_ID"
