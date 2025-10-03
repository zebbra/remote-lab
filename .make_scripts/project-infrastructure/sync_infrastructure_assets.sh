#!/bin/sh

DEPENDENCY_MISSING=0

which ed > /dev/null        || { echo "🚫 ed is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which grep > /dev/null      || { echo "🚫 grep is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which awk > /dev/null       || { echo "🚫 awk is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which find > /dev/null      || { echo "🚫 find is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which unzip > /dev/null     || { echo "🚫 unzip is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which gh > /dev/null        || { echo "🚫 gh is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which printf > /dev/null    || { echo "🚫 printf is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which mktemp > /dev/null    || { echo "🚫 mktemp is not installed on your system - please install"; DEPENDENCY_MISSING=1; }
which yq > /dev/null        || { echo "🚫 yq is not installed on your system - please install"; DEPENDENCY_MISSING=1; }

if [[ $DEPENDENCY_MISSING -eq 1 ]]; then
    exit 1
fi

mkdir .make_scripts 2>/dev/null || true
mkdir .make_scripts/project-infrastructure 2>/dev/null || true

tmp_download_folder=$(mktemp -d)
gh release --repo ${ZEBBRA_PROJECT_INFRASTRUCTURE_SCRIPTS:-zebbra/project-infrastructure} download -A zip -D $tmp_download_folder && echo -e "\r✅ Download successful"

(cd $tmp_download_folder && unzip *.zip && echo -e "\r✅ Unzip complete")
\cp $tmp_download_folder/**/scripts/* .make_scripts/project-infrastructure/

mkdir .github 2>/dev/null || true

temp_old_issue_templates=$(mktemp -d)

if [ -d .github/ISSUE_TEMPLATE ]; then
  cp -r .github/ISSUE_TEMPLATE/* $temp_old_issue_templates/
fi

rm -rf .github/ISSUE_TEMPLATE
mkdir -p .github/ISSUE_TEMPLATE

cp -r $tmp_download_folder/**/.github/ISSUE_TEMPLATE/* .github/ISSUE_TEMPLATE/

for file in .github/ISSUE_TEMPLATE/*; do
  if [ -f $temp_old_issue_templates/$(basename $file) ]; then
    assignees=$(yq '.assignees' $temp_old_issue_templates/$(basename $file))
    projects=$(yq '.projects' $temp_old_issue_templates/$(basename $file))
    if [ "$assignees" != "[]" ]; then
      yq -y --in-place ".assignees = $assignees" $file
    fi
    if [ "$projects" != "[]" ]; then
      yq -y --in-place ".projects = $projects" $file
    fi
  fi
done

if [ -f .github/CODEOWNERS ]; then
  mv .github/CODEOWNERS CODEOWNERS
else
  \cp $tmp_download_folder/**/.github/CODEOWNERS CODEOWNERS
  echo "✅ Created CODEOWNERS file"
fi

if [ -d .github/workflows ]; then
  echo "✅ Workflows folder already exists"
  rm -f .github/workflows/enforce-pr-label.yml
  \cp $tmp_download_folder/**/assets/enforce-pr-label.yml .github/workflows/
  echo "✅ Updated Workflows folder"
else
  mkdir .github/workflows
  \cp $tmp_download_folder/**/assets/enforce-pr-label.yml .github/workflows/
  echo "✅ Created Workflows folder"
fi

MAKEFILE=./Makefile || true

if [ ! -f $MAKEFILE ]; then
  touch Makefile;
  printf "%s\n" "0a" "include .make_scripts/project-infrastructure/project-infrastructure-makefile" "# This includes make: sync-infrastructure-assets, github_autodelete_merged_branches, github_set_branch_protections and github_set_default_branch" . w | ed -s Makefile
  echo "✅ Created Makefile"
elif ! grep -q "include .make_scripts/project-infrastructure/project-infrastructure-makefile" $MAKEFILE; then
    printf "%s\n" "0a" "include .make_scripts/project-infrastructure/project-infrastructure-makefile" "# This includes make: sync-infrastructure-assets, github_autodelete_merged_branches, github_set_branch_protections and github_set_default_branch" . w | ed -s Makefile
    echo "✅ Updated Makefile"
else
  echo "✅ Makefile already up to date"
fi

PRTEMPLATE=./pull_request_template.md

if [ ! -f $PRTEMPLATE ]; then
  mv $tmp_download_folder/**/assets/pull_request_template.md .
  echo "✅ Created pull_request_template.md"
else
  mv $tmp_download_folder/**/assets/pull_request_template.md .
  echo "✅ pull_request_template.md already updated"
fi

rm -rf $tmp_download_folder
rm -rf $temp_old_issue_templates

cd .make_scripts/project-infrastructure

find . -type f -iname "*.sh" -exec chmod +x {} \;


# Function to check if any issue has the specified label
check_issues_for_label() {
  local label="$1"
  issues_with_label=$(gh issue list --label "$label" --json number,title --jq '.[] | "\t\(.number) - \(.title)"')

  if [ -n "$issues_with_label" ]; then
    echo -e "🚫 Label '$label' is being used by the following issues:\n$issues_with_label"
    echo "Please remove the label from these issues before attempting to delete it."
    exit 1
  fi
}

# Add triaged labels for issues
if ! gh label list | grep -q "triaged"; then
  gh label create triaged --description "Issue is being worked on" --color 228B22
else
  gh label edit triaged --description "Issue is being worked on" --color 228B22 
fi

# Remove labels from prior tool versions
if gh label list | grep -q "untriaged"; then
  check_issues_for_label "untriaged"
  gh label delete "untriaged" --yes
fi

if gh label list | grep -q "change"; then
  check_issues_for_label "change"
  gh label delete "change" --yes || true
fi

if gh label list | grep -q "other"; then
  check_issues_for_label "other"
  gh label delete "other" --yes
fi

# Delete standard GH labels
if gh label list | grep -q "bug"; then
  check_issues_for_label "bug"
  gh label delete "bug" --yes
fi

if gh label list | grep -q "documentation"; then
  check_issues_for_label "documentation"
  gh label delete "documentation" --yes
fi

if gh label list | grep -q "duplicate"; then
  check_issues_for_label "duplicate"
  gh label delete "duplicate" --yes
fi

if gh label list | grep -q "enhancement"; then
  check_issues_for_label "enhancement"
  gh label delete "enhancement" --yes
fi

if gh label list | grep -q "good first issue"; then
  check_issues_for_label "good first issue"
  gh label delete "good first issue" --yes
fi

if gh label list | grep -q "help wanted"; then
  check_issues_for_label "help wanted"
  gh label delete "help wanted" --yes
fi

if gh label list | grep -q "invalid"; then
  check_issues_for_label "invalid"
  gh label delete "invalid" --yes
fi

if gh label list | grep -q "question"; then
  check_issues_for_label "question"
  gh label delete "question" --yes
fi

if gh label list | grep -q "wontfix"; then
  check_issues_for_label "wontfix"
  gh label delete "wontfix" --yes
fi

# Add labels for PR's

if ! gh label list | grep -q "pr-breaking-change"; then
  gh label create pr-breaking-change --description "PR introduces breaking change" --color ffa500
else
  gh label edit pr-breaking-change --description "PR introduces breaking change" --color ffa500 
fi

if ! gh label list | grep -q "pr-new-feature"; then
  gh label create pr-new-feature --description "PR introduces new feature/s" --color ffa500
else
  gh label edit pr-new-feature --description "PR introduces new feature/s" --color ffa500 
fi

if ! gh label list | grep -q "pr-bugfix"; then
  gh label create pr-bugfix --description "PR introduces a bugfix" --color ffa500
else
  gh label edit pr-bugfix --description "PR introduces a bugfix" --color ffa500 
fi

if ! gh label list | grep -q "pr-security"; then
  gh label create pr-security --description "PR introduces a security improvement" --color ffa500
else
  gh label edit pr-security --description "PR introduces a security improvement" --color ffa500 
fi

if ! gh label list | grep -q "pr-other"; then
  gh label create pr-other --description "PR does something not covered by other labels" --color ffa500
else
  gh label edit pr-other --description "PR does something not covered by other labels" --color ffa500 
fi
