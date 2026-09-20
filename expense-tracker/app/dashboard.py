"""Streamlit dashboard.  Run:  streamlit run app/dashboard.py"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Allow running without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.express as px
import streamlit as st

from expense_tracker import analytics, config
from expense_tracker.database import init_db
from expense_tracker.models import Expense, ValidationError
from expense_tracker.repository import ExpenseRepository
from expense_tracker.seed import seed_database

SYM = config.CURRENCY_SYMBOL
PALETTE = px.colors.qualitative.Set2

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")


def money(v: float) -> str:
    return f"{SYM}{v:,.0f}"


@st.cache_resource
def get_repo() -> ExpenseRepository:
    init_db()
    return ExpenseRepository()


repo = get_repo()
all_expenses = repo.expenses_df()

# ---------------------------------------------------------------- empty state
if all_expenses.empty:
    st.title("💰 Expense Tracker")
    st.info("No data yet. Load 12 months of realistic sample data to explore the dashboard.")
    if st.button("Load sample data", type="primary"):
        seed_database(repo)
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Filters")
min_d, max_d = all_expenses["expense_date"].min().date(), all_expenses["expense_date"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_d, max_d
categories = repo.list_categories()
picked = st.sidebar.multiselect("Categories", categories, default=categories)

st.sidebar.divider()
st.sidebar.header("Add expense")
with st.sidebar.form("add_expense", clear_on_submit=True):
    f_date = st.date_input("Date", date.today())
    f_amount = st.number_input(f"Amount ({SYM})", min_value=0.0, step=50.0)
    f_cat = st.selectbox("Category", categories)
    f_pay = st.selectbox("Payment method", config.PAYMENT_METHODS)
    f_desc = st.text_input("Description")
    if st.form_submit_button("Add", type="primary"):
        try:
            repo.add_expense(Expense.create(f_date, f_amount, f_cat, f_pay, f_desc))
            st.success("Expense added.")
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))

# ---------------------------------------------------------------- filtered data
mask = (
    (all_expenses["expense_date"].dt.date >= start)
    & (all_expenses["expense_date"].dt.date <= end)
    & (all_expenses["category"].isin(picked))
)
df = all_expenses[mask]

st.title("💰 Expense Tracker")
st.caption(f"{start:%d %b %Y} → {end:%d %b %Y} · {len(df):,} transactions")

if df.empty:
    st.warning("No expenses match the current filters.")
    st.stop()

# ---------------------------------------------------------------- KPIs
k = analytics.kpis(df)
monthly = analytics.monthly_summary(df)
savings = analytics.savings_summary(all_expenses, repo.income_df())
complete_savings = savings.iloc[:-1] if len(savings) > 1 else savings  # skip partial current month

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total spend", money(k["total"]))
c2.metric("Avg per day", money(k["avg_daily"]))
c3.metric("Avg transaction", money(k["avg_transaction"]))
c4.metric("Top category", k["top_category"])
if not complete_savings.empty:
    c5.metric(
        "Savings rate (last full month)", f"{complete_savings['savings_rate_pct'].iloc[-1]:.0f}%"
    )

tab_overview, tab_budget, tab_insights, tab_data = st.tabs(
    ["📈 Overview", "🎯 Budget", "🔎 Insights", "🗂️ Data"]
)

# ---------------------------------------------------------------- Overview
with tab_overview:
    left, right = st.columns([3, 2])
    fig = px.bar(
        monthly,
        x="month",
        y="total",
        text_auto=".2s",
        title="Monthly spend",
        color_discrete_sequence=[PALETTE[0]],
    )
    fig.update_layout(xaxis_title=None, yaxis_title=f"Spend ({SYM})")
    left.plotly_chart(fig, width="stretch")

    cat = analytics.category_breakdown(df)
    fig = px.pie(
        cat,
        names="category",
        values="total",
        hole=0.5,
        title="Spend by category",
        color_discrete_sequence=PALETTE,
    )
    right.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    dow = analytics.day_of_week_pattern(df)
    fig = px.bar(
        dow,
        x="weekday",
        y="avg_daily_spend",
        title="Average spend by weekday",
        color_discrete_sequence=[PALETTE[1]],
    )
    fig.update_layout(xaxis_title=None, yaxis_title=f"Avg daily spend ({SYM})")
    left.plotly_chart(fig, width="stretch")

    pay = analytics.payment_method_breakdown(df)
    fig = px.bar(
        pay,
        x="total",
        y="payment_method",
        orientation="h",
        title="Payment methods",
        color_discrete_sequence=[PALETTE[2]],
    )
    fig.update_layout(
        yaxis_title=None, xaxis_title=f"Spend ({SYM})", yaxis={"categoryorder": "total ascending"}
    )
    right.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- Budget
with tab_budget:
    months = sorted(
        all_expenses["expense_date"].dt.to_period("M").astype(str).unique(), reverse=True
    )
    month = st.selectbox("Month", months)
    bva = analytics.budget_vs_actual(all_expenses, repo.budgets_df(), month)
    if bva.empty:
        st.info("No budgets set for this month.")
    else:
        over = int((bva["status"] == "Over budget").sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Total budget", money(bva["budget"].sum()))
        m2.metric(
            "Actual spend",
            money(bva["actual"].sum()),
            delta=money(bva["actual"].sum() - bva["budget"].sum()),
            delta_color="inverse",
        )
        m3.metric("Categories over budget", over)

        long = bva.melt(
            id_vars="category",
            value_vars=["budget", "actual"],
            var_name="type",
            value_name="amount",
        )
        fig = px.bar(
            long,
            x="category",
            y="amount",
            color="type",
            barmode="group",
            title=f"Budget vs actual · {month}",
            color_discrete_sequence=[PALETTE[2], PALETTE[1]],
        )
        fig.update_layout(xaxis_title=None, yaxis_title=f"Amount ({SYM})")
        st.plotly_chart(fig, width="stretch")

        def colour(val: str) -> str:
            return {
                "Over budget": "background-color:#f8d7da",
                "Near limit": "background-color:#fff3cd",
                "On track": "background-color:#d4edda",
            }.get(val, "")

        st.dataframe(
            bva.style.map(colour, subset=["status"]).format(
                {
                    "budget": "{:,.0f}",
                    "actual": "{:,.0f}",
                    "remaining": "{:,.0f}",
                    "utilisation_pct": "{:.0f}%",
                }
            ),
            width="stretch",
            hide_index=True,
        )

# ---------------------------------------------------------------- Insights
with tab_insights:
    left, right = st.columns(2)

    with left:
        st.subheader("Income vs expenses")
        if savings.empty:
            st.info("Add income records to see savings analysis.")
        else:
            long = savings.melt(
                id_vars="month",
                value_vars=["income", "expense"],
                var_name="type",
                value_name="amount",
            )
            fig = px.bar(
                long,
                x="month",
                y="amount",
                color="type",
                barmode="group",
                color_discrete_sequence=[PALETTE[0], PALETTE[1]],
            )
            fig.update_layout(xaxis_title=None, yaxis_title=f"Amount ({SYM})", legend_title=None)
            st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Next-month forecast")
        complete = analytics.monthly_summary(all_expenses).iloc[:-1]
        fc = analytics.forecast_next_month(complete)
        if fc["forecast"] is None:
            st.info("Need at least 3 complete months of data.")
        else:
            a, b = st.columns(2)
            a.metric("Trend forecast", money(fc["forecast"]))
            b.metric("6-month average", money(fc["trailing_avg"]))
            direction = "rising" if fc["slope_per_month"] > 0 else "falling"
            st.caption(
                f"Spending is {direction} by about {money(abs(fc['slope_per_month']))} per month "
                "(linear trend over the last 6 complete months)."
            )

    st.subheader("Category × month heatmap")
    matrix = analytics.category_month_matrix(df)
    fig = px.imshow(
        matrix, aspect="auto", color_continuous_scale="Blues", labels={"color": f"Spend ({SYM})"}
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, width="stretch")

    st.subheader("⚠️ Unusual transactions")
    st.caption("Flagged with a robust modified z-score (median/MAD) per category; score > 3.5.")
    anomalies = analytics.detect_anomalies(df)
    if anomalies.empty:
        st.success("No unusual transactions detected.")
    else:
        st.dataframe(
            anomalies.assign(expense_date=anomalies["expense_date"].dt.date).drop(columns=["id"]),
            width="stretch",
            hide_index=True,
        )

# ---------------------------------------------------------------- Data
with tab_data:
    view = df.assign(expense_date=df["expense_date"].dt.date)
    st.dataframe(view, width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download CSV",
        view.to_csv(index=False).encode(),
        file_name="expenses.csv",
        mime="text/csv",
    )
