# Design

## Main decision: JSON storage instead of CSV

Transactions are stored as a JSON list in `data/transactions.json`, although the
course template uses `sample_transactions.csv`. JSON keeps native types (numbers
stay numbers, so `amount` needs no conversion on load), maps directly to the
`Transaction.to_dict()` structure, and leaves room for nested data in later
practices (the API in Practice 2 will speak JSON anyway). The trade-off is
fragility: in CSV a broken line affects one row, while in JSON a single syntax
error (a trailing comma) makes the whole file unreadable. The program handles
this explicitly: a corrupt file is reported as an error and never treated as an
empty list, because saving after that would erase all the data. Writes go to a
temporary file that replaces the original in one step, so an interrupted save
cannot leave a half-written file.

## Layers

| Module | Responsibility | Does not |
| --- | --- | --- |
| `models.py` | Transaction schema and allowed values | Read files, print, validate |
| `validation.py` | Turn raw input into clean values or a clear `ValueError` | Fix ambiguous data silently |
| `services.py` | Pure budget logic: ids, adding, filtering, summaries | Touch files, print or ask for input |
| `storage.py` | Load, save and back up the JSON file | Contain budget rules |
| `cli.py` | Arguments, prompts, output and exit codes | Calculate anything |

Both interfaces (command mode and interactive mode) call the same validation,
services and storage, so a transaction follows the same rules however it is
entered. Services are pure functions, which makes them testable without files.

## Policy decisions

- **Unknown categories are rejected, not mapped to `other`.** Cleaner data at
  the cost of more friction when entering a transaction; the error message lists
  the allowed categories so the user can correct it.
- **Input is normalized, never corrected.** `" Food "` becomes `food` and `eur`
  becomes `EUR`, because there is only one possible meaning. A negative amount
  or an impossible date is rejected, because any correction would be a guess.
- **Amounts are always positive; `kind` gives the sign.** This avoids two ways
  of writing the same expense (`-18.5` as expense vs `18.5` as expense).
- **Invalid records are skipped and reported when loading.** `list` and
  `summary` keep working with the valid records and show a warning for each
  skipped one.
- **Commands that write refuse to run if the file has invalid records.**
  Saving rewrites the whole file from the valid records only, so it would
  silently delete the invalid ones. The user must fix the file first (exit 1).
- **File problems and input problems are different errors.** `StorageError`
  (exit 1) is deliberately not a subclass of `ValueError` (exit 2), because
  `json.JSONDecodeError` is a `ValueError` and a corrupt file would otherwise be
  reported as a user typing mistake.
- **Dates are stored as `YYYY-MM-DD` text, not `datetime.date`.** The model
  matches the JSON file with no conversion, and ISO text sorts and filters by
  month with `startswith`. The cost is that the type itself does not guarantee
  a valid date; only creating transactions through validation does.
- **Ids are generated as the highest existing number + 1**, not the count of
  transactions, so deleting a record can never produce a duplicate id.
- **Validation lives outside the class.** `Transaction` does not validate in
  `__init__`, because `validation.py` imports `models.py` to build transactions
  and the reverse import would be circular. The rule is enforced by design:
  transactions are created only through `parse_record` or `add_transaction`.

## Backup failure policy

- The data file is copied byte for byte with `shutil.copy2`, not rewritten from
  memory, so the backup is identical to what was on disk.
- Each backup is verified (same bytes, readable JSON) before anything else
  happens. If verification fails, the bad copy is removed and the command
  exits with code 1.
- Without a destination, backup names include the timestamp to the second.
  With a destination (`budget backup backup.json`, as in the course example),
  that exact file is used. In both cases an existing file is never overwritten.
- Only after a successful verification are old backups removed, keeping the
  newest 7 by default (`--keep`). The newest backup is never deleted.
- A missing data file is an error (exit 1), not an empty backup.