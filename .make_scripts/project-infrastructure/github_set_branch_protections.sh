#!/bin/sh

if [[ "$1" == "--force" ]]
    then
        echo "force switch here"
    else 
        read -p "This will set requiredReviews to 1 for [main,develop]. Continue (y/n)? [use --force switch to skip this]: " choice
    case "$choice" in 
    y|Y ) echo "yes";;
    n|N ) echo "no" && exit 1;;
    * ) echo "invalid" && exit 1;;
    esac
fi

repositoryId="$(gh api graphql -F owner='{owner}' -F name='{repo}' -f query='
    query($name: String!, $owner: String!) {
      repository(owner: $owner, name: $name) {
        id
      }
    }
  ' -q .data.repository.id)" >/dev/null

output=$(gh api graphql -f query='
mutation($repositoryId:ID!,$branch:String!,$requiredReviews:Int!) {
  createBranchProtectionRule(input: {
    repositoryId: $repositoryId
    pattern: $branch
    requiresApprovingReviews: true
    requiredApprovingReviewCount: $requiredReviews
  }) { clientMutationId }
}' -f repositoryId="$repositoryId" -f branch="main" -F requiredReviews=1)

if [ $? -eq 0 ]; then
  echo "✅ Successfully set requiredReviews to 1 for [main]."
else
  echo "🚫 Failed to set requiredReviews to 1 for [main]."
  echo $output
fi

output=$(gh api graphql -f query='
mutation($repositoryId:ID!,$branch:String!,$requiredReviews:Int!) {
  createBranchProtectionRule(input: {
    repositoryId: $repositoryId
    pattern: $branch
    requiresApprovingReviews: true
    requiredApprovingReviewCount: $requiredReviews
  }) { clientMutationId }
}' -f repositoryId="$repositoryId" -f branch="develop" -F requiredReviews=1)

if [ $? -eq 0 ]; then
  echo "✅ Successfully set requiredReviews to 1 for [develop]."
else
  echo "🚫 Failed to set requiredReviews to 1 for [develop]."
  echo $output
fi
