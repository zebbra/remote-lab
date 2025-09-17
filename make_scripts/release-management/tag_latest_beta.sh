#!/bin/sh

CURRENT_BETA_TAG=$(git tag | grep b | grep v | sed 's/v//' | sort --version-sort --reverse | head -n 1)
if [ -z "$CURRENT_BETA_TAG" ]; then
    NEW_TAG=$(git tag | grep v | sed 's/v//' | sort --version-sort --reverse | head -n 1)
    if [ -z "$NEW_TAG" ]; then
        NEW_TAG="0.1.0"
        git tag v$NEW_TAG-beta.1 -m "beta release" && echo "✅ Created new tag(beta): v$NEW_TAG-beta.1"
    else
        while read NEW_TAG; do git tag v$NEW_TAG-beta.1 -m "beta release" && echo "✅ Created new tag(beta):
        v$NEW_TAG-beta.1"; done <<< "$NEW_TAG"
    fi
else
    echo "Current beta tag: v$CURRENT_BETA_TAG"
    NEW_BETA_TAG=$(echo $CURRENT_BETA_TAG | awk -F. -v OFS=. '{ $4 += 1; print }')
    git tag v$NEW_BETA_TAG -m "beta release" && echo "✅ Created new tag(beta): v$NEW_BETA_TAG"
fi
