.PHONY: install format format-check lint typecheck test audit docs build quality clean

install:
	uv sync --all-extras

format:
	uv run ruff format .
	uv run ruff check --fix .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

test:
	uv run pytest

audit:
	uv run pip-audit

docs:
	uv run mkdocs build --strict

build:
	uv run python -m build

quality: lint typecheck test docs

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache dist site htmlcov
