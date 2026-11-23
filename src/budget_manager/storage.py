"""Storage: read and write the transactions JSON file, and back it up.

This module knows about files and JSON. It does not contain budget rules:
every record it loads goes through validation.parse_record.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from budget_manager.models import Transaction
from budget_manager.validation import parse_record


class StorageError(Exception):
    """The data file or a backup cannot be used: missing, unreadable or corrupt.

    It is not a ValueError on purpose: cli.py treats it as a file problem
    (exit 1), different from invalid user input (ValueError, exit 2).
    """


def load_transactions(path: Path) -> tuple[list[Transaction], list[str]]:
    """Return (valid transactions, error messages) from the JSON file.

    - File does not exist -> ([], []): the first add will create it.
    - File is not valid JSON, or is not a list -> StorageError.
      Never an empty list: saving afterwards would erase the data.
    - Invalid or duplicated records are skipped and reported in the errors.
    """
    path = Path(path)
    if not path.exists():
        return [], []

    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except OSError as error:
        raise StorageError(f"cannot read {path}: {error}") from None
    except json.JSONDecodeError as error:
        raise StorageError(
            f"{path} is not valid JSON (line {error.lineno}, column {error.colno}): "
            f"{error.msg}. The file was not modified."
        ) from None

    if not isinstance(data, list):
        raise StorageError(
            f"{path} must contain a JSON list of transactions, "
            f"got {type(data).__name__}. The file was not modified."
        )

    transactions = []
    errors = []
    seen_ids = set()
    for index, record in enumerate(data, start=1):
        try:
            transaction = parse_record(record, index)
        except ValueError as error:
            errors.append(str(error))
            continue
        if transaction.id in seen_ids:
            errors.append(f"Record {index} ({transaction.id}): duplicate id")
            continue
        seen_ids.add(transaction.id)
        transactions.append(transaction)

    return transactions, errors


def save_transactions(path: Path, transactions: list[Transaction]) -> None:
    """Write all transactions to the JSON file safely.

    Writes to a temporary file next to the target, then replaces the target
    in one step. If anything fails before the replace, the old file is intact.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [t.to_dict() for t in transactions]
    temporary = path.with_name(path.name + ".tmp")

    try:
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def backup(
    path: Path, backup_dir: Path, keep: int = 7, destination: Path | None = None
) -> Path:
    """Copy the data file and return the copy's path.

    - destination given -> copy to exactly that file (never overwrites it).
    - no destination -> backup_dir/<name>-<timestamp>.json, and only the
      newest `keep` timestamped backups are kept.
    The copy is verified (same bytes, readable JSON) before old backups are
    removed.
    """
    path = Path(path)
    backup_dir = Path(backup_dir)
    if keep < 1:
        raise ValueError(f"keep must be at least 1, got {keep}")
    if not path.exists():
        raise StorageError(f"nothing to back up: {path} does not exist")

    if destination is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = backup_dir / f"{path.stem}-{stamp}{path.suffix}"
        rotate = True
    else:
        destination = Path(destination)
        rotate = False

    if destination.exists():
        raise StorageError(f"backup {destination} already exists; it was not overwritten")

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    except OSError as error:
        raise StorageError(f"cannot create backup {destination}: {error}") from None

    # Verify before deleting anything old.
    try:
        same_bytes = destination.read_bytes() == path.read_bytes()
        json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        same_bytes = False
    if not same_bytes:
        destination.unlink(missing_ok=True)
        raise StorageError(f"backup {destination} could not be verified and was removed")

    # Retention, only for automatic backups: names contain the timestamp,
    # so sorting by name is sorting by date.
    if rotate:
        backups = sorted(backup_dir.glob(f"{path.stem}-*{path.suffix}"))
        for old in backups[:-keep]:
            old.unlink()

    return destination