#!/bin/sh

DEPENDENCY_MISSING=0

which poetry  > /dev/null      || (echo "poetry is not installed on your system  - please install" && DEPENDENCY_MISSING=1)
which gh  > /dev/null          || (echo "gh is not installed on your system      - please install" && DEPENDENCY_MISSING=1)
which mktemp  > /dev/null      || (echo "mktemp is not installed on your system  - please install" && DEPENDENCY_MISSING=1)

# shellcheck disable=SC2039
if [[ $DEPENDENCY_MISSING -eq 1 ]]
 then
    exit 1
fi

# Here, we know that all dependencies are installed and we are in the correct PWD

mkdir .make_scripts || true
mkdir .make_scripts/mkdocs-documentation || true
tmp_folder=$(mktemp -d)
gh release --repo "${ZEBBRA_DOC_SCRIPTS:-zebbra/mkdocs-documentation}" download -A zip -D "$tmp_folder"
(cd "$tmp_folder" && unzip *.zip)
\cp -r "$tmp_folder"/**/assets/* .make_scripts/mkdocs-documentation/
\cp -r "$tmp_folder"/**/assets/.github .make_scripts/mkdocs-documentation/
rm -rf "$tmp_folder"


MAKEFILE=./Makefile
MAKEFILE_LINE="include .make_scripts/mkdocs-documentation/mkdocs-documentation-makefile.mk"
if [ ! -f $MAKEFILE ]; then
  touch Makefile;
  printf "%s\n" 1 i "$MAKEFILE_LINE" . w | ed -s Makefile
  echo "Created Makefile"
elif ! grep -q "$MAKEFILE_LINE" $MAKEFILE; then
    printf "%s\n" 1 i "$MAKEFILE_LINE" . w | ed -s Makefile
    echo "Updated Makefile"
else
  echo "Makefile already up to date"
fi


(
  cd .make_scripts/mkdocs-documentation
  find . -type f -iname "*.sh" -exec chmod +x {} \;
)

poetry install --project .make_scripts/mkdocs-documentation/
poetry run --project .make_scripts/mkdocs-documentation/ python .make_scripts/mkdocs-documentation/setup_documentation.py
