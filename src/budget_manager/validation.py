"""Validation at the boundary: turn raw input into clean values or fail clearly.

Every function receives a raw value (from JSON, argparse or input()),
returns the clean value, or raises ValueError with a message the user
can act on. Nothing here fixes ambiguous data silently.
"""

from datetime import date

from budget_manager.models import CATEGORIES, CURRENCIES, FIELDS, KINDS, Transaction

def _format_allowed(values: set) -> str:
    """Return the allowed values as sorted, comma-separated text."""
    return ", ".join(sorted(values))


def validate_amount(value) -> float:
    """Return the amount as a float > 0.

    Accepts int, float, or text such as "18.5" (input() and argparse give text).
    Rejects: bool, text that is not a number, 0, negatives.
    Example message: "amount must be > 0, got -5"
    """

    # 1. Type: bool goes first, because True would pass as the number 1.
    if isinstance(value, bool):
        raise ValueError(f"amount must be a number, got {value!r}")

    # 2. Convert: text becomes a number; other types are rejected.
    if isinstance(value, str):
        try:
            amount = float(value.strip())
        except ValueError:
            raise ValueError(f"amount must be a number, got {value!r}") from None
    elif isinstance(value, (int, float)):
        amount = float(value)
    else:
        raise ValueError(f"amount must be a number, got {value!r}")

    # 3. Rule: the amount itself is always positive; kind gives the sign.
    if amount <= 0:
        raise ValueError(f"amount must be > 0, got {amount}")

    # 4. Return the clean value.
    return amount


def validate_kind(value) -> str:
    """Return the kind in lowercase, without spaces around it.

    " Income " -> "income". Must be one of KINDS.
    Example message: "kind must be one of: expense, income"
    """
    # 1. Type: kind is cleaned and must be a str
    if not isinstance(value, str):
        raise ValueError(f"kind must be text, got {value!r}")
    
    # 2. Clean: no spaces around it, lowercase
    cleaned = value.strip().lower()

    # 3. Rule: must be on of the allowed kinds
    if cleaned not in KINDS:
        raise ValueError(f"kind must be one of: {_format_allowed(KINDS)}, got {value!r}")

    # 4. Return the clean value
    return cleaned


def validate_category(value) -> str:
    """Return the category in lowercase, without spaces around it.

    " Food " -> "food". Must be one of CATEGORIES.
    Example message: "unknown category 'pizza'"
    """
    # 1. Type: category is cleaned and must be a str
    if not isinstance(value, str):
        raise ValueError(f"category must be text, got {value!r}")
    
    # 2. Clean: no spaces around it, lowercase
    cleaned = value.strip().lower()

    # 3. Rule: must be on of the allowed categoriess
    if cleaned not in CATEGORIES:
        raise ValueError(f"unknown category {value!r}; use one of {_format_allowed(CATEGORIES)}")

    # 4. Return the clean value
    return cleaned


def validate_currency(value) -> str:
    """Return the currency in uppercase, without spaces around it.

    "eur" -> "EUR". Must be one of CURRENCIES.
    """
    # 1. Type: currency is cleaned and must be a str
    if not isinstance(value, str):
        raise ValueError(f"currency must be text, got {value!r}")
    
    # 2. Clean: no spaces around it, lowercase
    cleaned = value.strip().upper()

    # 3. Rule: must be on of the allowed currencies
    if cleaned not in CURRENCIES:
        raise ValueError(f"unsupported currency {value!r}; use one of {_format_allowed(CURRENCIES)}")

    # 4. Return the clean value
    return cleaned


def validate_date(value) -> str:
    """Return the date as text in the exact format YYYY-MM-DD.

    It must also be a real date: "2026-13-01" and "2026-02-30" fail.
    Example message: "date must be YYYY-MM-DD, got '2026-13-01'"
    """
    # 1. Type: only text is accepted.
    if not isinstance(value, str):
        raise ValueError(f"date must be text in YYYY-MM-DD format, got {value!r}")

    # 2. Clean: no spaces around it.
    cleaned = value.strip()

    # 3a. Rule: must be a real date (month 1-12, valid day, leap years).
    try:
        parsed = date.fromisoformat(cleaned)
    except ValueError:
        raise ValueError(
            f"date must be a real date in YYYY-MM-DD format, got {value!r}"
        ) from None

    # 3b. Rule: exactly YYYY-MM-DD. fromisoformat also accepts "20260904"
    # and "2026-W36-5"; converting back and comparing rejects them.
    if parsed.isoformat() != cleaned:
        raise ValueError(f"date must be in YYYY-MM-DD format, got {value!r}")

    # 4. Return the clean text, not the date object (the model stores str).
    return cleaned


def validate_month(value) -> str:
    """Return the month as text in the exact format YYYY-MM, e.g. "2026-09"."""
    if not isinstance(value, str):
        raise ValueError(f"month must be text in YYYY-MM format, got {value!r}")
    cleaned = value.strip()
    try:
        parsed = date.fromisoformat(f"{cleaned}-01")
    except ValueError:
        raise ValueError(
            f"month must be a real month in YYYY-MM format, got {value!r}"
        ) from None
    if parsed.isoformat()[:7] != cleaned:
        raise ValueError(f"month must be in YYYY-MM format, got {value!r}")
    return cleaned


def validate_id(value) -> str:
    """Return the id if it looks like "T" followed by digits, e.g. "T001"."""
    # 1. Type: only text is accepted.
    if not isinstance(value, str):
        raise ValueError(f"id must be text like 'T001', got {value!r}")

    # 2. Clean: no spaces around it. Case is not changed: ids are generated
    # by the program, so "t001" means the file was edited by hand.
    cleaned = value.strip()

    # 3. Rule: "T" followed by one or more ASCII digits.
    # isascii() is needed because isdigit() also accepts "²" or "٣".
    number = cleaned[1:]
    if not (cleaned.startswith("T") and number.isascii() and number.isdigit()):
        raise ValueError(
            f"id must be 'T' followed by digits, like 'T001', got {value!r}"
        )

    # 4. Return the clean value.
    return cleaned


def parse_record(record, index: int) -> Transaction:
    """Turn one record loaded from JSON (a dict) into a Transaction.

    index is the record's position in the file, starting at 1.
    Checks that record is a dict and has exactly the fields in FIELDS,
    then validates each field with the functions above.
    Any error is raised again with the position and id in front:
    "Record 4 (T004): amount must be > 0, got -12.0"
    """
        # 1. Type: each record in the JSON list must be an object (dict).
    if not isinstance(record, dict):
        raise ValueError(
            f"Record {index}: must be an object with fields, got {record!r}"
        )

    # Prefix for every message. get() because the id may be missing.
    prefix = f"Record {index} ({record.get('id', '?')})"

    # 2. Structure: exactly the fields in FIELDS, no more, no less.
    missing = [field for field in FIELDS if field not in record]
    if missing:
        raise ValueError(f"{prefix}: missing field(s): {', '.join(missing)}")

    extra = [key for key in record if key not in FIELDS]
    if extra:
        raise ValueError(f"{prefix}: unexpected field(s): {', '.join(extra)}")

    # 3. Content: each field through its validator. The first error stops
    # the record and comes back with the prefix in front.
    try:
        return Transaction(
            id=validate_id(record["id"]),
            date=validate_date(record["date"]),
            kind=validate_kind(record["kind"]),
            category=validate_category(record["category"]),
            amount=validate_amount(record["amount"]),
            currency=validate_currency(record["currency"]),
        )
    except ValueError as error:
        raise ValueError(f"{prefix}: {error}") from None