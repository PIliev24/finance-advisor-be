from typing import Literal

from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float = Field(gt=0)


class BudgetUpdate(BaseModel):
    monthly_limit: float | None = Field(default=None, gt=0)


class BudgetResponse(BaseModel):
    id: str
    category: str
    monthly_limit: float
    current_usage: float
    utilization_pct: float
    alert_level: str
    is_active: bool
    created_at: str
    updated_at: str


class BudgetAlert(BaseModel):
    category: str
    monthly_limit: float
    current_usage: float
    utilization_pct: float
    alert_level: Literal["ok", "warning", "exceeded", "critical"]
