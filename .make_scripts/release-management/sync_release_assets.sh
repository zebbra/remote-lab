#!/bin/sh

DEPENDENCY_MISSING=0

which ed  > /dev/null          || (echo "🚫 ed is not installed on your system      - please install" && DEPENDENCY_MISSING=1)
which grep  > /dev/null        || (echo "🚫 grep is not installed on your system    - please install" && DEPENDENCY_MISSING=1)
which awk  > /dev/null         || (echo "🚫 awk is not installed on your system     - please install" && DEPENDENCY_MISSING=1)
which find  > /dev/null        || (echo "🚫 find is not installed on your system    - please install" && DEPENDENCY_MISSING=1)
which unzip  > /dev/null       || (echo "🚫 unzip is not installed on your system   - please install" && DEPENDENCY_MISSING=1)
which sed  > /dev/null         || (echo "🚫 sed is not installed on your system     - please install" && DEPENDENCY_MISSING=1)
which gh  > /dev/null          || (echo "🚫 gh is not installed on your system      - please install" && DEPENDENCY_MISSING=1)
which printf  > /dev/null      || (echo "🚫 printf is not installed on your system  - please install" && DEPENDENCY_MISSING=1)
which mktemp  > /dev/null      || (echo "🚫 printf is not installed on your system  - please install" && DEPENDENCY_MISSING=1)

if [[ $DEPENDENCY_MISSING -eq 1 ]]
 then
    exit 1
fi

REPOS=$(sed -n '4p' .make_scripts/release-management/check_for_releases.sh  2>/dev/null)

mkdir .make_scripts 2>/dev/null || true
rm -rf .make_scripts/release-management
mkdir .make_scripts/release-management || true
mkdir .github 2>/dev/null || true


tmp_folder=$(mktemp -d)

gh release --repo ${ZEBBRA_MAKE_RELEASE_SCRIPTS:-zebbra/release-management} download -A zip -D $tmp_folder && echo -e "\r✅ Download successful"

(cd $tmp_folder && unzip *.zip && echo -e "\r✅ Unzip complete")
\cp $tmp_folder/**/scripts/* .make_scripts/release-management/
\cp $tmp_folder/**/.github/release.yml .github/release.yml

if [ -z "$REPOS" ]; then
  REPOS=("REPOS=()")
fi

sed -i.bak '4i\
'"$REPOS"'
' .make_scripts/release-management/check_for_releases.sh && rm .make_scripts/release-management/check_for_releases.sh.bak

MAKEFILE=./Makefile

if [ ! -f $MAKEFILE ]; then
  touch Makefile
  printf "%s\n" "0a" "include .make_scripts/release-management/release-management-makefile" "# This includes make: tag-major, tag-major-beta, tag-minor, tag-minor-beta, tag-patch, tag-patch-beta, tag-latest-beta, tag-major-minor-ruleset, hard-reset-tags, check-for-release and sync-release-assets." "." "w" "q" | ed -s Makefile
  echo "✅ Created Makefile"
elif ! grep -q "include .make_scripts/release-management/release-management-makefile" $MAKEFILE; then
  printf "%s\n" "0a" "include .make_scripts/release-management/release-management-makefile" "# This includes make: tag-major, tag-major-beta, tag-minor, tag-minor-beta, tag-patch, tag-patch-beta, tag-latest-beta, tag-major-minor-ruleset, hard-reset-tags, check-for-release and sync-release-assets." "." "w" "q" | ed -s Makefile
  echo "✅ Updated Makefile"
else
  echo "✅ Makefile already up to date"
fi

rm -rf $tmp_folder

cd .make_scripts/release-management

find . -type f -iname "*.sh" -exec chmod +x {} \;
