#!/bin/sh

if [[ "$1" == "--force" ]]
    then
        echo "force switch here"
    else 
        read -p "This will (create) set the default branch to [develop]. Continue (y/n)? [use --force switch to skip this]: " choice
    case "$choice" in 
    y|Y ) echo "yes";;
    n|N ) echo "no" && exit 1;;
    * ) echo "invalid" && exit 1;;
    esac
fi

git checkout -b develop 2>/dev/null
git push -u origin develop 2>/dev/null

output=$(gh api repos/{owner}/{repo} --method PATCH --field 'default_branch=develop')

if [ $? -eq 0 ]; then
  echo "✅ Successfully set the default branch to 'develop'."
else
  echo "🚫 Failed to set the default branch to 'develop'."
  echo $output
fi
