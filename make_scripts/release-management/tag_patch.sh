#!/bin/sh

NEW_TAG=$(git tag | grep v | grep -v - | sed 's/v//' | sort --version-sort --reverse | head -n 1 | awk -F. -v OFS=. '{
 $3 += 1; print }')
 if [ -z "$NEW_TAG" ]; then
   NEW_TAG="0.0.1"
 fi
BRANCH=$(git branch --show-current)
if [[ $BRANCH == hotfix/* ]] || [[ $BRANCH == patch/* ]] || [[ $BRANCH == main ]]; then
  git tag v$NEW_TAG -m "patch release" && echo "✅ Created new tag(patch): v$NEW_TAG"
else
  echo "🚫 A patch should only be created on hotfix/*, patch/* or the main branch to prevent accidental breaking changes. Current branch: $BRANCH"
fi
