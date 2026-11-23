# Budget Manager

A command-line personal budget manager. Record income and expenses by category,
store them in a local JSON file, and get summary reports: total expenses,
remaining balance, and a breakdown by category.

Every input is validated before it is saved: amounts must be positive, categories
and currencies must come from an allowed list, and dates must be real ISO dates.
Invalid records are reported with a clear message instead of being silently
accepted or "fixed". A corrupted data file stops the program without touching
your data.

This is the core of a larger project built across the course (Practice 1 of 3):
later practices add a web/API interface and data analysis on top of this same
validated core.

## Installation

Requires [uv](https://docs.astral.sh/uv/). From the project folder:

```bash
uv sync
```

This creates the virtual environment, installs the project and registers the
`budget` command. uv downloads the required Python version if needed.

## Two ways to use it

**Interactive mode.** Start a session and enter as many transactions as you
want without restarting the program. Each entry is validated as you type it;
if something is wrong you get the reason and can try again.

```bash
uv run budget interactive
```

```text
Enter transactions. Leave the amount empty to finish.
Amount: 18.5
Category: food
Kind (expense/income) [expense]:
Date YYYY-MM-DD [today]:
Saved T001  2026-11-23  expense  food               -18.50 EUR
Amount:
Bye.
```

Values in brackets are defaults: press Enter to use them. Leave the amount
empty (or press Ctrl+C) to finish.

**Command mode.** One command per run. This mode suits quick entries, scripts
and scheduled tasks, and it returns an exit code (see below).

```bash
uv run budget add 18.5 --category food
uv run budget add 2500 --category salary --kind income --date 2026-11-01
uv run budget list
uv run budget list --month 2026-11
uv run budget summary
uv run budget summary --month 2026-11
uv run budget backup
uv run budget --help
```

Both modes share the same validation, logic and storage, so a transaction
entered either way follows exactly the same rules.

### Commands

| Command | What it does | Options |
| --- | --- | --- |
| `add AMOUNT --category C` | Adds one transaction | `--kind` (default `expense`), `--date` (default today), `--currency` (default `EUR`) |
| `list` | Shows transactions sorted by date | `--month YYYY-MM` |
| `summary` | Income, expenses, balance and expenses by category | `--month YYYY-MM` |
| `backup` | Copies the data file to `backups/` with a timestamp | `--keep N` (default 7), `--backup-dir` |
| `interactive` | Enters several transactions in one session | |

All commands accept `--data PATH` before the command name to use another data
file, for example to try the program without touching your real data:

```bash
uv run budget --data /tmp/test.json add 10 --category food
```

### Exit codes

| Code | Meaning | Example |
| --- | --- | --- |
| 0 | Success | Transaction saved, list shown |
| 1 | Data file or backup problem | Corrupt JSON, invalid records when adding, nothing to back up |
| 2 | Invalid input | Negative amount, unknown category, impossible date |

Errors and warnings are printed to stderr, so normal output can be redirected
cleanly.

## Validation rules

| Field | Rule | Normalized |
| --- | --- | --- |
| `amount` | Number greater than 0. The sign comes from `kind`. | Text such as `"18.5"` becomes `18.5` |
| `kind` | `expense` or `income` | Lowercase, spaces removed |
| `category` | `salary`, `food`, `transport`, `housing`, `entertainment`, `health`, `other` | Lowercase, spaces removed |
| `currency` | `EUR` only | Uppercase, spaces removed |
| `date` | A real date in exactly `YYYY-MM-DD` format | Spaces removed |
| `id` | `T` followed by digits, generated automatically | Not changed |

Input is normalized, never corrected: `" Food "` is accepted as `food`, but a
negative amount or `2026-13-01` is rejected with a message explaining why.

## Data format

Transactions are stored as a JSON list in `data/transactions.json`. The file
is created on the first `add` and is not tracked by Git (it holds personal
data). The course template uses CSV; this project uses JSON (see `DESIGN.md`
for why).

```json
[
  {
    "id": "T001",
    "date": "2026-09-04",
    "kind": "expense",
    "category": "food",
    "amount": 18.5,
    "currency": "EUR"
  }
]
```

`data/sample_transactions.json` contains valid and invalid examples. Loading it
shows how invalid records are handled:

```bash
uv run budget --data data/sample_transactions.json list
```

Three transactions are listed, and three warnings explain which records were
skipped and why.

**When the data file has problems:**

- **Invalid records** (negative amount, unknown category, duplicate id...) are
  skipped with a warning. `list` and `summary` keep working; `add` and
  `interactive` refuse to save until the file is fixed, because saving would
  drop the invalid records.
- **Invalid JSON** (for example a trailing comma) stops every command with
  exit 1 and the line and column of the problem. The file is never modified.

## Running the tests

```bash
uv run pytest -v
```

Tests use temporary folders and never touch `data/transactions.json`. They
cover validation rules, budget logic, safe saving (including a simulated disk
failure in the middle of a write) and backups.

## Known limitations

- **Amounts use `float`, not `Decimal`.** Totals are rounded to 2 decimals,
  which is enough for a personal budget but not for accounting.
- **Only the first error of each record is reported.** A record with two
  problems shows the second one after the first is fixed.
- **Category and kind are not cross-checked.** `salary` recorded as an
  expense is accepted; remember `--kind income` for income.
- **Future dates are accepted**, so planned transactions can be recorded.
- **No edit or delete command.** Corrections are made by editing the JSON file;
  invalid edits are caught on the next load.
- **One currency (EUR)** and no exchange rates.
- **No locking.** Two programs writing the file at the same moment could lose
  one of the changes. Safe writes prevent half-written files, not concurrent
  updates.

## Project structure

```text
budget-manager/
├── src/budget_manager/
│   ├── models.py       # Transaction schema and allowed values
│   ├── validation.py   # Input rules and error messages
│   ├── services.py     # Budget logic (pure functions)
│   ├── storage.py      # JSON load/save and backups
│   ├── cli.py          # Commands, interactive mode, exit codes
│   └── __main__.py     # Allows `python -m budget_manager`
├── tests/              # pytest tests for validation, services and storage
├── data/
│   └── sample_transactions.json
├── DESIGN.md           # Design decisions and trade-offs
├── AI_DISCLOSURE.md    # How AI assistance was used
└── pyproject.toml
```