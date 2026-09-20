"""Generate realistic, reproducible sample data (INR) so the project works out of the box."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

import numpy as np

from .models import Expense, Income
from .repository import ExpenseRepository

# category -> (transactions/month range, amount range, payment methods, descriptions)
VARIABLE_SPEC = {
    "Groceries": (
        (8, 12),
        (250, 1800),
        ["UPI", "Debit Card", "Credit Card"],
        ["BigBasket", "Blinkit", "D-Mart", "Local vegetable market"],
    ),
    "Dining Out": (
        (6, 11),
        (250, 1600),
        ["UPI", "Credit Card"],
        ["Swiggy", "Zomato", "Restaurant dinner", "Cafe"],
    ),
    "Transport": (
        (14, 22),
        (50, 650),
        ["UPI", "Cash", "Debit Card"],
        ["Uber", "Ola", "Metro card recharge", "Petrol", "Auto"],
    ),
    "Entertainment": (
        (2, 5),
        (200, 1200),
        ["UPI", "Credit Card"],
        ["Movie tickets", "Concert", "Gaming", "Bowling"],
    ),
    "Shopping": (
        (2, 5),
        (500, 4000),
        ["Credit Card", "UPI"],
        ["Amazon", "Myntra", "Flipkart", "Electronics"],
    ),
    "Health": (
        (0, 2),
        (300, 2500),
        ["UPI", "Debit Card"],
        ["Pharmacy", "Doctor consultation", "Lab tests"],
    ),
    "Education": (
        (0, 1),
        (1500, 6000),
        ["Net Banking", "Credit Card"],
        ["Online course", "Books", "Certification exam"],
    ),
    "Travel": (
        (0, 1),
        (3000, 15000),
        ["Credit Card", "Net Banking"],
        ["Flight tickets", "Train tickets", "Hotel booking"],
    ),
}

# Multipliers to build in seasonality (month number -> factor)
SEASONALITY = {
    "Shopping": {10: 1.6, 11: 1.6, 1: 1.3, 6: 1.3},
    "Travel": {5: 1.8, 12: 1.8},
}
ELECTRICITY_SUMMER = {4: 1.6, 5: 1.7, 6: 1.3}

MONTHLY_BUDGETS = {
    "Rent": 24000,
    "Groceries": 11000,
    "Dining Out": 9000,
    "Transport": 6500,
    "Utilities": 3500,
    "Entertainment": 3000,
    "Shopping": 9000,
    "Health": 3000,
    "Education": 3000,
    "Travel": 6000,
    "Subscriptions": 1000,
}

ANOMALIES = [
    ("Health", "Emergency dental surgery", 24500, "Credit Card"),
    ("Shopping", "Laptop screen replacement", 31000, "Credit Card"),
    ("Dining Out", "Team dinner - office party", 9800, "Credit Card"),
]


def _month_starts(end: date, months: int) -> list[date]:
    starts, y, m = [], end.year, end.month
    for _ in range(months):
        starts.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return starts[::-1]


def _random_day(rng, month_start: date, end: date) -> date:
    last = min(
        calendar.monthrange(month_start.year, month_start.month)[1], (end - month_start).days + 1
    )
    return month_start + timedelta(days=int(rng.integers(0, max(last, 1))))


def generate(months: int = 12, end: date | None = None, seed: int = 42):
    """Return (expenses, income, budgets) generated deterministically from `seed`."""
    rng = np.random.default_rng(seed)
    end = end or date.today()
    expenses: list[Expense] = []
    income: list[Income] = []
    budgets: list[tuple[str, str, float]] = []
    starts = _month_starts(end, months)

    anomaly_slots = {}
    if months > 4:
        slots = rng.choice(np.arange(1, months - 1), size=min(3, months - 2), replace=False)
        anomaly_slots = {int(s): ANOMALIES[i] for i, s in enumerate(slots)}

    for idx, ms in enumerate(starts):
        key = f"{ms.year}-{ms.month:02d}"

        # ---- fixed recurring items ----
        rent = 22000 if idx < months // 2 else 24000  # rent hike halfway through
        fixed = [
            (1 + int(rng.integers(0, 4)), "Rent", rent, "Net Banking", "Monthly rent"),
            (8, "Utilities", 999, "UPI", "Broadband"),
            (12, "Utilities", 399, "UPI", "Mobile recharge"),
            (15, "Subscriptions", 649, "Credit Card", "Netflix"),
            (18, "Subscriptions", 119, "Credit Card", "Spotify"),
        ]
        for day, cat, amt, pay, desc in fixed:
            d = ms + timedelta(days=day - 1)
            if d <= end:
                expenses.append(Expense(d, float(amt), cat, pay, desc))

        # electricity bill with summer peak
        d = ms + timedelta(days=9)
        if d <= end:
            base = rng.uniform(1100, 1800) * ELECTRICITY_SUMMER.get(ms.month, 1.0)
            expenses.append(Expense(d, round(float(base)), "Utilities", "UPI", "Electricity bill"))

        # ---- variable spend ----
        for cat, ((lo_n, hi_n), (lo_a, hi_a), pays, descs) in VARIABLE_SPEC.items():
            factor = SEASONALITY.get(cat, {}).get(ms.month, 1.0)
            n = int(round(rng.integers(lo_n, hi_n + 1) * (factor if cat == "Travel" else 1)))
            for _ in range(n):
                day = _random_day(rng, ms, end)
                if cat == "Dining Out" and rng.random() < 0.55:  # weekend bias
                    day += timedelta(days=(5 - day.weekday()) % 7)
                    day = min(day, end)
                amt = round(float(rng.uniform(lo_a, hi_a) * (factor if cat == "Shopping" else 1)))
                expenses.append(
                    Expense(day, float(amt), cat, str(rng.choice(pays)), str(rng.choice(descs)))
                )

        # ---- injected anomalies ----
        if idx in anomaly_slots:
            cat, desc, amt, pay = anomaly_slots[idx]
            expenses.append(Expense(_random_day(rng, ms, end), float(amt), cat, pay, desc))

        # ---- income ----
        salary = 105000 if idx < months // 2 else 115000
        income.append(Income(ms, float(salary), "Salary"))
        if ms.month == 3:
            income.append(Income(ms + timedelta(days=14), 40000.0, "Annual bonus"))
        if rng.random() < 0.3:
            side = _random_day(rng, ms, end)
            income.append(Income(side, float(round(rng.uniform(6000, 18000))), "Freelance"))

        budgets += [(c, key, float(a)) for c, a in MONTHLY_BUDGETS.items()]

    return expenses, income, budgets


def seed_database(
    repo: ExpenseRepository,
    months: int = 12,
    seed: int = 42,
    end: date | None = None,
    reset: bool = True,
) -> dict:
    """Populate the database with generated data."""
    from .database import get_connection, init_db

    init_db(repo.db_path)
    if reset:
        with get_connection(repo.db_path) as conn:
            for table in ("expenses", "income", "budgets"):
                conn.execute(f"DELETE FROM {table}")
    expenses, income, budgets = generate(months, end, seed)
    repo.add_expenses_bulk(expenses)
    for inc in income:
        repo.add_income(inc)
    for cat, month, amt in budgets:
        repo.set_budget(cat, month, amt)
    return {"expenses": len(expenses), "income": len(income), "budgets": len(budgets)}
