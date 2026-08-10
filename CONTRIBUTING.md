# Contributing

## Environment

PortGuard-AIS requires Python 3.13 or newer.

```bash
uv sync --all-extras
uv run pre-commit install
```

## Before opening a pull request

```bash
make quality
make audit
make build
```

New behavioural changes require tests. Public APIs require docstrings and a documentation update.
Do not introduce route generation, fairway design or autonomous manoeuvre prescription without a
separate project-level scope decision.
