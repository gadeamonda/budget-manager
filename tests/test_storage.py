"""Tests for storage.py: real files, each test in its own temporary folder.

tmp_path is a pytest fixture: a new empty folder (a pathlib.Path) for every
test, deleted afterwards. Tests never touch data/transactions.json.
"""

import json

import pytest

from budget_manager import storage
from budget_manager.models import Transaction
from budget_manager.storage import (
    StorageError,
    backup,
    load_transactions,
    save_transactions,
)

TRANSACTIONS = [
    Transaction("T001", "2026-09-01", "income", "salary", 2500.0, "EUR"),
    Transaction("T002", "2026-09-04", "expense", "food", 18.5, "EUR"),
]


def write_json(path, data):
    """Helper: write any Python data as JSON, to prepare test files."""
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------- load_transactions ----------

def test_load_missing_file_is_empty(tmp_path):
    assert load_transactions(tmp_path / "nope.json") == ([], [])


def test_save_then_load_gives_same_transactions(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    loaded, errors = load_transactions(path)
    assert loaded == TRANSACTIONS
    assert errors == []


def test_load_skips_invalid_records_and_reports_them(tmp_path):
    path = tmp_path / "transactions.json"
    good = TRANSACTIONS[0].to_dict()
    bad = {**TRANSACTIONS[1].to_dict(), "amount": -12.0}
    write_json(path, [good, bad])

    loaded, errors = load_transactions(path)

    assert loaded == [TRANSACTIONS[0]]
    assert len(errors) == 1
    assert "Record 2 (T002): amount must be > 0" in errors[0]


def test_load_reports_duplicate_ids(tmp_path):
    path = tmp_path / "transactions.json"
    record = TRANSACTIONS[0].to_dict()
    write_json(path, [record, record])

    loaded, errors = load_transactions(path)

    assert len(loaded) == 1
    assert "duplicate id" in errors[0]


def test_load_corrupt_json_raises_and_keeps_file(tmp_path):
    path = tmp_path / "transactions.json"
    path.write_text('[{"id": "T001",}]', encoding="utf-8")  # trailing comma
    before = path.read_bytes()

    with pytest.raises(StorageError, match="not valid JSON"):
        load_transactions(path)

    assert path.read_bytes() == before


def test_load_rejects_json_that_is_not_a_list(tmp_path):
    path = tmp_path / "transactions.json"
    write_json(path, {"id": "T001"})
    with pytest.raises(StorageError, match="must contain a JSON list"):
        load_transactions(path)


def test_storage_error_is_not_a_value_error():
    # cli.py relies on this to give exit 1 (file) instead of 2 (input).
    assert not issubclass(StorageError, ValueError)


# ---------- save_transactions ----------

def test_save_creates_missing_folder(tmp_path):
    path = tmp_path / "new_folder" / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    assert path.exists()


def test_save_writes_readable_json_and_no_temp_file(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == [t.to_dict() for t in TRANSACTIONS]
    assert list(tmp_path.glob("*.tmp")) == []


def test_failed_save_keeps_original_file(tmp_path, monkeypatch):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    before = path.read_bytes()

    # monkeypatch replaces os.fsync inside storage only during this test,
    # to simulate the disk