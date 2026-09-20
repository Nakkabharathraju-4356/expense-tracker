import pytest

from expense_tracker.models import Expense, Income, ValidationError


def _add(repo, d="2026-01-10", amt=100.0, cat="Groceries", pay="UPI", desc=""):
    return repo.add_expense(Expense.create(d, amt, cat, pay, desc))


def test_default_categories_are_seeded(repo):
    cats = repo.list_categories()
    assert "Rent" in cats and "Groceries" in cats


def test_add_and_read_back(repo):
    _add(repo, amt=250.0, desc="milk")
    df = repo.expenses_df()
    assert len(df) == 1
    assert df.loc[0, "amount"] == 250.0 and df.loc[0, "category"] == "Groceries"


def test_category_lookup_is_case_insensitive(repo):
    _add(repo, cat="groceries")
    assert repo.expenses_df().loc[0, "category"] == "Groceries"


def test_unknown_category_rejected(repo):
    with pytest.raises(ValidationError):
        _add(repo, cat="Nonexistent")


def test_filters(repo):
    _add(repo, d="2026-01-10", cat="Groceries")
    _add(repo, d="2026-02-10", cat="Rent")
    assert len(repo.expenses_df(start="2026-02-01")) == 1
    assert len(repo.expenses_df(end="2026-01-31")) == 1
    assert len(repo.expenses_df(category="rent")) == 1


def test_delete(repo):
    new_id = _add(repo)
    assert repo.delete_expense(new_id) is True
    assert repo.delete_expense(new_id) is False
    assert repo.expenses_df().empty


def test_update(repo):
    new_id = _add(repo, amt=100.0)
    assert repo.update_expense(new_id, amount=175.0, category="Rent")
    row = repo.expenses_df().iloc[0]
    assert row["amount"] == 175.0 and row["category"] == "Rent"


def test_update_rejects_bad_input(repo):
    new_id = _add(repo)
    with pytest.raises(ValidationError):
        repo.update_expense(new_id, amount=-1)
    with pytest.raises(ValidationError):
        repo.update_expense(new_id, id=99)


def test_budget_upsert(repo):
    repo.set_budget("Groceries", "2026-01", 5000)
    repo.set_budget("Groceries", "2026-01", 6000)  # should overwrite, not duplicate
    b = repo.budgets_df()
    assert len(b) == 1 and b.loc[0, "budget"] == 6000


def test_income_roundtrip(repo):
    repo.add_income(Income(__import__("datetime").date(2026, 1, 1), 50000.0, "Salary"))
    assert repo.income_df().loc[0, "amount"] == 50000.0


def test_bulk_insert(repo):
    exps = [Expense.create("2026-01-01", 10 * i, "Groceries") for i in range(1, 6)]
    assert repo.add_expenses_bulk(exps) == 5
    assert len(repo.expenses_df()) == 5
