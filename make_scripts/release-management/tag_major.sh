#!/bin/sh

NEW_TAG=$(git tag | grep v | grep -v - | sed 's/v//' | sort --version-sort --reverse | head -n 1 | awk -F. -v OFS=. '{ $1 += 1; $2 = 0; $3 = 0; print }')
if [ -z "$NEW_TAG" ]; then
  NEW_TAG="1.0.0"
fi
git tag v$NEW_TAG -m "major release" && echo "✅ Created new tag(major): v$NEW_TAG"

