"""Smart habit rules — positive financial patterns worth reinforcing."""

from app.advisor.schemas import RuleCategory, RuleResult, RuleSeverity

from .registry import registry

_CAT = RuleCategory.smart_habit


def _insufficient_data(rule_id: str, name: str, reason: str) -> RuleResult:
    """Helper for rules that cannot evaluate due to missing data."""
    return RuleResult(
        rule_id=rule_id,
        name=name,
        category=_CAT,
        triggered=False,
        severity=RuleSeverity.warning,
        message=f"Insufficient data to evaluate: {reason}",
    )


# ---------------------------------------------------------------------------
# SH-01: Spend Money to Save Time
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-01",
    name="Spend Money to Save Time",
    category=_CAT,
    description="Time-saving service purchases relative to income level",
)
def spend_to_save_time(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("SH-01", "Spend Money to Save Time", "no income data")

    time_saving_cats = {"subscriptions", "utilities"}
    time_saving_spend = sum(spending.get(c, 0) for c in time_saving_cats)
    ratio = time_saving_spend / total_income

    triggered = 0.01 < ratio < 0.10
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Spending {ratio:.1%} on time-saving services — smart use of money when "
        "income supports it."
        if triggered
        else "Consider whether modest spending on services could free up valuable time."
    )
    return RuleResult(
        rule_id="SH-01",
        name="Spend Money to Save Time",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"time_saving_spend": round(time_saving_spend, 2), "ratio": round(ratio, 4)},
    )


# ---------------------------------------------------------------------------
# SH-02: Measure in Hours
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-02",
    name="Measure in Hours",
    category=_CAT,
    description="Purchases relative to estimated hourly wage",
)
def measure_in_hours(ctx: dict) -> RuleResult:
    total_income = ctx.get("total_income", 0)
    trends = ctx.get("spending_trends", [])
    num_months = max(len(trends), 1)

    if total_income <= 0:
        return _insufficient_data("SH-02", "Measure in Hours", "no income data")

    monthly_income = total_income / num_months
    hourly_wage = monthly_income / (22 * 8)

    transactions = ctx.get("transactions", [])
    discretionary_cats = {"entertainment", "clothing", "gifts"}
    big_discretionary = [
        t
        for t in transactions
        if t.get("category") in discretionary_cats
        and t.get("type") == "expense"
        and t.get("amount", 0) > hourly_wage * 4
    ]

    triggered = len(big_discretionary) == 0 and len(transactions) > 0
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"No discretionary purchases exceed 4 hours of work (~{hourly_wage * 4:.2f}) — "
        "spending is proportional to earnings."
        if triggered
        else f"Some discretionary purchases exceed 4 hours of work (~{hourly_wage * 4:.2f}). "
        "Consider evaluating large purchases in hours worked."
    )
    return RuleResult(
        rule_id="SH-02",
        name="Measure in Hours",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "hourly_wage": round(hourly_wage, 2),
            "large_discretionary_count": len(big_discretionary),
        },
    )


# ---------------------------------------------------------------------------
# SH-03: Leverage Good Debt
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-03",
    name="Leverage Good Debt",
    category=_CAT,
    description="Debt-to-income ratio below 36%",
)
def leverage_good_debt(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("SH-03", "Leverage Good Debt", "no income data")

    debt = spending.get("debt_payment", 0)
    ratio = debt / total_income

    triggered = 0 < ratio < 0.36
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Debt-to-income ratio is {ratio:.1%} — within the healthy 36% guideline."
        if triggered
        else f"Debt-to-income is {ratio:.1%}. "
        + (
            "Consider using strategic debt to build assets."
            if ratio == 0
            else "Ratio exceeds 36% — work on reducing debt."
        )
    )
    return RuleResult(
        rule_id="SH-03",
        name="Leverage Good Debt",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"debt_payment": debt, "income": total_income, "ratio": round(ratio, 4)},
    )


# ---------------------------------------------------------------------------
# SH-04: Strategic Spending
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-04",
    name="Strategic Spending",
    category=_CAT,
    description="Education/self-investment spending present",
)
def strategic_spending(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    education = spending.get("education", 0)

    triggered = education > 0
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Investing {education:.2f} in education/self-development — strategic spending."
        if triggered
        else "No education spending detected — consider investing in skills and knowledge."
    )
    return RuleResult(
        rule_id="SH-04",
        name="Strategic Spending",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"education_spending": education},
    )


# ---------------------------------------------------------------------------
# SH-05: Invest in Yourself
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-05",
    name="Invest in Yourself",
    category=_CAT,
    description="Regular education entries appearing in multiple months",
)
def invest_in_yourself(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    edu_months: set[str] = set()
    for t in transactions:
        if t.get("category") == "education" and t.get("type") == "expense":
            date_str = t.get("date", "")
            if len(date_str) >= 7:
                edu_months.add(date_str[:7])

    triggered = len(edu_months) >= 2
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Education spending in {len(edu_months)} different months — consistent self-investment."
        if triggered
        else "Education spending is sporadic or absent — consistency builds compounding returns."
    )
    return RuleResult(
        rule_id="SH-05",
        name="Invest in Yourself",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"education_months": len(edu_months)},
    )


# ---------------------------------------------------------------------------
# SH-06: Avoid Good Deals
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-06",
    name="Avoid Good Deals",
    category=_CAT,
    description="No spending spikes during typical sale months",
)
def avoid_good_deals(ctx: dict) -> RuleResult:
    trends = ctx.get("spending_trends", [])
    if len(trends) < 3:
        return _insufficient_data("SH-06", "Avoid Good Deals", "need 3+ months of trends")

    sale_months = {"06", "07", "11", "12"}
    sale_expenses: list[float] = []
    normal_expenses: list[float] = []

    for t in trends:
        ym = t.get("year_month", "")
        month_part = ym[5:7] if len(ym) >= 7 else ""
        expense = t.get("total_expenses", 0)
        if month_part in sale_months:
            sale_expenses.append(expense)
        else:
            normal_expenses.append(expense)

    if not normal_expenses or not sale_expenses:
        return _insufficient_data("SH-06", "Avoid Good Deals", "insufficient seasonal data")

    avg_normal = sum(normal_expenses) / len(normal_expenses)
    avg_sale = sum(sale_expenses) / len(sale_expenses)

    triggered = avg_sale <= avg_normal * 1.15 if avg_normal > 0 else True
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        "No significant spending spikes during sale periods — disciplined spending."
        if triggered
        else "Spending increases during sale periods — 'good deals' may cost more overall."
    )
    return RuleResult(
        rule_id="SH-06",
        name="Avoid Good Deals",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "avg_sale_spending": round(avg_sale, 2),
            "avg_normal_spending": round(avg_normal, 2),
        },
    )


# ---------------------------------------------------------------------------
# SH-07: Overpay for Quality
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-07",
    name="Overpay for Quality",
    category=_CAT,
    description="Low frequency, high-value durable goods purchases",
)
def overpay_for_quality(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    durable_cats = {"clothing", "health", "education"}
    durable_txns = [
        t for t in transactions if t.get("category") in durable_cats and t.get("type") == "expense"
    ]

    if not durable_txns:
        return _insufficient_data("SH-07", "Overpay for Quality", "no durable category purchases")

    amounts = [t.get("amount", 0) for t in durable_txns]
    avg_amount = sum(amounts) / len(amounts) if amounts else 0

    months_set: set[str] = set()
    for t in transactions:
        date_str = t.get("date", "")
        if len(date_str) >= 7:
            months_set.add(date_str[:7])
    num_months = max(len(months_set), 1)

    frequency = len(durable_txns) / num_months

    triggered = frequency <= 5 and avg_amount > 50
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Few but meaningful purchases (avg {avg_amount:.2f}, "
        f"{frequency:.1f}/month) — quality over quantity."
        if triggered
        else "Purchase pattern suggests frequent, lower-value buys — "
        "consider fewer, higher-quality purchases."
    )
    return RuleResult(
        rule_id="SH-07",
        name="Overpay for Quality",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "avg_amount": round(avg_amount, 2),
            "frequency_per_month": round(frequency, 2),
        },
    )


# ---------------------------------------------------------------------------
# SH-08: Spend on Mistakes
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-08",
    name="Spend on Mistakes",
    category=_CAT,
    description="Learning/education spending present — willingness to invest in growth",
)
def spend_on_mistakes(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    education = spending.get("education", 0)
    health = spending.get("health", 0)

    growth_spend = education + health
    triggered = growth_spend > 0
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Spending {growth_spend:.2f} on education + health — "
        "investing in growth and learning from experience."
        if triggered
        else "No education/health spending — consider investing in personal growth."
    )
    return RuleResult(
        rule_id="SH-08",
        name="Spend on Mistakes",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"education": education, "health": health, "total_growth": growth_spend},
    )


# ---------------------------------------------------------------------------
# SH-09: Emotional Detachment
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-09",
    name="Emotional Detachment",
    category=_CAT,
    description="Consistent savings regardless of income fluctuations",
)
def emotional_detachment(ctx: dict) -> RuleResult:
    trends = ctx.get("spending_trends", [])
    if len(trends) < 3:
        return _insufficient_data("SH-09", "Emotional Detachment", "need 3+ months of trends")

    savings_rates: list[float] = []
    for t in trends:
        income = t.get("total_income", 0)
        expenses = t.get("total_expenses", 0)
        if income > 0:
            savings_rates.append((income - expenses) / income)

    if len(savings_rates) < 3:
        return _insufficient_data("SH-09", "Emotional Detachment", "insufficient income data")

    avg_rate = sum(savings_rates) / len(savings_rates)
    variance = sum((r - avg_rate) ** 2 for r in savings_rates) / len(savings_rates)
    std_dev = variance**0.5

    triggered = std_dev < 0.10 and avg_rate > 0
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Savings rate is consistent (std dev {std_dev:.1%}) — "
        "emotionally detached spending discipline."
        if triggered
        else f"Savings rate fluctuates significantly (std dev {std_dev:.1%}) — "
        "aim for consistent saving regardless of income changes."
    )
    return RuleResult(
        rule_id="SH-09",
        name="Emotional Detachment",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "avg_savings_rate": round(avg_rate, 4),
            "std_dev": round(std_dev, 4),
        },
    )


# ---------------------------------------------------------------------------
# SH-10: Ignore Windfalls
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-10",
    name="Ignore Windfalls",
    category=_CAT,
    description="No spending spikes after income spikes",
)
def ignore_windfalls(ctx: dict) -> RuleResult:
    trends = ctx.get("spending_trends", [])
    if len(trends) < 3:
        return _insufficient_data("SH-10", "Ignore Windfalls", "need 3+ months of trends")

    incomes = [t.get("total_income", 0) for t in trends]
    expenses = [t.get("total_expenses", 0) for t in trends]

    avg_income = sum(incomes) / len(incomes) if incomes else 0
    if avg_income <= 0:
        return _insufficient_data("SH-10", "Ignore Windfalls", "no income data")

    windfall_followed_by_spike = False
    for i in range(1, len(incomes)):
        income_jump = incomes[i] > avg_income * 1.20
        expense_jump = expenses[i] > expenses[i - 1] * 1.20 if expenses[i - 1] > 0 else False
        if income_jump and expense_jump:
            windfall_followed_by_spike = True
            break

    triggered = not windfall_followed_by_spike
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        "Income increases don't trigger spending spikes — disciplined windfall handling."
        if triggered
        else "Spending tends to spike after income increases — "
        "consider directing windfalls to savings/investments."
    )
    return RuleResult(
        rule_id="SH-10",
        name="Ignore Windfalls",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"windfall_spending_spike": windfall_followed_by_spike},
    )


# ---------------------------------------------------------------------------
# SH-11: Calculated Risks
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-11",
    name="Calculated Risks",
    category=_CAT,
    description="Investment category with diversification across months",
)
def calculated_risks(ctx: dict) -> RuleResult:
    transactions = ctx.get("transactions", [])
    invest_months: set[str] = set()
    for t in transactions:
        if t.get("category") == "investments" and t.get("type") == "expense":
            date_str = t.get("date", "")
            if len(date_str) >= 7:
                invest_months.add(date_str[:7])

    triggered = len(invest_months) >= 2
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Investment activity in {len(invest_months)} months — consistent risk-taking."
        if triggered
        else "Investment activity is sporadic or absent — "
        "consistent investing builds long-term wealth."
    )
    return RuleResult(
        rule_id="SH-11",
        name="Calculated Risks",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={"investment_months": len(invest_months)},
    )


# ---------------------------------------------------------------------------
# SH-12: Only Buy Affordable
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-12",
    name="Only Buy Affordable",
    category=_CAT,
    description="No debt-funded discretionary spending",
)
def only_buy_affordable(ctx: dict) -> RuleResult:
    spending = ctx.get("spending_by_category", {})
    total_income = ctx.get("total_income", 0)
    if total_income <= 0:
        return _insufficient_data("SH-12", "Only Buy Affordable", "no income data")

    debt = spending.get("debt_payment", 0)
    discretionary = spending.get("entertainment", 0) + spending.get("clothing", 0)

    debt_ratio = debt / total_income
    discretionary_ratio = discretionary / total_income

    triggered = not (debt_ratio > 0.10 and discretionary_ratio > 0.15)
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        "Discretionary spending appears self-funded — living within means."
        if triggered
        else "High debt payments combined with high discretionary spending — "
        "possible debt-funded lifestyle."
    )
    return RuleResult(
        rule_id="SH-12",
        name="Only Buy Affordable",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "debt_ratio": round(debt_ratio, 4),
            "discretionary_ratio": round(discretionary_ratio, 4),
        },
    )


# ---------------------------------------------------------------------------
# SH-13: Envy as Motivation
# ---------------------------------------------------------------------------
@registry.register(
    rule_id="SH-13",
    name="Envy as Motivation",
    category=_CAT,
    description="Savings rate trending upward over time",
)
def envy_as_motivation(ctx: dict) -> RuleResult:
    trends = ctx.get("spending_trends", [])
    if len(trends) < 3:
        return _insufficient_data("SH-13", "Envy as Motivation", "need 3+ months of trends")

    savings_rates: list[float] = []
    for t in trends:
        income = t.get("total_income", 0)
        expenses = t.get("total_expenses", 0)
        if income > 0:
            savings_rates.append((income - expenses) / income * 100)

    if len(savings_rates) < 3:
        return _insufficient_data("SH-13", "Envy as Motivation", "insufficient income data")

    improving = all(
        savings_rates[i] >= savings_rates[i - 1] - 1 for i in range(1, len(savings_rates))
    )
    overall_trend = savings_rates[-1] - savings_rates[0]

    triggered = improving and overall_trend > 0
    severity = RuleSeverity.info if triggered else RuleSeverity.warning
    msg = (
        f"Savings rate trending up (+{overall_trend:.1f}pp) — "
        "channeling motivation into financial progress."
        if triggered
        else "Savings rate is flat or declining — set incremental savings goals."
    )
    return RuleResult(
        rule_id="SH-13",
        name="Envy as Motivation",
        category=_CAT,
        triggered=triggered,
        severity=severity,
        message=msg,
        details={
            "first_rate": round(savings_rates[0], 2),
            "last_rate": round(savings_rates[-1], 2),
            "overall_change": round(overall_trend, 2),
        },
    )
