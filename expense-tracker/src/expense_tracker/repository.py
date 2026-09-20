"""Data-access layer: all SQL for CRUD lives here."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .database import get_connection
from .models import Expense, Income, ValidationError


class ExpenseRepository:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = db_path

    # ---------- helpers ----------
    def _category_id(self, conn, name: str) -> int:
        row = conn.execute(
            "SELECT id FROM categories WHERE lower(name) = lower(?)", (name,)
        ).fetchone()
        if row is None:
            raise ValidationError(f"Unknown category '{name}'.")
        return row["id"]

    # ---------- categories ----------
    def list_categories(self) -> list[str]:
        with get_connection(self.db_path) as conn:
            return [r["name"] for r in conn.execute("SELECT name FROM categories ORDER BY name")]

    def add_category(self, name: str) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name.strip(),))

    # ---------- expenses ----------
    def add_expense(self, exp: Expense) -> int:
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO expenses
                   (expense_date, amount, category_id, payment_method, description)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    exp.expense_date.isoformat(),
                    exp.amount,
                    self._category_id(conn, exp.category),
                    exp.payment_method,
                    exp.description,
                ),
            )
            return cur.lastrowid

    def add_expenses_bulk(self, expenses: list[Expense]) -> int:
        with get_connection(self.db_path) as conn:
            ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}
            conn.executemany(
                """INSERT INTO expenses
                   (expense_date, amount, category_id, payment_method, description)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        e.expense_date.isoformat(),
                        e.amount,
                        ids[e.category],
                        e.payment_method,
                        e.description,
                    )
                    for e in expenses
                ],
            )
        return len(expenses)

    def delete_expense(self, expense_id: int) -> bool:
        with get_connection(self.db_path) as conn:
            cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            return cur.rowcount > 0

    def update_expense(self, expense_id: int, **fields) -> bool:
        allowed = {"expense_date", "amount", "payment_method", "description", "category"}
        bad = set(fields) - allowed
        if bad:
            raise ValidationError(f"Cannot update fields: {sorted(bad)}")
        if "amount" in fields and float(fields["amount"]) <= 0:
            raise ValidationError("Amount must be greater than zero.")
        with get_connection(self.db_path) as conn:
            sets, params = [], []
            for key, val in fields.items():
                if key == "category":
                    sets.append("category_id = ?")
                    params.append(self._category_id(conn, val))
                else:
                    sets.append(f"{key} = ?")
                    params.append(val)
            if not sets:
                return False
            params.append(expense_id)
            cur = conn.execute(f"UPDATE expenses SET {', '.join(sets)} WHERE id = ?", params)
            return cur.rowcount > 0

    def expenses_df(
        self, start: str | None = None, end: str | None = None, category: str | None = None
    ) -> pd.DataFrame:
        query = """
            SELECT e.id, e.expense_date, e.amount, c.name AS category,
                   e.payment_method, e.description
            FROM expenses e JOIN categories c ON c.id = e.category_id
            WHERE 1 = 1"""
        params: list = []
        if start:
            query += " AND e.expense_date >= ?"
            params.append(start)
        if end:
            query += " AND e.expense_date <= ?"
            params.append(end)
        if category:
            query += " AND lower(c.name) = lower(?)"
            params.append(category)
        query += " ORDER BY e.expense_date DESC, e.id DESC"
        with get_connection(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
        df["expense_date"] = pd.to_datetime(df["expense_date"])
        return df

    # ---------- income ----------
    def add_income(self, inc: Income) -> int:
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO income (income_date, amount, source) VALUES (?, ?, ?)",
                (inc.income_date.isoformat(), inc.amount, inc.source),
            )
            return cur.lastrowid

    def income_df(self) -> pd.DataFrame:
        with get_connection(self.db_path) as conn:
            df = pd.read_sql_query(
                "SELECT id, income_date, amount, source FROM income ORDER BY income_date", conn
            )
        df["income_date"] = pd.to_datetime(df["income_date"])
        return df

    # ---------- budgets ----------
    def set_budget(self, category: str, month: str, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Budget must be greater than zero.")
        with get_connection(self.db_path) as conn:
            conn.execute(
                """INSERT INTO budgets (category_id, month, amount) VALUES (?, ?, ?)
                   ON CONFLICT(category_id, month) DO UPDATE SET amount = excluded.amount""",
                (self._category_id(conn, category), month, amount),
            )

    def budgets_df(self) -> pd.DataFrame:
        with get_connection(self.db_path) as conn:
            return pd.read_sql_query(
                """SELECT b.month, c.name AS category, b.amount AS budget
                   FROM budgets b JOIN categories c ON c.id = b.category_id
                   ORDER BY b.month, c.name""",
                conn,
            )
