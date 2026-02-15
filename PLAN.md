# Personal Finance Advisor App - Implementation Plan

## Context

The project is a fresh FastAPI + LangGraph skeleton (single "Hello World" endpoint). The goal is to build a personal AI-powered finance advisor that tracks income/expenses via event sourcing, accepts multi-modal input (manual, CSV, screenshots, PDFs), provides personalized financial advice considering life events, and includes market data/sentiment services.

**Key decisions:**
- LLM: Both OpenAI + Anthropic via factory pattern
- Database: SQLite (local, personal use) with aiosqlite
- Auth: Simple API key from env var
- Currency: EUR (default), predefined categories + AI auto-suggestion
- API only (no frontend for now), SSE streaming for AI responses

---

## Phase 1: Foundation + MVP

Build the core infrastructure and a working system where transactions can be manually entered and the AI advisor gives personalized advice.

### Step 1.1: Project Scaffolding

Create the full directory structure organized by domain:

```
app/
├── main.py                    # App factory, lifespan, router mounting
├── config.py                  # Settings (pydantic-settings, fail fast)
├── database.py                # aiosqlite connection management + DDL
├── dependencies.py            # Shared DI: get_db, get_event_store, etc.
├── auth.py                    # API key dependency
├── exceptions.py              # AppError -> NotFoundError, ValidationError, etc.
├── exception_handlers.py      # Map domain exceptions -> HTTP responses
├── logging_config.py          # structlog setup
├── event_store/               # Event sourcing core
│   ├── models.py              # Event dataclass, EventType enum
│   ├── schemas.py             # Pydantic request/response
│   ├── repository.py          # Append events, read streams
│   ├── projections.py         # Rebuild read-model projections
│   └── service.py             # EventStoreService facade
├── transactions/              # Transaction domain
│   ├── models.py              # Category enum, TransactionType
│   ├── schemas.py             # Create/Update/Response/Filter
│   ├── router.py              # CRUD + import endpoints
│   ├── service.py             # Business logic via event store
│   └── importers/             # Phase 2: CSV, image, PDF parsers
├── budgets/                   # Budget domain
│   ├── schemas.py, router.py, service.py
├── context/                   # Personal life events
│   ├── schemas.py, router.py, service.py
├── advisor/                   # AI financial advisor (LangGraph)
│   ├── schemas.py             # AdvisorQuery, StreamChunk
│   ├── router.py              # POST /chat (SSE), GET /summary
│   ├── service.py             # Orchestrates graph invocation
│   ├── graph.py               # StateGraph definition
│   ├── nodes/                 # One file per node
│   │   ├── intent_classifier.py
│   │   ├── financial_analyst.py
│   │   ├── advice_generator.py
│   │   └── budget_checker.py
│   ├── tools.py               # LangGraph tools
│   └── prompts.py             # System prompts
├── market/                    # Phase 3: Stock market service
├── sentiment/                 # Phase 3: Social sentiment
├── trades/                    # Phase 3: Trade recommendations
└── llm/                       # Multi-provider LLM factory
    ├── factory.py             # LLMFactory.create(provider, model)
    └── config.py              # LLMProvider enum
```

**Files to modify:**
- `app/main.py` - Rewrite: lifespan, router mounting, exception handlers, CORS, API key middleware
- `pyproject.toml` - Add dependencies

**Files to create:**
- `app/config.py` - `Settings(BaseSettings)` with all env vars, validated at startup
- `app/database.py` - aiosqlite connection management, DDL execution
- `app/dependencies.py` - Annotated DI types for db, services
- `app/auth.py` - API key header dependency
- `app/exceptions.py` - `AppError`, `NotFoundError`, `ValidationError`, `ConflictError`
- `app/exception_handlers.py` - Global exception -> HTTP response mapping
- `app/logging_config.py` - structlog with JSON output
- `.env.example` - Template env file
- All `__init__.py` files

**New dependencies** (add to pyproject.toml):
```
aiosqlite>=0.20.0
pydantic-settings>=2.4.0
sse-starlette>=2.1.0
structlog>=24.4.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
pypdf>=4.0.0
yfinance>=0.2.40
httpx>=0.27.0
```

### Step 1.2: Event Store Core

The heart of the system. All financial mutations stored as immutable events.

**Event store table** (SQLite):
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    aggregate_type TEXT NOT NULL,     -- 'transaction', 'budget', 'context'
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,         -- 'transaction_created', etc.
    event_data TEXT NOT NULL,         -- JSON payload
    metadata TEXT,                    -- JSON: source, idempotency_key
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(aggregate_id, version)
);
```

**Projection tables** (materialized read models, rebuilt from events):
- `transactions_projection` - Current state of all transactions
- `monthly_summary_projection` - Aggregated monthly spending by category
- `budgets_projection` - Current budget definitions
- `life_events_projection` - Personal context

Projections are updated synchronously on event append (fine for single-user SQLite).

**Files to create:**
- `app/event_store/models.py` - Event dataclass, EventType enum
- `app/event_store/schemas.py` - EventCreate, EventResponse
- `app/event_store/repository.py` - `append_event()`, `get_events()`, `get_events_by_aggregate()`
- `app/event_store/projections.py` - ProjectionEngine: event type -> projection handler
- `app/event_store/service.py` - EventStoreService (append + project + idempotency check)

### Step 1.3: Transaction Domain (Manual Input)

**Categories** (predefined set, AI can suggest additions):
- `food`, `transport`, `housing`, `utilities`, `entertainment`, `health`, `education`, `clothing`, `savings`, `investments`, `salary`, `freelance`, `gifts`, `subscriptions`, `other`

**API endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/transactions` | Create transaction (manual) |
| GET | `/api/v1/transactions` | List with filters (date, category, type) |
| GET | `/api/v1/transactions/{id}` | Get single |
| PUT | `/api/v1/transactions/{id}` | Update (creates update event) |
| DELETE | `/api/v1/transactions/{id}` | Soft-delete (creates delete event) |
| GET | `/api/v1/transactions/summary` | Monthly/category summary |

**Files to create:**
- `app/transactions/models.py`, `schemas.py`, `service.py`, `router.py`, `exceptions.py`

### Step 1.4: LLM Factory

Factory pattern supporting OpenAI and Anthropic via langchain's `BaseChatModel`.

**Files to create:**
- `app/llm/factory.py` - `LLMFactory.create(provider, model) -> BaseChatModel`
- `app/llm/config.py` - `LLMProvider` enum

### Step 1.5: AI Financial Advisor (LangGraph)

**State:**
```python
class AdvisorState(TypedDict):
    messages: Annotated[list, add]
    user_query: str
    intent: str
    financial_context: dict
    personal_context: dict
    budget_status: dict
    iteration_count: int
```

**Graph topology:**
```
START -> classify_intent -> [gather_financial_data, check_budgets] -> enrich_personal_context -> generate_advice -> [tool_node | END]
                                                                                                      ^                    |
                                                                                                      └────────────────────┘
```

- `classify_intent` - Determines user intent (spending_analysis, budget_check, advice, general)
- `gather_financial_data` - Queries transaction projections
- `check_budgets` - Fetches budget status, flags near-limit categories
- `enrich_personal_context` - Loads life events for LLM context
- `generate_advice` - Core LLM call with all context, may invoke tools
- `tool_node` - Executes tools (query_transactions, get_monthly_summary, get_budget_status, calculate_savings_rate)

**Tools available to the agent:**
- `query_transactions(start_date, end_date, category, limit)`
- `get_monthly_summary(year_month)`
- `get_budget_status(category)`
- `calculate_savings_rate(months)`
- `get_spending_trend(category, months)`

**Streaming:** SSE via `sse-starlette` with events: `token`, `status`, `done`

**Files to create:**
- `app/advisor/schemas.py`, `router.py`, `service.py`, `graph.py`, `tools.py`, `prompts.py`
- `app/advisor/nodes/intent_classifier.py`, `financial_analyst.py`, `advice_generator.py`, `budget_checker.py`

### Step 1.6: Budget Domain

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/budgets` | Create budget for category |
| GET | `/api/v1/budgets` | List all with current utilization |
| PUT | `/api/v1/budgets/{id}` | Update limit |
| DELETE | `/api/v1/budgets/{id}` | Deactivate |
| GET | `/api/v1/budgets/alerts` | Active alerts |

Alert thresholds: 80% (warning), 100% (exceeded), 120% (critical).

### Step 1.7: Personal Context Domain

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/context/events` | Add life event |
| GET | `/api/v1/context/events` | List all |
| PUT | `/api/v1/context/events/{id}` | Update |
| DELETE | `/api/v1/context/events/{id}` | Remove |
| GET | `/api/v1/context/profile` | Assembled profile |

Life event types: `expecting_baby`, `job_change`, `retirement_planning`, `major_purchase`, `debt_payoff`, `education`, `relocation`, `marriage`, `health_event`, `other`

---

## Phase 2: Full Input Modes

### Step 2.1: Import Infrastructure
- `app/transactions/importers/base.py` - `ImporterBase` ABC: `async def parse(file) -> list[TransactionCreate]`
- Idempotency via hash of (date + amount + description)
- Batch tracking with `import_batch_id`

### Step 2.2: CSV Importer
- `app/transactions/importers/csv_importer.py`
- Auto-detect common bank CSV formats, configurable column mapping
- Endpoint: `POST /api/v1/transactions/import/csv`

### Step 2.3: Image/Screenshot Importer
- `app/transactions/importers/image_importer.py`
- Send image to vision LLM (GPT-4o/Claude) with extraction prompt
- Parse structured response into transactions
- Endpoint: `POST /api/v1/transactions/import/image`

### Step 2.4: PDF Importer
- `app/transactions/importers/pdf_importer.py`
- Use `pypdf` to extract text, then LLM for structured parsing
- Endpoint: `POST /api/v1/transactions/import/pdf`

---

## Phase 3: Market Services

### Step 3.1: Market Data Service
- `app/market/providers/base.py` - `MarketDataProvider` ABC
- `app/market/providers/yahoo_finance.py` - yfinance wrapper
- `app/market/providers/alpha_vantage.py` - httpx async client
- Endpoints: `GET /api/v1/market/quote/{ticker}`, `GET /api/v1/market/analysis/{ticker}`

### Step 3.2: Sentiment Service
- `app/sentiment/service.py` - X/Twitter API via httpx + LLM sentiment classification
- Endpoint: `GET /api/v1/sentiment/{ticker}`

### Step 3.3: Trade Recommendations
- `app/trades/service.py` - Combines market data + sentiment + user context
- Endpoint: `GET /api/v1/trades/recommendations`

### Step 3.4: Integrate into Advisor Graph
- Add `gather_market_data` node to LangGraph
- Add market-related tools
- Update conditional routing

---

## Configuration (.env)

```bash
FA_API_KEY=your-secret-key          # Required
FA_LLM_PROVIDER=openai              # openai | anthropic
FA_LLM_MODEL=gpt-4o
FA_OPENAI_API_KEY=sk-...            # Required if provider=openai
FA_ANTHROPIC_API_KEY=sk-ant-...     # Required if provider=anthropic
FA_DEFAULT_CURRENCY=EUR
FA_BUDGET_ALERT_THRESHOLD=0.8
FA_LOG_LEVEL=INFO
# Phase 3:
# FA_ALPHA_VANTAGE_API_KEY=...
# FA_TWITTER_BEARER_TOKEN=...
```

---

## Verification

After Phase 1 implementation:
1. `uv sync` - Install all dependencies
2. `ruff check app/` - Zero lint warnings
3. Start the server: `uv run uvicorn app.main:app --reload`
4. `GET /api/v1/health` - Verify DB connectivity
5. `POST /api/v1/transactions` - Create a manual transaction (income + expense)
6. `GET /api/v1/transactions/summary` - Verify projection works
7. `POST /api/v1/budgets` - Create a budget
8. `POST /api/v1/context/events` - Add a life event
9. `POST /api/v1/advisor/chat` - Ask "What's my spending like?" and verify SSE stream
10. Verify event store: `GET /api/v1/events` shows all immutable events


● How to Interact with the Advisor

  1. Start the server

  uv run uvicorn app.main:app --reload

  2. Add some financial data first

  # Set your API key header
  API="X-API-Key: dev-secret-key"

  # Create income transactions
  curl -X POST http://localhost:8000/api/v1/transactions \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"type":"income","amount":5000,"category":"salary","date":"2026-02-01","description":"Monthly salary"}'

  # Create expense transactions
  curl -X POST http://localhost:8000/api/v1/transactions \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"type":"expense","amount":1200,"category":"housing","date":"2026-02-01","description":"Rent"}'

  curl -X POST http://localhost:8000/api/v1/transactions \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"type":"expense","amount":400,"category":"food","date":"2026-02-05","description":"Groceries"}'

  # Set a budget
  curl -X POST http://localhost:8000/api/v1/budgets \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"category":"food","monthly_limit":500}'

  # Add a life event
  curl -X POST http://localhost:8000/api/v1/context/events \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"event_type":"expecting_baby","date":"2026-06-01","description":"First child expected","impact":"Need to increase savings"}'

  3. Chat with the advisor

  Sync (full response):
  curl -X POST http://localhost:8000/api/v1/advisor/chat/sync \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"query":"How am I doing financially?"}'

  Streaming (SSE):
  curl -N -X POST http://localhost:8000/api/v1/advisor/chat \
    -H "$API" -H "Content-Type: application/json" \
    -d '{"query":"Where does my money go?"}'

  Other queries to try:
  - "Am I spending too much on food?"
  - "What's my savings rate?"
  - "Should I invest in AAPL?" (triggers market analysis path)
  - "How can I prepare for the baby financially?"

  4. Import transactions from files

  # CSV import
  curl -X POST http://localhost:8000/api/v1/transactions/import/csv \
    -H "$API" -F "file=@bank_statement.csv"

  # Receipt image
  curl -X POST http://localhost:8000/api/v1/transactions/import/image \
    -H "$API" -F "file=@receipt.png"

  5. Market data

  curl http://localhost:8000/api/v1/market/quote/AAPL -H "$API"
  curl http://localhost:8000/api/v1/trades/recommendations?tickers=AAPL,MSFT -H "$API"

  Note: The advisor chat and market/sentiment/trades endpoints require a real LLM API key. Update your .env:
  FA_OPENAI_API_KEY=sk-your-real-key-here