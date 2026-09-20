"""Command-line interface.  Usage: python -m expense_tracker.cli --help"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

from . import analytics, config
from .database import init_db
from .models import Expense, ValidationError
from .repository import ExpenseRepository
from .seed import seed_database

SYM = config.CURRENCY_SYMBOL


def _money(value: float) -> str:
    return f"{SYM}{value:,.0f}"


def _print_df(df: pd.DataFrame, title: str | None = None) -> None:
    if title:
        print(f"\n== {title} ==")
    print("(no data)" if df.empty else df.to_string(index=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="expense-tracker", description="Personal expense tracker & analytics"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create the database")

    s = sub.add_parser("seed", help="Load realistic sample data")
    s.add_argument("--months", type=int, default=12)
    s.add_argument("--seed", type=int, default=42)

    a = sub.add_parser("add", help="Add an expense")
    a.add_argument("--amount", type=float, required=True)
    a.add_argument("--category", required=True)
    a.add_argument("--date", default=date.today().isoformat())
    a.add_argument("--payment", default="UPI", choices=config.PAYMENT_METHODS)
    a.add_argument("--desc", default="")

    ls = sub.add_parser("list", help="List expenses")
    ls.add_argument("--start", help="YYYY-MM-DD")
    ls.add_argument("--end", help="YYYY-MM-DD")
    ls.add_argument("--category")
    ls.add_argument("--limit", type=int, default=20)

    d = sub.add_parser("delete", help="Delete an expense by id")
    d.add_argument("id", type=int)

    b = sub.add_parser("budget", help="Set a monthly category budget")
    b.add_argument("--category", required=True)
    b.add_argument("--month", required=True, help="YYYY-MM")
    b.add_argument("--amount", type=float, required=True)

    sm = sub.add_parser("summary", help="Spending summary")
    sm.add_argument("--month", help="YYYY-MM for budget status (default: latest month)")

    sub.add_parser("anomalies", help="Unusually large transactions")
    sub.add_parser("forecast", help="Forecast next month's spend")

    e = sub.add_parser("export", help="Export expenses to CSV")
    e.add_argument("--output", default="data/expenses_export.csv")
    return p


def run(args: argparse.Namespace, repo: ExpenseRepository) -> int:
    cmd = args.command

    if cmd == "init":
        init_db(repo.db_path)
        print(f"Database ready at {config.DB_PATH}")

    elif cmd == "seed":
        counts = seed_database(repo, months=args.months, seed=args.seed)
        print(
            f"Seeded {counts['expenses']} expenses, {counts['income']} income records, "
            f"{counts['budgets']} budgets."
        )

    elif cmd == "add":
        init_db(repo.db_path)
        new_id = repo.add_expense(
            Expense.create(args.date, args.amount, args.category, args.payment, args.desc)
        )
        print(f"Added expense #{new_id}: {_money(args.amount)} on {args.category}")

    elif cmd == "list":
        df = repo.expenses_df(args.start, args.end, args.category).head(args.limit)
        _print_df(df.assign(expense_date=df["expense_date"].dt.date))

    elif cmd == "delete":
        print("Deleted." if repo.delete_expense(args.id) else f"No expense with id {args.id}.")

    elif cmd == "budget":
        repo.set_budget(args.category, args.month, args.amount)
        print(f"Budget for {args.category} in {args.month}: {_money(args.amount)}")

    elif cmd == "summary":
        df = repo.expenses_df()
        if df.empty:
            print("No expenses yet. Try: python -m expense_tracker.cli seed")
            return 0
        k = analytics.kpis(df)
        print(
            f"Total spend: {_money(k['total'])} | Transactions: {k['transactions']} | "
            f"Avg/day: {_money(k['avg_daily'])} | Top category: {k['top_category']}"
        )
        _print_df(analytics.monthly_summary(df).tail(6), "Last 6 months")
        _print_df(analytics.category_breakdown(df), "By category")
        month = args.month or analytics.monthly_summary(df)["month"].iloc[-1]
        _print_df(
            analytics.budget_vs_actual(df, repo.budgets_df(), month), f"Budget vs actual ({month})"
        )

    elif cmd == "anomalies":
        an = analytics.detect_anomalies(repo.expenses_df())
        _print_df(an.assign(expense_date=an["expense_date"].dt.date), "Anomalous transactions")

    elif cmd == "forecast":
        monthly = analytics.monthly_summary(repo.expenses_df())
        complete = monthly.iloc[:-1]  # last month is usually partial
        f = analytics.forecast_next_month(complete)
        if f["forecast"] is None:
            print("Need at least 3 complete months of data.")
        else:
            print(
                f"Trend forecast: {_money(f['forecast'])} "
                f"| Trailing avg: {_money(f['trailing_avg'])} "
                f"| Trend: {f['slope_per_month']:+,.0f}/month"
            )

    elif cmd == "export":
        df = repo.expenses_df()
        df.to_csv(args.output, index=False)
        print(f"Exported {len(df)} rows to {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args, ExpenseRepository())
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
