"""Central configuration. Override the DB location with EXPENSE_DB_PATH."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
DB_PATH = Path(os.getenv("EXPENSE_DB_PATH", DATA_DIR / "expenses.db"))

CURRENCY_SYMBOL = "₹"

DEFAULT_CATEGORIES = [
    "Rent",
    "Groceries",
    "Dining Out",
    "Transport",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Health",
    "Education",
    "Travel",
    "Subscriptions",
]

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Cash", "Net Banking"]
