"""Command-line interface: arguments, prompts, output and exit codes.

This is the only module that talks to the user. It reads input
(argparse or input()), calls services and storage, prints results,
and turns errors into exit codes:
    0 = success, 1 = data file or backup problem, 2 = invalid input.
"""

import argparse
import sys
from pathlib import Path

from budget_manager.models import DEFAULT_CURRENCY
from budget_manager.services import add_transaction, filter_by_month, summarize
from budget_manager.storage import (
    StorageError,
    backup,
    load_transactions,
    save_transactions,
)

# Absolute paths computed from this file, so the program works from any folder
# (cli.py -> budget_manager -> src -> project root).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = PROJECT_ROOT / "data" / "transactions.json"
DEFAULT_BACKUPS = PROJECT_ROOT / "backups"

# Commands that save the file. They refuse to run if the file has invalid
# records, because saving would silently drop them.
WRITE_COMMANDS = {"add", "interactive"}


def build_parser() -> argparse.ArgumentParser:
    """Define the commands and options the program accepts."""
    parser = argparse.ArgumentParser(
        prog="budget",
        description="Record income and expenses, summarize them, and back up the data.",
    )
    parser.add_argument(
        "--data", type=Path, default=DEFAULT_DATA,
        help="path to the transactions JSON file (default: data/transactions.json)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="add one transaction")
    add.add_argument("amount", help="positive amount, e.g. 18.5")
    add.add_argument("--category", required=True, help="e.g. food, transport, salary")
    add.add_argument("--kind", default="expense", help="expense (default) or income")
    add.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    add.add_argument("--currency", default=DEFAULT_CURRENCY, help="default: EUR")

    list_cmd = commands.add_parser("list", help="show transactions")
    list_cmd.add_argument("--month", help="only this month, YYYY-MM")

    summary = commands.add_parser("summary", help="totals and expenses by category")
    summary.add_argument("--month", help="only this month, YYYY-MM")

    backup_cmd = commands.add_parser("backup", help="copy the data file to backups/")
    backup_cmd.add_argument("--keep", type=int, default=7, help="backups to keep (default: 7)")
    backup_cmd.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUPS)

    commands.add_parser("interactive", help="enter several transactions in a session")

    return parser


def print_error(message: str) -> None:
    """Errors and warnings go to stderr, so normal output stays clean."""
    print(f"error: {message}", file=sys.stderr)


def format_transaction(t) -> str:
    """One line for the list command, with the sign coming from kind."""
    return f"{t.id}  {t.date}  {t.kind:<7}  {t.category:<13}  {t.signed_amount:>+10.2f} {t.currency}"


def cmd_add(args, transactions) -> int:
    transactions = add_transaction(
        transactions, args.amount, args.category,
        kind=args.kind, date_text=args.date, currency=args.currency,
    )
    save_transactions(args.data, transactions)
    print(f"Saved {format_transaction(transactions[-1])}")
    return 0


def cmd_list(args, transactions) -> int:
    if args.month:
        transactions = filter_by_month(transactions, args.month)
    if not transactions:
        print("No transactions.")
        return 0
    for t in sorted(transactions, key=lambda t: (t.date, t.id)):
        print(format_transaction(t))
    return 0


def cmd_summary(args, transactions) -> int:
    if args.month:
        transactions = filter_by_month(transactions, args.month)
    result = summarize(transactions)
    title = f"Summary for {args.month}" if args.month else "Summary (all transactions)"
    print(title)
    print(f"  Income:   {result['income']:>10.2f}")
    print(f"  Expenses: {result['expenses']:>10.2f}")
    print(f"  Balance:  {result['balance']:>+10.2f}")
    if result["expenses_by_category"]:
        print("  Expenses by category:")
        for category, total in result["expenses_by_category"].items():
            print(f"    {category:<13} {total:>10.2f}")
    return 0


def cmd_backup(args) -> int:
    destination = backup(args.data, args.backup_dir, keep=args.keep)
    print(f"Backup created: {destination}")
    return 0


def ask(prompt: str) -> str | None:
    """input() that returns None when the user presses Ctrl+D or Ctrl+C."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def run_interactive(args, transactions) -> int:
    """Loop: ask for transactions until the user leaves the amount empty."""
    print("Enter transactions. Leave the amount empty to finish.")
    while True:
        amount = ask("Amount: ")
        if not amount:
            break
        category = ask("Category: ")
        if category is None:
            break
        kind = ask("Kind (expense/income) [expense]: ")
        if kind is None:
            break
        date_text = ask("Date YYYY-MM-DD [today]: ")
        if date_text is None:
            break

        try:
            transactions = add_transaction(
                transactions, amount, category,
                kind=kind or "expense",
                date_text=date_text or None,
            )
        except ValueError as error:
            print_error(f"{error}. Nothing saved, try again.")
            continue

        save_transactions(args.data, transactions)
        print(f"Saved {format_transaction(transactions[-1])}")

    print("Bye.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. argv=None reads the real command line; tests pass a list."""
    args = build_parser().parse_args(argv)

    try:
        # backup copies the file as it is, without loading it.
        if args.command == "backup":
            return cmd_backup(args)

        transactions, errors = load_transactions(args.data)
        for message in errors:
            print(f"warning: skipped {message}", file=sys.stderr)
        if errors and args.command in WRITE_COMMANDS:
            print_error(
                f"{args.data} has {len(errors)} invalid record(s); "
                "fix them before adding, or they would be lost when saving."
            )
            return 1

        if args.command == "add":
            return cmd_add(args, transactions)
        elif args.command == "list":
            return cmd_list(args, transactions)
        elif args.command == "summary":
            return cmd_summary(args, transactions)
        elif args.command == "interactive":
            return run_interactive(args, transactions)

    except StorageError as error:
        print_error(str(error))
        return 1
    except ValueError as error:
        print_error(str(error))
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())