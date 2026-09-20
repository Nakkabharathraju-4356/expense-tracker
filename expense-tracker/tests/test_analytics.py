import pandas as pd
import pytest

from expense_tracker import analytics


def test_kpis(sample_df):
    k = analytics.kpis(sample_df)
    assert k["total"] == 5100 and k["transactions"] == 9
    assert k["top_category"] == "Rent" and k["largest"] == 1000


def test_kpis_empty():
    assert (
        analytics.kpis(pd.DataFrame(columns=["expense_date", "amount", "category"]))["total"] == 0.0
    )


def test_monthly_summary_and_mom(sample_df):
    m = analytics.monthly_summary(sample_df)
    assert list(m["month"]) == ["2026-01", "2026-02", "2026-03"]
    assert list(m["total"]) == [1500, 1500, 2100]
    assert m.loc[2, "mom_pct"] == pytest.approx(40.0)


def test_category_breakdown_sums_to_100(sample_df):
    c = analytics.category_breakdown(sample_df)
    assert c["pct_of_total"].sum() == pytest.approx(100, abs=0.1)
    assert c.loc[0, "category"] == "Rent"


def test_budget_vs_actual_status(sample_df):
    budgets = pd.DataFrame(
        {
            "month": ["2026-03"] * 3,
            "category": ["Rent", "Groceries", "Dining Out"],
            "budget": [1000.0, 800.0, 400.0],
        }
    )
    r = analytics.budget_vs_actual(sample_df, budgets, "2026-03").set_index("category")
    assert r.loc["Dining Out", "status"] == "Over budget"  # 600 vs 400
    assert r.loc["Rent", "status"] == "Near limit"  # exactly 100%
    assert r.loc["Groceries", "status"] == "On track"  # 500 vs 800


def test_anomaly_detection_flags_only_the_outlier():
    amounts = [100, 110, 95, 105, 98, 102, 107, 99, 101, 5000]
    df = pd.DataFrame(
        {
            "expense_date": pd.date_range("2026-01-01", periods=10),
            "amount": map(float, amounts),
            "category": "Shopping",
        }
    )
    out = analytics.detect_anomalies(df)
    assert len(out) == 1 and out.loc[0, "amount"] == 5000


def test_anomaly_detection_skips_small_groups():
    df = pd.DataFrame(
        {
            "expense_date": pd.date_range("2026-01-01", periods=3),
            "amount": [10.0, 10.0, 9999.0],
            "category": "Health",
        }
    )
    assert analytics.detect_anomalies(df).empty


def test_savings_summary(sample_df):
    inc = pd.DataFrame(
        {
            "income_date": pd.to_datetime(["2026-01-01", "2026-02-01"]),
            "amount": [3000.0, 3000.0],
            "source": "Salary",
        }
    )
    s = analytics.savings_summary(sample_df, inc).set_index("month")
    assert s.loc["2026-01", "savings"] == 1500
    assert s.loc["2026-01", "savings_rate_pct"] == pytest.approx(50.0)


def test_forecast_linear_trend():
    monthly = pd.DataFrame({"total": [100.0, 200.0, 300.0, 400.0]})
    f = analytics.forecast_next_month(monthly)
    assert f["forecast"] == pytest.approx(500.0)
    assert f["slope_per_month"] == pytest.approx(100.0)


def test_forecast_needs_history():
    assert analytics.forecast_next_month(pd.DataFrame({"total": [1.0, 2.0]}))["forecast"] is None


def test_day_of_week_order(sample_df):
    order = list(analytics.day_of_week_pattern(sample_df)["weekday"])
    assert order == sorted(order, key=analytics.DAY_ORDER.index)
