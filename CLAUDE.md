# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
uv run uvicorn app.main:app --reload

# Lint & format
uv run ruff check app/
uv run ruff format app/

# Tests
uv run pytest                          # all tests
uv run pytest app/transactions/        # single module
uv run pytest -k test_create           # by name pattern
uv run pytest -v                       # verbose

# Dependencies
uv add <package>                       # runtime
uv add --group dev <package>           # dev only
uv sync                                # install from lockfile
```

## Architecture

**Stack:** FastAPI + LangGraph + aiosqlite (SQLite with WAL mode)

### Layered Design (strict separation)

```
Router (controller) → Service → Repository (SQL)
```

- **Routers** (`app/*/router.py`): HTTP handling, DI injection, no business logic
- **Services** (`app/*/service.py`): Business logic, event store coordination
- **Repositories** (`app/*/repository.py`): Raw SQL via aiosqlite against projection tables
- **Never put SQL operations directly in routers**

### Event Sourcing

All mutations go through the event store — never write directly to projection tables.

```
Service → EventStoreService.append_event(aggregate_type, aggregate_id, event_type, event_data: dict)
       → ProjectionEngine auto-projects to denormalized tables
```

- `event_data` is a plain `dict`; `append_event()` calls `json.dumps()` internally
- Idempotency key support via `metadata` field
- Tables: `events` (append-only log), `*_projection` (read-optimized views)

### Dependency Injection

All DI is in `app/dependencies.py` using `Annotated[T, Depends()]` type aliases:

```python
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
```

API key auth: `APIKey = Annotated[str, Depends(verify_api_key)]`

### LangGraph Orchestrator (Hierarchical Sub-graphs)

```
classify_intent
├── market path:    run_market_analysis → [END | run_advice_generation]
└── financial path: gather_financial_data → run_rule_evaluation → enrich_personal_context → run_advice_generation → END
```

- **5 sub-graphs** in `app/advisor/subgraphs/`: financial_analysis, budget_analysis, rule_evaluation, advice_generation, market_analysis
- **Only `advice_generation` has LLM calls**; all other sub-graphs are deterministic
- Rule evaluation uses parallel fan-out with `Annotated[list, add]` reducer
- Tool-calling loop in advice_generation is bounded to 5 iterations
- `gather_financial_data` runs financial + budget analysis in parallel via `asyncio.gather`

### Configuration

`pydantic-settings` in `app/config.py` — all env vars prefixed with `FA_` (e.g., `FA_API_KEY`, `FA_LLM_PROVIDER`). Loaded from `.env` file. See `.env.example` for all options.

### LLM Integration

`LLMFactory.create()` in `app/llm/factory.py` — returns OpenAI or Anthropic chat model based on `FA_LLM_PROVIDER` setting.

## Code Style

- **Ruff** with line-length=100, target py312
- Rules: E, F, W, I (isort), N, UP, B, A, SIM, TCH
- Structured logging via `structlog` (JSON output)
- Async throughout — all DB operations, service methods, and graph nodes are `async`
- Custom exceptions in `app/exceptions.py`: `NotFoundError`, `ValidationError`, `ConflictError`
