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
	$(PYTHON) -m unittest tests/
