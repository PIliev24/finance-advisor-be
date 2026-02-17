from typing import Annotated

import aiosqlite
from fastapi import Depends

from app.advisor.service import AdvisorService
from app.auth import verify_token
from app.budgets.repository import BudgetRepository
from app.budgets.service import BudgetService
from app.context.repository import ContextRepository
from app.context.service import ContextService
from app.database import get_db
from app.event_store.service import EventStoreService
from app.market.providers.yahoo_finance import YahooFinanceProvider
from app.market.service import MarketService
from app.sentiment.service import SentimentService
from app.trades.service import TradeService
from app.transactions.importers.service import ImportService
from app.transactions.repository import TransactionRepository
from app.transactions.service import TransactionService

DBConn = Annotated[aiosqlite.Connection, Depends(get_db)]
APIKey = Annotated[dict, Depends(verify_token)]


def get_event_store() -> EventStoreService:
    return EventStoreService(get_db())


def get_transaction_repo() -> TransactionRepository:
    return TransactionRepository(get_db())


def get_transaction_service() -> TransactionService:
    return TransactionService(get_event_store(), get_transaction_repo())


def get_budget_repo() -> BudgetRepository:
    return BudgetRepository(get_db())


def get_budget_service() -> BudgetService:
    return BudgetService(get_event_store(), get_budget_repo())


def get_context_repo() -> ContextRepository:
    return ContextRepository(get_db())


def get_context_service() -> ContextService:
    return ContextService(get_event_store(), get_context_repo())


def get_import_service() -> ImportService:
    from app.llm.factory import LLMFactory

    return ImportService(get_transaction_service(), LLMFactory.create())


EventStoreDep = Annotated[EventStoreService, Depends(get_event_store)]
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
TransactionRepoDep = Annotated[TransactionRepository, Depends(get_transaction_repo)]
BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]
ContextServiceDep = Annotated[ContextService, Depends(get_context_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


def get_market_service() -> MarketService:
    return MarketService(YahooFinanceProvider())


def get_sentiment_service() -> SentimentService:
    from app.llm.factory import LLMFactory

    return SentimentService(LLMFactory.create())


def get_trade_service() -> TradeService:
    from app.llm.factory import LLMFactory

    return TradeService(get_market_service(), get_sentiment_service(), LLMFactory.create())


MarketServiceDep = Annotated[MarketService, Depends(get_market_service)]
SentimentServiceDep = Annotated[SentimentService, Depends(get_sentiment_service)]
TradeServiceDep = Annotated[TradeService, Depends(get_trade_service)]


def get_advisor_service() -> AdvisorService:
    return AdvisorService()


AdvisorServiceDep = Annotated[AdvisorService, Depends(get_advisor_service)]
