from datetime import date

from expense_tracker import analytics
from expense_tracker.cli import build_parser, run
from expense_tracker.seed import generate, seed_database

END = date(2026, 6, 30)


def test_generation_is_reproducible():
    a, *_ = generate(months=6, end=END, seed=7)
    b, *_ = generate(months=6, end=END, seed=7)
    assert [(e.expense_date, e.amount, e.category) for e in a] == [
        (e.expense_date, e.amount, e.category) for e in b
    ]


def test_generated_data_respects_end_date_and_is_valid():
    exps, income, budgets = generate(months=6, end=END, seed=1)
    assert max(e.expense_date for e in exps) <= END
    assert all(e.amount > 0 for e in exps)
    assert len(income) >= 6 and len(budgets) == 6 * 11


def test_seeded_db_surfaces_injected_anomalies(repo):
    seed_database(repo, months=12, end=END, seed=42)
    flagged = analytics.detect_anomalies(repo.expenses_df())
    descriptions = " ".join(flagged["description"])
    assert "dental" in descriptions.lower() or "laptop" in descriptions.lower()


def test_cli_add_list_delete_roundtrip(repo, capsys):
    p = build_parser()
    run(
        p.parse_args(["add", "--amount", "120", "--category", "Groceries", "--date", "2026-01-02"]),
        repo,
    )
    assert len(repo.expenses_df()) == 1
    run(p.parse_args(["delete", "1"]), repo)
    assert repo.expenses_df().empty


def test_cli_summary_on_seeded_db(repo, capsys):
    seed_database(repo, months=6, end=END)
    assert run(build_parser().parse_args(["summary"]), repo) == 0
    out = capsys.readouterr().out
    assert "Total spend" in out and "Budget vs actual" in out
