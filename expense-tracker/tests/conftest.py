import pandas as pd
import pytest

from expense_tracker.database import init_db
from expense_tracker.repository import ExpenseRepository


@pytest.fixture()
def repo(tmp_path):
    """A repository backed by a throw-away SQLite file."""
    db = tmp_path / "test.db"
    init_db(db)
    return ExpenseRepository(db)


@pytest.fixture()
def sample_df():
    """Small, hand-checkable expenses frame."""
    rows = [
        ("2026-01-05", 1000, "Rent"),
        ("2026-01-10", 200, "Groceries"),
        ("2026-01-20", 300, "Groceries"),
        ("2026-02-05", 1000, "Rent"),
        ("2026-02-11", 400, "Groceries"),
        ("2026-02-14", 100, "Dining Out"),
        ("2026-03-05", 1000, "Rent"),
        ("2026-03-09", 500, "Groceries"),
        ("2026-03-15", 600, "Dining Out"),
    ]
    df = pd.DataFrame(rows, columns=["expense_date", "amount", "category"])
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["amount"] = df["amount"].astype(float)
    df["payment_method"] = "UPI"
    return df
