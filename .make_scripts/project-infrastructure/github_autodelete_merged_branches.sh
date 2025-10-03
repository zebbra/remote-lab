#!/bin/sh

if [[ "$1" == "--force" ]]
    then
        echo "force switch here"
    else 
        read -p "This will activate automatic deletion of head branches on merge. Continue (y/n)? [use --force switch to skip this]: " choice
    case "$choice" in 
    y|Y ) echo "yes";;
    n|N ) echo "no" && exit 1;;
    * ) echo "invalid" && exit 1;;
    esac
fi

output=$(gh api repos/{owner}/{repo} --method PATCH --field 'delete_branch_on_merge=true')
if [ $? -eq 0 ]; then
  echo "✅ Successfully activated automatic deletion of head branches on merge."
else
  echo "🚫 Failed to activate automatic deletion of head branches on merge."
  echo $output
fi
