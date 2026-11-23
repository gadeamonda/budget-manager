"""Tests for services.py: pure functions over a list of transactions.
No files are involved, so each test builds its own small list."""

from datetime import date

import pytest

from budget_manager.models import Transaction
from budget_manager.services import (
    add_transaction,
    filter_by_month,
    next_id,
    summarize,
)


def make(id, day, kind, category, amount):
    """Shortcut to build a Transaction for the tests (always EUR)."""
    return Transaction(id, day, kind, category, amount, "EUR")


SEPTEMBER_AND_OCTOBER = [
    make("T001", "2026-09-01", "income", "salary", 2500.0),
    make("T002", "2026-09-04", "expense", "food", 18.5),
    make("T003", "2026-09-10", "expense", "transport", 45.0),
    make("T004", "2026-09-12", "expense", "food", 6.5),
    make("T005", "2026-10-02", "expense", "housing", 700.0),
]


# ---------- next_id ----------

def test_next_id_on_empty_list():
    assert next_id([]) == "T001"


def test_next_id_uses_highest_not_count():
    # Two transactions, but T009 exists: the next one is T010, not T003.
    transactions = [make("T009", "2026-09-01", "expense", "food", 1.0),
                    make("T001", "2026-09-01", "expense", "food", 1.0)]
    assert next_id(transactions) == "T010"


def test_next_id_grows_past_three_digits():
    assert next_id([make("T999", "2026-09-01", "expense", "food", 1.0)]) == "T1000"


# ---------- add_transaction ----------

def test_add_on_empty_list_creates_t001():
    result = add_transaction([], 18.5, "food", date_text="2026-09-04")
    assert len(result) == 1
    assert result[0] == make("T001", "2026-09-04", "expense", "food", 18.5)


def test_add_validates_and_cleans_raw_values():
    result = add_transaction([], "2500", " Salary ", kind="Income", date_text="2026-09-01")
    assert result[0] == make("T001", "2026-09-01", "income", "salary", 2500.0)


def test_add_uses_today_when_no_date():
    result = add_transaction([], 10, "food")
    assert result[0].date == date.today().isoformat()


def test_add_does_not_modify_the_original_list():
    original = [make("T001", "2026-09-01", "expense", "food", 5.0)]
    result = add_transaction(original, 10, "food", date_text="2026-09-02")
    assert len(original) == 1
    assert len(result) == 2


def test_add_invalid_value_raises_and_keeps_list():
    original = [make("T001", "2026-09-01", "expense", "food", 5.0)]
    with pytest.raises(ValueError, match="must be > 0"):
        add_transaction(original, -5, "food")
    assert len(original) == 1


# ---------- filter_by_month ----------

def test_filter_by_month_keeps_only_that_month():
    result = filter_by_month(SEPTEMBER_AND_OCTOBER, "2026-09")
    assert [t.id for t in result] == ["T001", "T002", "T003", "T004"]


def test_filter_by_month_without_data_is_empty():
    assert filter_by_month(SEPTEMBER_AND_OCTOBER, "2026-11") == []


def test_filter_by_month_rejects_bad_month():
    with pytest.raises(ValueError, match="YYYY-MM"):
        filter_by_month(SEPTEMBER_AND_OCTOBER, "2026-13")


# ---------- summarize ----------

def test_summarize_totals_and_categories():
    result = summarize(filter_by_month(SEPTEMBER_AND_OCTOBER, "2026-09"))
    assert result["income"] == 2500.0
    assert result["expenses"] == 70.0
    assert result["balance"] == 2430.0
    assert result["expenses_by_category"] == {"food": 25.0, "transport": 45.0}


def test_summarize_empty_list():
    result = summarize([])
    assert result["balance"] == 0
    assert result["expenses_by_category"] == {}


def test_summarize_rounds_float_noise():
    # 0.1 + 0.2 is 0.30000000000000004 with float; the summary shows 0.3.
    transactions = [make("T001", "2026-09-01", "expense", "food", 0.1),
                    make("T002", "2026-09-02", "expense", "food", 0.2)]
    assert summarize(transactions)["expenses"] == 0.3