#!/usr/bin/env bash
# Create a session and poll until it reaches ACTIVE.
#
# The Python client and pytest fixture do this automatically with exponential
# backoff; this script is the equivalent for shell-based callers.
#
# Usage:
#   LAB_HOST=lab.example.com:8000 ./examples/curl/poll_until_active.sh

set -euo pipefail

: "${LAB_HOST:?LAB_HOST must be set, e.g. LAB_HOST=lab.example.com:8000}"

SESSION=$(curl -s -X POST "http://$LAB_HOST/session" | jq -r .session_id)

while true; do
    STATUS=$(curl -s "http://$LAB_HOST/session/$SESSION" | jq -r .status)
    [[ $STATUS == "active" ]] && break
    sleep 5
done

echo "$SESSION"
