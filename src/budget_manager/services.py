"""Budget logic: pure functions over a list of transactions.

Nothing here reads files, prints, or asks for input. Every function
receives data and returns a result, so it can be tested directly.
"""

from datetime import date

from budget_manager.models import DEFAULT_CURRENCY, Transaction
from budget_manager.validation import (
    validate_amount,
    validate_category,
    validate_currency,
    validate_date,
    validate_kind,
    validate_month,
)


def next_id(transactions: list[Transaction]) -> str:
    """Return the next free id: "T001" for an empty list, else highest + 1."""
    if not transactions:
        return "T001"
    highest = max(int(t.id[1:]) for t in transactions)
    return f"T{highest + 1:03d}"


def add_transaction(
    transactions: list[Transaction],
    amount,
    category,
    kind="expense",
    date_text=None,
    currency=DEFAULT_CURRENCY,
) -> list[Transaction]:
    """Validate the raw values and return a NEW list with the transaction added.

    The original list is not modified. date_text defaults to today.
    Raises ValueError (from validation) if any value is invalid.
    """
    if date_text is None:
        date_text = date.today().isoformat()

    new = Transaction(
        id=next_id(transactions),
        date=validate_date(date_text),
        kind=validate_kind(kind),
        category=validate_category(category),
        amount=validate_amount(amount),
        currency=validate_currency(currency),
    )
    return transactions + [new]


def filter_by_month(transactions: list[Transaction], month: str) -> list[Transaction]:
    """Return only the transactions of month "YYYY-MM"."""
    month = validate_month(month)
    return [t for t in transactions if t.date.startswith(month)]


def summarize(transactions: list[Transaction]) -> dict:
    """Return income, expenses, balance and expenses by category, rounded to 2."""
    income = sum(t.amount for t in transactions if t.kind == "income")
    expenses = sum(t.amount for t in transactions if t.kind == "expense")

    by_category = {}
    for t in transactions:
        if t.kind == "expense":
            by_category[t.category] = by_category.get(t.category, 0) + t.amount

    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "balance": round(income - expenses, 2),
        "expenses_by_category": {
            category: round(total, 2)
            for category, total in sorted(by_category.items())
        },
    }