from datetime import date

import pytest

from expense_tracker.models import Expense, ValidationError, parse_date


def test_parse_date_valid():
    assert parse_date("2026-03-01") == date(2026, 3, 1)


@pytest.mark.parametrize("bad", ["01-03-2026", "2026/03/01", "hello", ""])
def test_parse_date_invalid(bad):
    with pytest.raises(ValidationError):
        parse_date(bad)


def test_expense_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        Expense.create("2026-01-01", 0, "Rent")
    with pytest.raises(ValidationError):
        Expense.create("2026-01-01", -10, "Rent")


def test_expense_rejects_bad_payment_method():
    with pytest.raises(ValidationError):
        Expense.create("2026-01-01", 10, "Rent", payment_method="Bitcoin")


def test_expense_trims_whitespace():
    e = Expense.create("2026-01-01", "99.5", "  Groceries  ", description="  milk ")
    assert (e.category, e.description, e.amount) == ("Groceries", "milk", 99.5)
