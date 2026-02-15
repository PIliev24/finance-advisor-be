from pydantic import BaseModel, Field

from app.transactions.models import Category, TransactionType


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0)
    category: Category
    description: str | None = None
    date: str
    currency: str = "EUR"


class TransactionUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    category: Category | None = None
    description: str | None = None
    date: str | None = None


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    currency: str
    category: str
    description: str | None
    date: str
    is_deleted: bool
    created_at: str
    updated_at: str


class TransactionFilter(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    category: Category | None = None
    type: TransactionType | None = None
    limit: int = 50
    offset: int = 0


class MonthlySummary(BaseModel):
    year_month: str
    category: str
    total_income: float
    total_expenses: float
    transaction_count: int
