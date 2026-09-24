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
\cp $tmp_download_folder/**/assets/labels.tsv .make_scripts/project-infrastructure/

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

# A public repository cannot use an action from the private zebbra/actions repository
if [ "$(gh repo view --json visibility --jq .visibility)" = "PUBLIC" ]; then
  enforce_pr_label_workflow=enforce-pr-label-public.yml
else
  enforce_pr_label_workflow=enforce-pr-label.yml
fi
mkdir -p .github/workflows
\cp $tmp_download_folder/**/assets/$enforce_pr_label_workflow .github/workflows/enforce-pr-label.yml
echo "✅ Updated .github/workflows/enforce-pr-label.yml ($enforce_pr_label_workflow)"

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



# Labels are matched exactly: `gh label list` without --limit returns only 30, and a
# plain grep would match "change" inside "pr-breaking-change".
label_exists() {
  gh label list --limit 1000 --json name --jq '.[].name' | grep -qxF "$1"
}

check_issues_for_label() {
  local label="$1"
  issues_with_label=$(gh issue list --label "$label" --json number,title --jq '.[] | "\t\(.number) - \(.title)"')

  if [ -n "$issues_with_label" ]; then
    echo -e "🚫 Label '$label' is being used by the following issues:\n$issues_with_label"
    echo "Please remove the label from these issues before attempting to delete it."
    exit 1
  fi
}

delete_label_if_present() {
  if label_exists "$1"; then
    check_issues_for_label "$1"
    gh label delete "$1" --yes
  fi
}

ensure_label() {
  if label_exists "$1"; then
    gh label edit "$1" --color "$2" --description "$3"
  else
    gh label create "$1" --color "$2" --description "$3"
  fi
}

# Labels from prior tool versions, and GitHub's defaults (replaced by issue types)
for label in untriaged change other bug documentation duplicate enhancement "good first issue" \
             "help wanted" invalid question wontfix; do
  delete_label_if_present "$label"
done

# The label set lives in labels.tsv: name, colour, description, tab-separated
while IFS="$(printf '\t')" read -r name color description; do
  case "$name" in ''|'#'*) continue ;; esac
  ensure_label "$name" "$color" "$description"
done < labels.tsv
