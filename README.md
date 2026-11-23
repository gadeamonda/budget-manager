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

## Two ways to use it

**Interactive mode.** Start a session and enter as many transactions as you
want without restarting the program. Each entry is validated as you type it;
if something is wrong you get the reason and can try again.

```bash
uv run budget interactive
```

**Command mode.** One command per run. This mode suits quick entries, scripts
and scheduled tasks, and it returns an exit code (0 = success, 1 = data or file
error, 2 = invalid input).

```bash
uv run budget add 18.5 --category food
uv run budget list
uv run budget summary --month 2026-09
uv run budget backup
```

Both modes share the same validation, logic and storage, so a transaction
entered either way follows exactly the same rules.

## Data format

Transactions are stored as a JSON list in `data/transactions.json`.
The course template uses CSV; this project uses JSON (see `DESIGN.md` for why).
`data/sample_transactions.json` contains valid and invalid examples.