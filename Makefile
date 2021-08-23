.PHONY: format format-check pylint typecheck lint test docs
PYTHON := python3

format:
	$(PYTHON) -m black .

format-check:
	$(PYTHON) -m black --check .

pylint:
	$(PYTHON) -m pylint dustmaker tests

typecheck:
	$(PYTHON) -m mypy dustmaker

lint: format-check pylint typecheck

test:
	$(PYTHON) -m unittest discover -v tests/

docs:
	make -C docs html
