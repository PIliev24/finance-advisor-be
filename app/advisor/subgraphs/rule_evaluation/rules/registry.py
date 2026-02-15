"""Rule registry for the financial rule evaluation engine."""

from collections.abc import Callable
from dataclasses import dataclass

from app.advisor.schemas import RuleCategory, RuleResult


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    name: str
    category: RuleCategory
    description: str
    check_fn: Callable[[dict], RuleResult]


class RuleRegistry:
    """Central registry for all financial analysis rules."""

    def __init__(self) -> None:
        self._rules: dict[str, RuleDefinition] = {}

    def register(
        self,
        rule_id: str,
        name: str,
        category: RuleCategory,
        description: str = "",
    ) -> Callable[[Callable[[dict], RuleResult]], Callable[[dict], RuleResult]]:
        """Decorator to register a rule function."""

        def decorator(
            fn: Callable[[dict], RuleResult],
        ) -> Callable[[dict], RuleResult]:
            self._rules[rule_id] = RuleDefinition(
                rule_id=rule_id,
                name=name,
                category=category,
                description=description,
                check_fn=fn,
            )
            return fn

        return decorator

    def get_rules(self, category: RuleCategory | None = None) -> list[RuleDefinition]:
        """Return all rules, optionally filtered by category."""
        if category is None:
            return list(self._rules.values())
        return [r for r in self._rules.values() if r.category == category]

    def run_all(
        self,
        category: RuleCategory | None,
        context: dict,
    ) -> list[RuleResult]:
        """Execute all matching rules against the provided financial context."""
        results: list[RuleResult] = []
        for rule_def in self.get_rules(category):
            result = rule_def.check_fn(context)
            results.append(result)
        return results


registry = RuleRegistry()
