# TTB Label Verifier

Checks alcohol label images against their application data and TTB labeling rules.

## Status

In development (October 2026). Only a placeholder page exists so far. This README grows as features land.

## Run locally

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## Run the checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Tools used to build this project

- [Claude Code](https://claude.com/claude-code) (Anthropic), an AI coding assistant, used under Christopher Parker's direction for planning, research, code, and tests.
