from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.advisor.router import router as advisor_router
from app.budgets.router import router as budgets_router
from app.context.router import router as context_router
from app.database import close_database, init_database
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.market.router import router as market_router
from app.sentiment.router import router as sentiment_router
from app.trades.router import router as trades_router
from app.transactions.router import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_database()
    yield
    await close_database()


app = FastAPI(
    title="Finance Advisor",
    description="Personal AI-powered finance advisor",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(transactions_router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(budgets_router, prefix="/api/v1/budgets", tags=["budgets"])
app.include_router(context_router, prefix="/api/v1/context", tags=["context"])
app.include_router(market_router, prefix="/api/v1/market", tags=["market"])
app.include_router(sentiment_router, prefix="/api/v1/sentiment", tags=["sentiment"])
app.include_router(trades_router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(advisor_router, prefix="/api/v1/advisor", tags=["advisor"])


@app.get("/api/v1/health")
async def health():
    from app.database import check_health

    await check_health()
    return {"status": "healthy"}
