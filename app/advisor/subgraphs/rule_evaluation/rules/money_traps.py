"""Money trap rules — patterns that silently erode financial health."""

from collections import Counter

from app.advisor.schemas import RuleCategory, RuleResult, RuleSeverity

from .registry import registry

_CAT = RuleCategory.money_trap


def _insufficient_data(rule_id: str, name: str, reason: str) -> RuleResult:
    """Helper for rules that cannot evaluate due to missing data."""
    return RuleResult(
        rule_id=rule_id,
        name=name,
        category=_CAT,
        triggered=False,
        severity=RuleSeverity.info,
        message=f"Insufficient data to evaluate: {reason}",
    )


# ---------------------------------------------------------------------------
# MT-01: Lifestyle Creep
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-01",
    name="Lifestyle Creep",
    category=_CAT,
    description="Spending growth outpaces income growth over 3+ months",
)
def lifestyle_creep(ctx: dict) -> RuleResult:
    trends = ctx.get("spending_trends", [])
    if len(trends) < 3:
        return _insufficient_data("MT-01", "Lifestyle Creep", "need 3+ months of trends")

    expense_vals = [t.get("total_expenses", 0) for t in trends]
    income_vals = [t.get("total_income", 0) for t in trends]

    if expense_vals[0] == 0 or income_vals[0] == 0:
        return _insufficient_data("MT-01", "Lifestyle Creep", "zero baseline values")

    expense_growth = (expense_vals[-1] - expense_vals[0]) / expense_vals[0] * 100
    income_growth = (income_vals[-1] - income_vals[0]) / income_vals[0] * 100

    triggered = expense_growth > income_growth + 5
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Spending grew {expense_growth:.1f}% vs income {income_growth:.1f}% — "
        "expenses are outpacing earnings."
        if triggered
        else "Spending growth is within healthy bounds relative to income growth."
    )
    return RuleResult(
        rule_id="MT-01",
        name="Lifestyle Creep",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "expense_growth_pct": round(expense_growth, 2),
            "income_growth_pct": round(income_growth, 2),
        },
    )


# ---------------------------------------------------------------------------
# MT-02: Car Payment Treadmill
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-02",
    name="Car Payment Treadmill",
    category=_CAT,
    description="Recurring large transport payments suggesting perpetual car debt",
)
def car_payment_treadmill(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    transport_txns = [
        t for t in transactions if t.get("category") == "transport" and t.get("type") == "expense"
    ]
    if len(transport_txns) < 3:
        return _insufficient_data("MT-02", "Car Payment Treadmill", "need 3+ transport expenses")

    amounts = [t.get("amount", 0) for t in transport_txns]
    if not amounts:
        return _insufficient_data("MT-02", "Car Payment Treadmill", "no transport amounts")

    rounded = [round(a, -1) for a in amounts]
    most_common_amount, count = Counter(rounded).most_common(1)[0]

    triggered = count >= 3 and most_common_amount > 100
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Detected {count} transport payments near {most_common_amount:.0f} — "
        "possible perpetual car debt cycle."
        if triggered
        else "No recurring large transport payment pattern detected."
    )
    return RuleResult(
        rule_id="MT-02",
        name="Car Payment Treadmill",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"recurring_amount": most_common_amount, "occurrences": count},
    )


# ---------------------------------------------------------------------------
# MT-03: Minimum Payment Illusion
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-03",
    name="Minimum Payment Illusion",
    category=_CAT,
    description="Same-amount recurring debt payments suggest minimum-only payments",
)
def minimum_payment_illusion(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    debt_txns = [
        t
        for t in transactions
        if t.get("category") == "debt_payment" and t.get("type") == "expense"
    ]
    if len(debt_txns) < 2:
        return _insufficient_data(
            "MT-03",
            "Minimum Payment Illusion",
            "need 2+ debt payments",
        )

    rounded = [round(t.get("amount", 0), 0) for t in debt_txns]
    most_common_amount, count = Counter(rounded).most_common(1)[0]

    triggered = count >= 2 and count == len(debt_txns)
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"All {count} debt payments are ~{most_common_amount:.0f} — "
        "likely minimum payments only, which extends payoff time and increases interest."
        if triggered
        else "Debt payment amounts vary, suggesting more than minimum payments."
    )
    return RuleResult(
        rule_id="MT-03",
        name="Minimum Payment Illusion",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"recurring_amount": most_common_amount, "occurrences": count},
    )


# ---------------------------------------------------------------------------
# MT-04: House Poor
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-04",
    name="House Poor",
    category=_CAT,
    description="Housing costs exceeding 30% of income",
)
def house_poor(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("MT-04", "House Poor", "no income data")

    housing = spending.get("housing", 0)
    ratio = housing / total_income

    triggered = ratio > 0.30
    severity = (
        RuleSeverity.critical
        if ratio > 0.40
        else (RuleSeverity.warning if triggered else RuleSeverity.info)
    )
    msg = (
        f"Housing costs are {ratio:.0%} of income — exceeds the 30% guideline."
        if triggered
        else f"Housing costs are {ratio:.0%} of income — within healthy range."
    )
    return RuleResult(
        rule_id="MT-04",
        name="House Poor",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"housing_cost": housing, "income": total_income, "ratio": round(ratio, 4)},
    )


# ---------------------------------------------------------------------------
# MT-05: Whole Life Insurance Drain
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-05",
    name="Whole Life Insurance Drain",
    category=_CAT,
    description="Insurance spending exceeding 5% of income",
)
def insurance_drain(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("MT-05", "Whole Life Insurance Drain", "no income data")

    insurance = spending.get("insurance", 0)
    ratio = insurance / total_income

    triggered = ratio > 0.05
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Insurance is {ratio:.1%} of income — review whether coverage is cost-effective."
        if triggered
        else f"Insurance spending is {ratio:.1%} of income — within normal range."
    )
    return RuleResult(
        rule_id="MT-05",
        name="Whole Life Insurance Drain",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"insurance_cost": insurance, "income": total_income, "ratio": round(ratio, 4)},
    )


# ---------------------------------------------------------------------------
# MT-06: Paying for Convenience
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-06",
    name="Paying for Convenience",
    category=_CAT,
    description="High-frequency small food/transport transactions suggesting convenience premium",
)
def paying_for_convenience(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    convenience_cats = {"food", "transport"}
    small_txns = [
        t
        for t in transactions
        if t.get("category") in convenience_cats
        and t.get("type") == "expense"
        and 0 < t.get("amount", 0) <= 20
    ]

    if not transactions:
        return _insufficient_data("MT-06", "Paying for Convenience", "no transactions")

    total_small = sum(t.get("amount", 0) for t in small_txns)
    count = len(small_txns)

    triggered = count > 30
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"{count} small convenience purchases totalling {total_small:.2f} — "
        "consider batching or meal-prepping to reduce costs."
        if triggered
        else f"{count} small convenience purchases — within reasonable range."
    )
    return RuleResult(
        rule_id="MT-06",
        name="Paying for Convenience",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"small_transaction_count": count, "total_amount": round(total_small, 2)},
    )


# ---------------------------------------------------------------------------
# MT-07: Keep Up Appearances
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-07",
    name="Keep Up Appearances",
    category=_CAT,
    description="Clothing + entertainment exceeding 25% of income",
)
def keep_up_appearances(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("MT-07", "Keep Up Appearances", "no income data")

    appearance = spending.get("clothing", 0) + spending.get("entertainment", 0)
    ratio = appearance / total_income

    triggered = ratio > 0.25
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Clothing + entertainment is {ratio:.0%} of income — "
        "consider whether lifestyle spending aligns with goals."
        if triggered
        else f"Clothing + entertainment is {ratio:.0%} of income — within bounds."
    )
    return RuleResult(
        rule_id="MT-07",
        name="Keep Up Appearances",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "clothing": spending.get("clothing", 0),
            "entertainment": spending.get("entertainment", 0),
            "combined_ratio": round(ratio, 4),
        },
    )


# ---------------------------------------------------------------------------
# MT-08: Emergency Free Delusion
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-08",
    name="Emergency Free Delusion",
    category=_CAT,
    description="Savings below 3 months of expenses",
)
def emergency_free(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_expenses = ctx.get("total_expenses", 0)
    savings_amount = spending.get("savings", 0)
    period_months = max(len(ctx.get("spending_trends", [])), 1)
    monthly_expenses = total_expenses / period_months if period_months > 0 else 0

    if monthly_expenses <= 0:
        return _insufficient_data("MT-08", "Emergency Free Delusion", "no expense data")

    months_covered = savings_amount / monthly_expenses if monthly_expenses > 0 else 0

    triggered = months_covered < 3
    severity = (
        RuleSeverity.critical
        if months_covered < 1
        else (RuleSeverity.warning if triggered else RuleSeverity.info)
    )
    msg = (
        f"Savings cover only ~{months_covered:.1f} months of expenses — "
        "aim for at least 3-6 months emergency fund."
        if triggered
        else f"Savings cover ~{months_covered:.1f} months of expenses — good buffer."
    )
    return RuleResult(
        rule_id="MT-08",
        name="Emergency Free Delusion",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "savings": savings_amount,
            "monthly_expenses": round(monthly_expenses, 2),
            "months_covered": round(months_covered, 2),
        },
    )


# ---------------------------------------------------------------------------
# MT-09: Retail Therapy Addiction
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-09",
    name="Retail Therapy Addiction",
    category=_CAT,
    description="High-frequency small discretionary transactions (>10/month)",
)
def retail_therapy(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    retail_cats = {"clothing", "entertainment", "gifts"}
    retail_txns = [
        t for t in transactions if t.get("category") in retail_cats and t.get("type") == "expense"
    ]

    if not transactions:
        return _insufficient_data("MT-09", "Retail Therapy Addiction", "no transactions")

    months_set: set[str] = set()
    for t in transactions:
        date_str = t.get("date", "")
        if len(date_str) >= 7:
            months_set.add(date_str[:7])
    num_months = max(len(months_set), 1)

    per_month = len(retail_txns) / num_months
    total_amount = sum(t.get("amount", 0) for t in retail_txns)

    triggered = per_month > 10
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Averaging {per_month:.1f} discretionary purchases/month "
        f"(totalling {total_amount:.2f}) — possible impulse spending pattern."
        if triggered
        else f"Averaging {per_month:.1f} discretionary purchases/month — within normal range."
    )
    return RuleResult(
        rule_id="MT-09",
        name="Retail Therapy Addiction",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "transactions_per_month": round(per_month, 2),
            "total_amount": round(total_amount, 2),
        },
    )


# ---------------------------------------------------------------------------
# MT-10: Retirement Delay
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-10",
    name="Retirement Delay",
    category=_CAT,
    description="No investment transactions despite positive savings rate",
)
def retirement_delay(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    savings_rate = ctx.get("savings_rate", 0)
    investment_amount = spending.get("investments", 0)

    has_positive_savings = savings_rate > 0
    has_investments = investment_amount > 0

    triggered = has_positive_savings and not has_investments
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Savings rate is {savings_rate:.1f}% but no investment activity — "
        "consider putting savings to work."
        if triggered
        else "Investment activity detected alongside savings — good diversification."
        if has_investments
        else "No investment data available."
    )
    return RuleResult(
        rule_id="MT-10",
        name="Retirement Delay",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "savings_rate": savings_rate,
            "investment_amount": investment_amount,
        },
    )


# ---------------------------------------------------------------------------
# MT-11: Brand Loyalty Tax
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-11",
    name="Brand Loyalty Tax",
    category=_CAT,
    description="High concentration in single categories without diversification",
)
def brand_loyalty_tax(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_expenses = ctx.get("total_expenses", 0)
    if total_expenses <= 0:
        return _insufficient_data("MT-11", "Brand Loyalty Tax", "no expense data")

    expense_cats = {
        k: v
        for k, v in spending.items()
        if k not in {"salary", "freelance", "savings", "investments"} and v > 0
    }
    if not expense_cats:
        return _insufficient_data("MT-11", "Brand Loyalty Tax", "no spending categories")

    max_cat = max(expense_cats, key=expense_cats.get)  # type: ignore[arg-type]
    max_ratio = expense_cats[max_cat] / total_expenses

    triggered = max_ratio > 0.50
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"'{max_cat}' alone accounts for {max_ratio:.0%} of spending — high concentration risk."
        if triggered
        else f"Spending is reasonably diversified (top category: {max_cat} at {max_ratio:.0%})."
    )
    return RuleResult(
        rule_id="MT-11",
        name="Brand Loyalty Tax",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "top_category": max_cat,
            "concentration_ratio": round(max_ratio, 4),
        },
    )


# ---------------------------------------------------------------------------
# MT-12: Side Hustle Trap
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="MT-12",
    name="Side Hustle Trap",
    category=_CAT,
    description="Freelance income less than associated freelance expenses (net negative)",
)
def side_hustle_trap(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    freelance_income = sum(
        t.get("amount", 0)
        for t in transactions
        if t.get("category") == "freelance" and t.get("type") == "income"
    )
    freelance_expense = sum(
        t.get("amount", 0)
        for t in transactions
        if t.get("category") == "freelance" and t.get("type") == "expense"
    )

    if freelance_income == 0 and freelance_expense == 0:
        return _insufficient_data("MT-12", "Side Hustle Trap", "no freelance transactions")

    net = freelance_income - freelance_expense
    triggered = net < 0
    severity = RuleSeverity.warning if triggered else RuleSeverity.info
    msg = (
        f"Freelance is net negative ({net:.2f}) — expenses exceed income."
        if triggered
        else f"Freelance net positive ({net:.2f})."
        if freelance_income > 0
        else "No freelance income to evaluate."
    )
    return RuleResult(
        rule_id="MT-12",
        name="Side Hustle Trap",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "freelance_income": freelance_income,
            "freelance_expense": freelance_expense,
            "net": round(net, 2),
        },
    )
