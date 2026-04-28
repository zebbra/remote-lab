include .make_scripts/mkdocs-documentation/mkdocs-documentation-makefile.mk
include .make_scripts/release-management/release-management-makefile
# This includes make: tag-major, tag-major-beta, tag-minor, tag-minor-beta, tag-patch, tag-patch-beta, tag-latest-beta, tag-major-minor-ruleset, hard-reset-tags, check-for-release and sync-release-assets.
include .make_scripts/project-infrastructure/project-infrastructure-makefile
# This includes make: sync-infrastructure-assets, github_autodelete_merged_branches, github_set_branch_protections and github_set_default_branch

lint:
	uv run ruff format --check neops_remote_lab tests
	uv run ruff check neops_remote_lab tests

format:
	uv run ruff format neops_remote_lab tests
	uv run ruff check --fix neops_remote_lab tests

typeCheck:
	uv run pyrefly check

test:
	uv run pytest

audit:
	# Audits the *runtime* dependency closure, not the dev environment.
	# Rationale: pip-audit pulls `pip-api` -> `pip`, and the latest pip
	# carries CVE-2026-3219 with no fixed version available. The service
	# never invokes pip on user input, so scanning the audit toolchain
	# itself produces noise without security signal. Exporting the
	# `--no-dev` requirements first scopes the scan to what actually ships.
	# Use `make audit-dev` to scan the dev environment as well.
	uv export --no-dev --no-emit-project --format requirements-txt -o /tmp/neops-remote-lab-prod-reqs.txt
	# `--disable-pip --no-deps --skip-editable` keeps pip-audit from
	# trying to spin up an internal venv to resolve the requirements
	# file. Runners without `python3.12-venv` (e.g. our hetzner image)
	# fail without these flags. The exported requirements already pin
	# every package, so resolution is unnecessary.
	uv run pip-audit --disable-pip --no-deps --skip-editable \
		-r /tmp/neops-remote-lab-prod-reqs.txt \
		--strict --progress-spinner=off --vulnerability-service osv

audit-dev:
	# Full-environment scan including dev tooling. Carries the pip CVE
	# above; document any new ignore here with a justification.
	uv run pip-audit --strict --progress-spinner=off --vulnerability-service osv \
		--ignore-vuln CVE-2026-3219

check: lint typeCheck audit test
