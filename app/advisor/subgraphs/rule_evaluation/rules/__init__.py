from app.advisor.subgraphs.rule_evaluation.rules import (
    money_traps,  # noqa: F401
    smart_habits,  # noqa: F401
)
from app.advisor.subgraphs.rule_evaluation.rules.registry import registry

__all__ = ["registry"]
