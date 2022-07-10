.PHONY: format format-check pylint typecheck lint test docs build pypy-test pypy-live
PYTHON := python3

all: format lint test docs

format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort --profile=black .

format-check:
	$(PYTHON) -m black --check .
	$(PYTHON) -m isort --profile=black --check .

pylint:
	$(PYTHON) -m pylint dustmaker tests

typecheck:
	$(PYTHON) -m mypy dustmaker

lint: format-check pylint typecheck

test:
	$(PYTHON) -m unittest discover -v tests/

docs:
	make -C docs html

build:
	$(PYTHON) -m build

clean:
	rm -rf build dist *.egg-info

pypi-test: build
	TWINE_USERNAME=__token__ TWINE_PASSWORD="$(shell gpg -d test.pypi-token.gpg)" \
    $(PYTHON) -m twine upload --repository testpypi dist/*

pypi-live: build
	TWINE_USERNAME=__token__ TWINE_PASSWORD="$(shell gpg -d live.pypi-token.gpg)" \
    $(PYTHON) -m twine upload dist/*
