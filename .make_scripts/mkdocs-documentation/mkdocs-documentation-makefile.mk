.PHONY: doc-update-assets doc-create-mkdocs doc-serve doc-build

MKDOCS_ENV= .make_scripts/mkdocs-documentation
PROJECT_NAME := $(notdir $(CURDIR))


doc-update-assets:
	gh release download --repo zebbra/mkdocs-documentation --pattern setup_documentation.sh --output - | /bin/sh

doc-create-mkdocs:
	poetry run --project $(MKDOCS_ENV)/ python $(MKDOCS_ENV)/setup_documentation.py
	$(MAKE) doc-create-mkdocs-build-workflow

doc-serve:
	poetry install --project $(MKDOCS_ENV)/
	poetry run --project $(MKDOCS_ENV)/ python $(MKDOCS_ENV)/setup_documentation.py
	poetry run --project $(MKDOCS_ENV)/ mkdocs serve

doc-build:
	poetry run --project $(MKDOCS_ENV)/ python $(MKDOCS_ENV)/setup_documentation.py
	poetry run --project $(MKDOCS_ENV)/ mkdocs build
	poetry run --project $(MKDOCS_ENV)/ python $(MKDOCS_ENV)/clean_sites_directory.py

doc-build-docker:
	docker build --file $(MKDOCS_ENV)/Dockerfile --build-context git=.git -t $(PROJECT_NAME)-docs . 

doc-run-docker:
	docker run --rm -p 8000:8000 $(PROJECT_NAME)-docs:latest

doc-site-clean:
	poetry run --project $(MKDOCS_ENV)/ python $(MKDOCS_ENV)/clean_sites_directory.py

doc-create-mkdocs-build-workflow:
	touch .github
	touch .github/workflows
	cp .make_scripts/mkdocs-documentation/.github/workflows/build-documentation.yml .github/workflows