#!/usr/bin/env bash
# Force-destroy a stuck lab via the REST API.
#
# Use when a lab is wedged: netlab up failed partway through, or a client
# crashed without releasing. Requires LAB_HOST to point at the Remote Lab
# Manager (e.g. lab.example.com:8000).
#
# Usage:
#   LAB_HOST=lab.example.com:8000 ./examples/scripts/force_cleanup.sh

set -euo pipefail

: "${LAB_HOST:?LAB_HOST must be set, e.g. LAB_HOST=lab.example.com:8000}"

SESSION_ID=$(curl -s -X POST "http://$LAB_HOST/session" | jq -r .session_id)

# Wait for ACTIVE
while [[ "$(curl -s "http://$LAB_HOST/session/$SESSION_ID" | jq -r .status)" != "active" ]]; do
  sleep 2
done

# Force destroy the lab
curl -s -X DELETE "http://$LAB_HOST/lab?force=true" \
  -H "X-Session-ID: $SESSION_ID"

# End the cleanup session
curl -s -X DELETE "http://$LAB_HOST/session/$SESSION_ID"

echo "Lab force-destroyed; cleanup session ended."
