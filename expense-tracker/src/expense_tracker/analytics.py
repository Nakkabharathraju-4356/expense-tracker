"""Pure-pandas analytics. No database access here, so everything is easy to unit test."""

from __future__ import annotations

import numpy as np
import pandas as pd

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _with_month(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(month=df["expense_date"].dt.to_period("M").astype(str))


def kpis(df: pd.DataFrame) -> dict:
    """Headline numbers for a set of expenses."""
    if df.empty:
        return {
            "total": 0.0,
            "transactions": 0,
            "avg_transaction": 0.0,
            "avg_daily": 0.0,
            "top_category": None,
            "largest": 0.0,
        }
    days = (df["expense_date"].max() - df["expense_date"].min()).days + 1
    by_cat = df.groupby("category")["amount"].sum()
    return {
        "total": float(df["amount"].sum()),
        "transactions": int(len(df)),
        "avg_transaction": float(df["amount"].mean()),
        "avg_daily": float(df["amount"].sum() / max(days, 1)),
        "top_category": by_cat.idxmax(),
        "largest": float(df["amount"].max()),
    }


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total spend, transaction count and month-over-month % change."""
    if df.empty:
        return pd.DataFrame(
            columns=["month", "total", "transactions", "avg_transaction", "mom_pct"]
        )
    out = (
        _with_month(df)
        .groupby("month", as_index=False)
        .agg(
            total=("amount", "sum"),
            transactions=("amount", "count"),
            avg_transaction=("amount", "mean"),
        )
        .sort_values("month")
        .reset_index(drop=True)
    )
    out["mom_pct"] = out["total"].pct_change() * 100
    return out.round(2)


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Spend per category with share of total, sorted descending."""
    if df.empty:
        return pd.DataFrame(columns=["category", "total", "transactions", "pct_of_total"])
    out = (
        df.groupby("category", as_index=False)
        .agg(total=("amount", "sum"), transactions=("amount", "count"))
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    out["pct_of_total"] = out["total"] / out["total"].sum() * 100
    return out.round(2)


def payment_method_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("payment_method", as_index=False)
        .agg(total=("amount", "sum"), transactions=("amount", "count"))
        .sort_values("total", ascending=False)
        .reset_index(drop=True)
    )
    return out.round(2)


def day_of_week_pattern(df: pd.DataFrame) -> pd.DataFrame:
    """Average spend per calendar day for each weekday (reveals weekend behaviour)."""
    if df.empty:
        return pd.DataFrame(columns=["weekday", "avg_daily_spend"])
    daily = df.groupby(df["expense_date"].dt.normalize())["amount"].sum().reset_index()
    daily["weekday"] = daily["expense_date"].dt.day_name()
    out = (
        daily.groupby("weekday", as_index=False)["amount"]
        .mean()
        .rename(columns={"amount": "avg_daily_spend"})
    )
    out["weekday"] = pd.Categorical(out["weekday"], categories=DAY_ORDER, ordered=True)
    return out.sort_values("weekday").reset_index(drop=True).round(2)


def category_month_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot: rows = category, columns = month (for heatmaps)."""
    return (
        _with_month(df)
        .pivot_table(
            index="category", columns="month", values="amount", aggfunc="sum", fill_value=0
        )
        .round(2)
    )


def budget_vs_actual(expenses: pd.DataFrame, budgets: pd.DataFrame, month: str) -> pd.DataFrame:
    """Compare a month's spend against budgets, with utilisation and status flag."""
    actual = (
        _with_month(expenses)
        .query("month == @month")
        .groupby("category", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "actual"})
    )
    bud = budgets.query("month == @month")[["category", "budget"]]
    out = bud.merge(actual, on="category", how="outer").fillna({"actual": 0.0})
    out["budget"] = out["budget"].astype(float)
    out["remaining"] = out["budget"] - out["actual"]
    out["utilisation_pct"] = np.where(
        out["budget"] > 0, out["actual"] / out["budget"] * 100, np.nan
    )
    out["status"] = np.select(
        [out["budget"].isna(), out["actual"] > out["budget"], out["utilisation_pct"] >= 90],
        ["No budget", "Over budget", "Near limit"],
        default="On track",
    )
    return (
        out.sort_values("utilisation_pct", ascending=False, na_position="last")
        .round(2)
        .reset_index(drop=True)
    )


def detect_anomalies(df: pd.DataFrame, threshold: float = 3.5, min_group: int = 8) -> pd.DataFrame:
    """Flag unusually large transactions using a robust per-category score.

    Uses the modified z-score (Iglewicz & Hoaglin): 0.6745 * (x - median) / MAD.
    Median/MAD are not distorted by the outliers themselves (unlike mean/std), and
    a score above 3.5 is the standard cut-off. Only *high* outliers are flagged, and
    categories with fewer than `min_group` records are skipped.
    """
    if df.empty:
        return df.assign(score=[])
    grp = df.groupby("category")["amount"]
    median = grp.transform("median")
    mad = (df["amount"] - median).abs().groupby(df["category"]).transform("median")
    cnt = grp.transform("count")
    score = 0.6745 * (df["amount"] - median) / mad.replace(0, np.nan)
    flagged = df.assign(score=score.round(2))[(score > threshold) & (cnt >= min_group)]
    return flagged.sort_values("score", ascending=False).reset_index(drop=True)


def savings_summary(expenses: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    """Monthly income vs expense with savings and savings rate."""
    exp_m = _with_month(expenses).groupby("month")["amount"].sum().rename("expense")
    inc = income.assign(month=income["income_date"].dt.to_period("M").astype(str))
    inc_m = inc.groupby("month")["amount"].sum().rename("income")
    out = (
        pd.concat([inc_m, exp_m], axis=1).fillna(0).reset_index().rename(columns={"index": "month"})
    )
    out["savings"] = out["income"] - out["expense"]
    out["savings_rate_pct"] = np.where(
        out["income"] > 0, out["savings"] / out["income"] * 100, np.nan
    )
    return out.sort_values("month").round(2).reset_index(drop=True)


def forecast_next_month(monthly: pd.DataFrame, window: int = 6) -> dict:
    """Forecast next month's spend with a linear trend over the last `window` COMPLETE months.

    Returns the trend forecast plus a simple trailing average for comparison.
    """
    if len(monthly) < 3:
        return {"forecast": None, "trailing_avg": None, "slope_per_month": None}
    recent = monthly.tail(window)
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent["total"].to_numpy(), 1)
    return {
        "forecast": float(max(slope * len(recent) + intercept, 0)),
        "trailing_avg": float(recent["total"].mean()),
        "slope_per_month": float(slope),
    }
