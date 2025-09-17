include ./make_scripts/release-management/release-management-makefile

typeCheck:
	poetry run mypy ./neops_remote_lab
	poetry run pylint ./neops_remote_lab