PYTHON := python3

format:
	$(PYTHON) -m black .

lint:
	$(PYTHON) -m pylint dustmaker
