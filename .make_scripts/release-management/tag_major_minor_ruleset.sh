echo "Adding tag ruleset..."
output=$(gh api --method POST -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /repos/{owner}/{repo}/rulesets --input .make_scripts/release-management/tag_major_minor_ruleset_input.json 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ Added tag ruleset"
else
  echo "🚫 Failed to add tag ruleset. Error output:"
  echo "$output"
fi
