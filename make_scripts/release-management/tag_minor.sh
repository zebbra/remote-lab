#!/bin/sh

NEW_TAG=$(git tag | grep v | grep -v - | sed 's/v//' | sort --version-sort --reverse | head -n 1 | awk -F. -v OFS=. '{ $2 += 1; $3 = 0; print }')
if [ -z "$NEW_TAG" ]; then
  NEW_TAG="0.1.0"
fi
git tag v$NEW_TAG -m "minor release" && echo "✅ Created new tag(minor): v$NEW_TAG"
