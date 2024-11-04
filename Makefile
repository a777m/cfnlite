# CFNLite makefile

PYTHON := python3.11
current_dir := $(shell pwd)

check: check-coding-standards check-tests

check-coding-standards: check-pylint check-isort check-pycodestyle

check-pylint:
	$(PYTHON) -m pylint cfnlite

check-pycodestyle:
	$(PYTHON) -m pycodestyle cfnlite

check-isort:
	$(PYTHON) -m isort cfnlite --check-only --diff --skip venv

check-tests:
	$(PYTHON) -m pytest tests/ -v

.PHONY: check check-coding-standards check-pylint check-isort check-tests
