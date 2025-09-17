#!/bin/sh

read -p "This will delete all local tags and fetch tags from remote repository. Continue (y/n)?" choice
case "$choice" in 
y|Y ) echo "yes";;
n|N ) echo "no" && exit 1;;
* ) echo "invalid" && exit 1;;
esac

echo "Deleting all local tags"
git tag -d $(git tag) 
if [ $? -ne 0 ]; then
    echo "❌ Error deleting local tags"
    exit 1
fi

echo "Fetching tags from remote repository"
git fetch --tags
if [ $? -ne 0 ]; then
    echo "❌ Error fetching tags from remote repository"
    exit 1
fi

echo "✅ Done"
