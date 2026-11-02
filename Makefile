PYTHON ?= python
RUFF ?= ruff

.PHONY: test lint format format-check run

test:
	$(PYTHON) -m pytest

lint:
	$(RUFF) check src tests

format:
	$(RUFF) format src tests

format-check:
	$(RUFF) format --check src tests

run:
	$(PYTHON) -m uvicorn neuralnotes.api:app --reload
