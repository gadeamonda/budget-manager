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

def test_backup_creates_identical_copy(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)

    copy = backup(path, tmp_path / "backups")

    assert copy.exists()
    assert copy.read_bytes() == path.read_bytes()
    assert copy.name.startswith("transactions-")


def test_backup_without_data_file_raises(tmp_path):
    with pytest.raises(StorageError, match="nothing to back up"):
        backup(tmp_path / "nope.json", tmp_path / "backups")


def test_backup_keeps_only_newest(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for day in range(1, 6):  # five old backups from January 2026
        (backup_dir / f"transactions-2026010{day}-000000.json").write_text("[]")

    newest = backup(path, backup_dir, keep=3)

    remaining = sorted(p.name for p in backup_dir.iterdir())
    assert len(remaining) == 3
    assert newest.name in remaining
    assert "transactions-20260101-000000.json" not in remaining


def test_backup_rejects_keep_below_one(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    with pytest.raises(ValueError, match="keep must be at least 1"):
        backup(path, tmp_path / "backups", keep=0)







def test_backup_to_given_destination(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    target = tmp_path / "copies" / "backup.json"

    copy = backup(path, tmp_path / "backups", destination=target)

    assert copy == target
    assert target.read_bytes() == path.read_bytes()


def test_backup_never_overwrites_given_destination(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    target = tmp_path / "backup.json"
    target.write_text("old backup", encoding="utf-8")

    with pytest.raises(StorageError, match="already exists"):
        backup(path, tmp_path / "backups", destination=target)

    assert target.read_text(encoding="utf-8") == "old backup"


def test_backup_with_destination_does_not_delete_other_backups(tmp_path):
    path = tmp_path / "transactions.json"
    save_transactions(path, TRANSACTIONS)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for day in range(1, 6):
        (backup_dir / f"transactions-2026010{day}-000000.json").write_text("[]")

    backup(path, backup_dir, keep=1, destination=tmp_path / "extra.json")

    assert len(list(backup_dir.iterdir())) == 5