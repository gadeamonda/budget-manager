"""Domain model: the transaction schema and its allowed values.

This module only describes what a transaction is. It does not read files,
print anything, or check the rules: validation.py does that.
"""

KINDS = {"income", "expense"}
CATEGORIES = {
    "salary",
    "food",
    "transport",
    "housing",
    "entertainment",
    "health",
    "other",
}
CURRENCIES = {"EUR"}
DEFAULT_CURRENCY = "EUR"

# Field order used to save and to check records loaded from JSON.
FIELDS = ("id", "date", "kind", "category", "amount", "currency")


class Transaction:
    """One income or expense record.

    Create transactions through validation.parse_record, not directly,
    so every Transaction in the program has passed the rules.
    """

    def __init__(
        self,
        id: str,
        date: str,
        kind: str,
        category: str,
        amount: float,
        currency: str,
    ) -> None:
        self.id = id              # "T001"
        self.date = date          # ISO text "YYYY-MM-DD"
        self.kind = kind          # one of KINDS
        self.category = category  # one of CATEGORIES
        self.amount = amount      # always > 0; the sign comes from kind
        self.currency = currency  # one of CURRENCIES

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id!r}, date={self.date!r}, "
            f"kind={self.kind!r}, category={self.category!r}, "
            f"amount={self.amount!r}, currency={self.currency!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    @property
    def signed_amount(self) -> float:
        """Amount with sign: positive for income, negative for expense."""
        if self.kind == "income":
            return self.amount
        return -self.amount

    def to_dict(self) -> dict:
        """Return the transaction as a plain dict, ready for json.dump."""
        return {field: getattr(self, field) for field in FIELDS}