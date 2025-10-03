include ./make_scripts/mkdocs-documentation/mkdocs-documentation-makefile.mk
include .make_scripts/project-infrastructure/project-infrastructure-makefile
# This includes make: sync-infrastructure-assets, github_autodelete_merged_branches, github_set_branch_protections and github_set_default_branch
include ./make_scripts/release-management/release-management-makefile

typeCheck:
	poetry run mypy ./neops_remote_lab
	poetry run pylint ./neops_remote_lab
