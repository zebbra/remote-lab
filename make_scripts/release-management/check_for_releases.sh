#!/bin/bash

# Enter the repositories you want to check here, eg. REPOS=("zebbra/neops-web-sdk" "zebbra/neops-core"). Do not separate with commas.
REPOS=()

if [ ${#REPOS[@]} -eq 0 ]; then
  echo "🚫 No repositories found in the REPOS array."
  exit 0
fi

check_latest_commit_and_release() {
  REPO=$1
  latest_release=$(gh api repos/$REPO/releases --jq 'sort_by(.published_at) | reverse | .[0]')

  if [ $? -ne 0 ] || [ -z "$latest_release" ] || [ "$latest_release" == "null" ]; then
    echo "🚫 Error: No releases found for '$REPO'."
    return 1
  fi

  latest_release_date=$(echo $latest_release | jq -r '.published_at')

  latest_develop_commit=$(gh api "repos/$REPO/commits?sha=develop&per_page=1" --jq '.[0]' )

  if [ $? -ne 0 ] || [ -z "$latest_develop_commit" ]; then
    echo "🚫 Error: Unable to fetch the latest commit on develop branch for '$REPO'."
    return 1
  fi

  latest_develop_date=$(echo $latest_develop_commit | jq -r '.commit.committer.date')

  compare_dates "$REPO" "$latest_release_date" "$latest_develop_date"
}

compare_dates() {
  REPO=$1
  RELEASE_DATE=$2
  DEVELOP_DATE=$3

  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[0;33m'
  NC='\033[0m'

if [[ "$DEVELOP_DATE" > "$RELEASE_DATE" ]]; then
    echo -e "⚠️  Repository '${YELLOW}$REPO${NC}': A release might be required."
    echo -e "     -> Latest release: ${YELLOW}$RELEASE_DATE${NC}"
    echo -e "     -> Latest commit on develop: ${YELLOW}$DEVELOP_DATE${NC}"
  else
    echo -e "✅  Repository '${GREEN}$REPO${NC}': Everything is up to date."
    echo -e "     -> Latest release ${GREEN}$RELEASE_DATE${NC}"
    echo -e "     -> Latest commit on develop: ${GREEN}$DEVELOP_DATE${NC}"
  fi
}

for REPO in "${REPOS[@]}"
do
  check_latest_commit_and_release $REPO
done

exit 0
