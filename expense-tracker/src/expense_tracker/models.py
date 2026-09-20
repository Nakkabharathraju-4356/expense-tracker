"""Domain models with validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from . import config


class ValidationError(ValueError):
    """Raised when user input fails validation."""


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc


@dataclass(frozen=True)
class Expense:
    expense_date: date
    amount: float
    category: str
    payment_method: str = "UPI"
    description: str = ""

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        if not self.category.strip():
            raise ValidationError("Category is required.")
        if self.payment_method not in config.PAYMENT_METHODS:
            raise ValidationError(f"Payment method must be one of {config.PAYMENT_METHODS}.")

    @classmethod
    def create(cls, expense_date, amount, category, payment_method="UPI", description=""):
        return cls(
            parse_date(expense_date),
            float(amount),
            category.strip(),
            payment_method,
            description.strip(),
        )


@dataclass(frozen=True)
class Income:
    income_date: date
    amount: float
    source: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
