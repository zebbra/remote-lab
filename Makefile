include .make_scripts/mkdocs-documentation/mkdocs-documentation-makefile.mk
include .make_scripts/release-management/release-management-makefile
# This includes make: tag-major, tag-major-beta, tag-minor, tag-minor-beta, tag-patch, tag-patch-beta, tag-latest-beta, tag-major-minor-ruleset, hard-reset-tags, check-for-release and sync-release-assets.
include .make_scripts/project-infrastructure/project-infrastructure-makefile
# This includes make: sync-infrastructure-assets, github_autodelete_merged_branches, github_set_branch_protections and github_set_default_branch

typeCheck:
	poetry run mypy ./neops_remote_lab
	poetry run pylint ./neops_remote_lab
