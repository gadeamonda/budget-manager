"""Tests for validation.py: each validator accepts clean input,
normalizes it, and rejects bad input with a clear ValueError."""

import pytest

from budget_manager.models import Transaction
from budget_manager.validation import (
    parse_record,
    validate_amount,
    validate_category,
    validate_currency,
    validate_date,
    validate_id,
    validate_kind,
    validate_month,
)


# ---------- validate_amount ----------

def test_amount_accepts_number_and_text():
    assert validate_amount(18.5) == 18.5
    assert validate_amount(10) == 10.0
    assert validate_amount(" 18.5 ") == 18.5


@pytest.mark.parametrize("bad", [0, -5, "-3"])
def test_amount_rejects_zero_and_negative(bad):
    with pytest.raises(ValueError, match="must be > 0"):
        validate_amount(bad)


@pytest.mark.parametrize("bad", ["abc", "", None, True])
def test_amount_rejects_non_numbers(bad):
    # True is the important one: bool is a subclass of int.
    with pytest.raises(ValueError, match="must be a number"):
        validate_amount(bad)


# ---------- kind, category, currency ----------

def test_kind_is_normalized():
    assert validate_kind(" Income ") == "income"


def test_kind_rejects_unknown():
    with pytest.raises(ValueError, match="kind must be one of"):
        validate_kind("gift")


def test_category_is_normalized():
    assert validate_category(" Food ") == "food"


def test_category_rejects_unknown():
    with pytest.raises(ValueError, match="unknown category 'pizza'"):
        validate_category("pizza")


def test_category_rejects_non_text():
    with pytest.raises(ValueError, match="must be text"):
        validate_category(5)


def test_currency_is_uppercased():
    assert validate_currency(" eur ") == "EUR"


def test_currency_rejects_unsupported():
    with pytest.raises(ValueError, match="unsupported currency"):
        validate_currency("USD")


# ---------- validate_date and validate_month ----------

def test_date_accepts_real_date():
    assert validate_date(" 2026-09-04 ") == "2026-09-04"
    assert validate_date("2024-02-29") == "2024-02-29"  # leap year


@pytest.mark.parametrize("bad", ["2026-13-01", "2026-02-30", "2026-02-29", "04/09/2026", ""])
def test_date_rejects_impossible_dates(bad):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_date(bad)


@pytest.mark.parametrize("bad", ["20260904", "2026-W36-5"])
def test_date_rejects_other_iso_formats(bad):
    # fromisoformat accepts these since Python 3.11; we must not.
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validate_date(bad)


def test_month_accepts_and_rejects():
    assert validate_month("2026-09") == "2026-09"
    with pytest.raises(ValueError, match="YYYY-MM"):
        validate_month("2026-13")


# ---------- validate_id ----------

@pytest.mark.parametrize("good", ["T001", "T1000"])
def test_id_accepts_t_and_digits(good):
    assert validate_id(good) == good


@pytest.mark.parametrize("bad", ["t001", "T", "001", "T01a", "T²"])
def test_id_rejects_bad_shapes(bad):
    with pytest.raises(ValueError, match="'T' followed by digits"):
        validate_id(bad)


# ---------- parse_record ----------

VALID_RECORD = {
    "id": "T001",
    "date": "2026-09-04",
    "kind": "expense",
    "category": "food",
    "amount": 18.5,
    "currency": "EUR",
}


def test_parse_record_builds_transaction():
    expected = Transaction("T001", "2026-09-04", "expense", "food", 18.5, "EUR")
    assert parse_record(VALID_RECORD, 1) == expected


def test_parse_record_adds_position_and_id_to_errors():
    record = {**VALID_RECORD, "id": "T004", "amount": -12.0}
    with pytest.raises(ValueError, match=r"Record 4 \(T004\): amount must be > 0"):
        parse_record(record, 4)


def test_parse_record_reports_missing_field():
    record = {key: value for key, value in VALID_RECORD.items() if key != "category"}
    with pytest.raises(ValueError, match="missing field"):
        parse_record(record, 1)


def test_parse_record_reports_extra_field():
    record = {**VALID_RECORD, "note": "lunch"}
    with pytest.raises(ValueError, match="unexpected field"):
        parse_record(record, 1)


def test_parse_record_without_id_still_has_prefix():
    record = {key: value for key, value in VALID_RECORD.items() if key != "id"}
    with pytest.raises(ValueError, match=r"Record 9 \(\?\)"):
        parse_record(record, 9)


def test_parse_record_rejects_non_dict():
    with pytest.raises(ValueError, match="must be an object"):
        parse_record("T010", 10)