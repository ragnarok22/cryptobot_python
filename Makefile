.PHONY: clean clean-build clean-pyc clean-test coverage dist docs help install lint lint/flake8 format
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python3 -c "$$BROWSER_PYSCRIPT"

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint/flake8: ## check style with flake8
	poetry run flake8 cryptobot tests --count --show-source --max-complexity=10 --max-line-length=127 --exclude=.venv --statistics

lint: lint/flake8 ## check style

format: ## format code with black and isort
	poetry run isort cryptobot tests
	poetry run black cryptobot tests

test: ## run tests quickly with the default Python
	poetry run coverage run -m pytest
	poetry run coverage report
	poetry run coverage xml
test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	poetry run coverage run -m pytest
	poetry run coverage report -m
	poetry run coverage html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/cryptobot.rst
	rm -f docs/modules.rst
	poetry run sphinx-apidoc -o docs/ cryptobot
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

docs-translations: ## update translation catalogs for all languages
	$(MAKE) -C docs gettext
	$(MAKE) -C docs update-po LANG=es

docs-es: ## build Spanish documentation
	$(MAKE) -C docs html-lang LANG=es
	$(BROWSER) docs/_build/html/es/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	poetry publish

dist: clean ## builds source and wheel package
	python3 -m pip install --upgrade pip setuptools wheel
	poetry build

install: clean ## install the package to the active Python's site-packages
	python3 setup.py install
