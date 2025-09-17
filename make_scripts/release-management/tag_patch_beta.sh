#!/bin/sh

CURRENT_TAG=$(git tag | grep v | grep -v - | sed 's/v//' | sort --version-sort --reverse | head -n 1)
CURRENT_BETA_TAG=$(echo $CURRENT_TAG | awk -F. -v OFS=. '{ $3 += 1; print }')
CURRENT_BETA_TAG=$(echo $(git tag | grep $CURRENT_BETA_TAG | sed 's/v//' | sort --version-sort --reverse | head -n 1))
if [ -z "$CURRENT_BETA_TAG" ]; then
    NEW_BETA_TAG=$(echo $CURRENT_TAG | awk -F. -v OFS=. '{ $1 += 0; $2 += 0; $3 += 1; print }')
    git tag v$NEW_BETA_TAG-beta.1 -m "patch-beta release" && echo "✅ Created new tag(patch-beta): v$NEW_BETA_TAG-beta.1"
else
    echo "Current beta tag: $CURRENT_BETA_TAG"
    NEW_BETA_TAG=$(echo $CURRENT_BETA_TAG | awk -F. -v OFS=. '{ $4 += 1; print }')
    git tag v$NEW_BETA_TAG -m "patch-beta release" && echo "✅ Created new tag(patch-beta): v$NEW_BETA_TAG"
fi
