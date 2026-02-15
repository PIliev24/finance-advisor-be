from enum import StrEnum


class Category(StrEnum):
    food = "food"
    transport = "transport"
    housing = "housing"
    utilities = "utilities"
    entertainment = "entertainment"
    health = "health"
    education = "education"
    clothing = "clothing"
    savings = "savings"
    investments = "investments"
    salary = "salary"
    freelance = "freelance"
    gifts = "gifts"
    subscriptions = "subscriptions"
    insurance = "insurance"
    debt_payment = "debt_payment"
    other = "other"


class TransactionType(StrEnum):
    income = "income"
    expense = "expense"
