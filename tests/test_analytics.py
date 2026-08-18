from datetime import date

import pandas as pd
import pytest

import analytics
import db
from analytics import (
    apply_filters,
    calculate_financial_health,
    category_summary,
    check_category_budgets,
    csv_template,
    detect_anomalies,
    detect_duplicates,
    enrich_expenses,
    merchant_summary,
    month_forecast,
    monthly_series,
    savings_progress,
    streak_metrics,
    weekday_summary,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _row(id, iso_date, amount, category, note="", currency="EUR", subscription=0, tx_type="expense"):
    return {
        "id": id,
        "user_id": "u1",
        "date": iso_date,
        "amount": amount,
        "category": category,
        "currency": currency,
        "subscription": subscription,
        "note": note,
        "type": tx_type,
    }


def _enriched(rows, display_currency="EUR"):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return enrich_expenses(df, display_currency)


class _FixedDate(date):
    """Drop-in replacement for datetime.date with a frozen .today()."""

    _frozen = date(2026, 3, 20)

    @classmethod
    def today(cls):
        return cls._frozen


@pytest.fixture
def freeze_today(monkeypatch):
    monkeypatch.setattr(analytics, "date", _FixedDate)
    return _FixedDate.today()


# ---------------------------------------------------------------------------
# enrich_expenses
# ---------------------------------------------------------------------------

def test_enrich_expenses_empty_df_returns_empty():
    empty = pd.DataFrame(columns=["id", "user_id", "date", "amount", "category", "currency", "subscription", "note", "type"])
    out = enrich_expenses(empty, "EUR")
    assert out.empty


def test_enrich_expenses_computes_expected_columns():
    df = _enriched([_row(1, "2026-03-17", 12.5, "Cafe", note="coffee at starbucks")])
    row = df.iloc[0]
    ts = pd.Timestamp("2026-03-17")
    assert row["display_amount"] == 12.5
    assert row["display_abs_amount"] == 12.5
    assert row["date_only"] == ts.date()
    assert row["month"] == "2026-03"
    assert row["year"] == 2026
    assert row["day"] == 17
    assert row["weekday"] == ts.day_name()
    assert row["merchant"]  # extract_merchant should produce something non-empty


def test_enrich_expenses_display_amount_is_absolute_for_income_rows():
    df = _enriched([_row(1, "2026-03-01", -2500.0, "Salary", tx_type="income")])
    row = df.iloc[0]
    assert row["display_amount"] == -2500.0
    assert row["display_abs_amount"] == 2500.0


def test_enrich_expenses_converts_to_a_non_eur_display_currency(monkeypatch):
    # Amounts are stored in EUR; converting to a display currency goes through
    # db.get_rates_map, which normally calls out to Frankfurter/NBU. Stub it
    # so the test is deterministic and doesn't touch the network.
    monkeypatch.setattr(db, "get_rates_map", lambda base="EUR": {"EUR": 1.0, "USD": 1.1})
    df = _enriched([_row(1, "2026-03-01", 10.0, "Food", currency="EUR")], display_currency="USD")
    row = df.iloc[0]
    assert row["display_amount"] == pytest.approx(11.0)


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    return _enriched(
        [
            _row(1, "2026-03-01", 50.0, "Food", note="groceries"),
            _row(2, "2026-03-05", 20.0, "Cafe", note="coffee"),
            _row(3, "2026-03-10", 15.0, "Cafe", note="coffee", subscription=1),
            _row(4, "2026-02-20", 30.0, "Food", note="groceries"),
        ]
    )


def test_apply_filters_by_date_range(sample_df):
    out = apply_filters(sample_df, date(2026, 3, 1), date(2026, 3, 31), [], "", False)
    assert set(out["id"]) == {1, 2, 3}


def test_apply_filters_by_category(sample_df):
    out = apply_filters(sample_df, date(2026, 1, 1), date(2026, 12, 31), ["Cafe"], "", False)
    assert set(out["id"]) == {2, 3}


def test_apply_filters_by_text_query_matches_note(sample_df):
    out = apply_filters(sample_df, date(2026, 1, 1), date(2026, 12, 31), [], "grocer", False)
    assert set(out["id"]) == {1, 4}


def test_apply_filters_subscriptions_only(sample_df):
    out = apply_filters(sample_df, date(2026, 1, 1), date(2026, 12, 31), [], "", True)
    assert set(out["id"]) == {3}


def test_apply_filters_empty_df_returns_empty():
    empty = pd.DataFrame(columns=["date", "category", "note", "merchant", "subscription"])
    out = apply_filters(empty, date(2026, 1, 1), date(2026, 12, 31), [], "", False)
    assert out.empty


# ---------------------------------------------------------------------------
# aggregation helpers
# ---------------------------------------------------------------------------

def test_monthly_series_sums_per_month():
    df = _enriched(
        [
            _row(1, "2026-03-01", 10.0, "Food"),
            _row(2, "2026-03-05", 5.0, "Food"),
            _row(3, "2026-02-20", 7.0, "Food"),
        ]
    )
    out = monthly_series(df).set_index("month")["display_amount"]
    assert out["2026-03"] == 15.0
    assert out["2026-02"] == 7.0


def test_category_summary_sorts_descending():
    df = _enriched(
        [
            _row(1, "2026-03-01", 10.0, "Food"),
            _row(2, "2026-03-05", 50.0, "Rent"),
            _row(3, "2026-03-06", 5.0, "Cafe"),
        ]
    )
    out = category_summary(df)
    assert out.iloc[0]["category"] == "Rent"
    assert list(out["category"]) == ["Rent", "Food", "Cafe"]


def test_weekday_summary_empty_df_returns_all_seven_days_zeroed():
    empty = pd.DataFrame(columns=["weekday", "display_amount"])
    out = weekday_summary(empty)
    assert len(out) == 7
    assert set(out["weekday"]) == {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    }
    assert (out["display_amount"] == 0).all()


def test_weekday_summary_only_includes_days_with_activity():
    df = _enriched([_row(1, "2026-03-02", 10.0, "Food")])  # a Monday
    out = weekday_summary(df)
    assert list(out["weekday"].astype(str)) == ["Monday"]
    assert out.iloc[0]["display_amount"] == 10.0


def test_merchant_summary_counts_and_sums():
    # extract_merchant() takes the first two words of the note verbatim
    # (no stopword filtering) -- unlike detect_merchant_candidate in utils.py.
    df = _enriched(
        [
            _row(1, "2026-03-01", 10.0, "Cafe", note="Starbucks"),
            _row(2, "2026-03-02", 12.0, "Cafe", note="Starbucks"),
        ]
    )
    out = merchant_summary(df)
    row = out[out["merchant"] == "Starbucks"].iloc[0]
    assert row["display_amount"] == 22.0
    assert row["count"] == 2


# ---------------------------------------------------------------------------
# detect_duplicates
# ---------------------------------------------------------------------------

def test_detect_duplicates_flags_exact_matches_only():
    df = _enriched(
        [
            _row(1, "2026-03-10", 15.0, "Cafe", note="coffee"),
            _row(2, "2026-03-10", 15.0, "Cafe", note="coffee"),  # duplicate of 1
            _row(3, "2026-03-10", 15.0, "Cafe", note="tea"),  # different note -> not a duplicate
        ]
    )
    out = detect_duplicates(df)
    assert set(out["id"]) == {1, 2}


def test_detect_duplicates_empty_df():
    empty = pd.DataFrame(columns=["id", "date_only", "amount", "category", "note", "date"])
    assert detect_duplicates(empty).empty


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------

def test_detect_anomalies_flags_outlier_within_a_category():
    rows = [
        _row(1, "2026-03-01", 10.0, "Cafe"),
        _row(2, "2026-03-02", 11.0, "Cafe"),
        _row(3, "2026-03-03", 9.0, "Cafe"),
        _row(4, "2026-03-04", 12.0, "Cafe"),
        _row(5, "2026-03-05", 100.0, "Cafe"),  # clear outlier
        # A second category with an extreme value but too few rows (<4) to qualify.
        _row(6, "2026-03-06", 500.0, "Rent"),
        _row(7, "2026-03-07", 510.0, "Rent"),
        _row(8, "2026-03-08", 5000.0, "Rent"),
    ]
    df = _enriched(rows)
    out = detect_anomalies(df)
    assert set(out["id"]) == {5}


def test_detect_anomalies_requires_minimum_rows():
    df = _enriched([_row(1, "2026-03-01", 10.0, "Cafe")])
    out = detect_anomalies(df)
    assert out.empty


# ---------------------------------------------------------------------------
# month_forecast
# ---------------------------------------------------------------------------

def test_month_forecast_extrapolates_linearly():
    df = _enriched(
        [
            _row(1, "2026-03-01", 100.0, "Food"),
            _row(2, "2026-03-10", 100.0, "Food"),
        ]
    )
    # 200 spent by day 10 of a 31-day month -> 200 / 10 * 31 = 620
    forecast = month_forecast(df, today=date(2026, 3, 10))
    assert forecast == pytest.approx(620.0)


def test_month_forecast_zero_when_no_spending_this_month():
    df = _enriched([_row(1, "2026-02-01", 100.0, "Food")])
    forecast = month_forecast(df, today=date(2026, 3, 10))
    assert forecast == 0.0


# ---------------------------------------------------------------------------
# streak_metrics
# ---------------------------------------------------------------------------

def test_streak_metrics_no_spend_streak_counts_days_since_last_expense(monkeypatch):
    monkeypatch.setattr(analytics, "date", _FixedDate)  # today frozen at 2026-03-20
    df = _enriched([_row(1, "2026-03-17", 10.0, "Food")])
    no_spend_streak, _ = streak_metrics(df)
    assert no_spend_streak == 3  # 18th, 19th, 20th have no spending


def test_streak_metrics_empty_df():
    empty = pd.DataFrame(columns=["date_only"])
    assert streak_metrics(empty) == (0, 0)


# ---------------------------------------------------------------------------
# calculate_financial_health
# ---------------------------------------------------------------------------

def test_calculate_financial_health_empty_df_returns_neutral_score():
    score, label, breakdown = calculate_financial_health(pd.DataFrame(), pd.DataFrame({"saved": []}), None)
    assert score == 50
    assert "more data" in label.lower()


def test_calculate_financial_health_within_budget_scores_well(freeze_today):
    df = _enriched(
        [
            _row(1, "2026-03-01", 100.0, "Food"),
            _row(2, "2026-03-02", 100.0, "Food"),
        ]
    )
    score, label, breakdown = calculate_financial_health(df, pd.DataFrame({"saved": [1000.0]}), monthly_limit_display=1000.0)
    assert 0 <= score <= 100
    assert breakdown["budget"] == 95.0  # usage = 200/1000 = 0.2 <= 0.75
    assert label in {"Excellent", "Good", "Needs attention", "Risky"}


def test_calculate_financial_health_over_budget_scores_worse_than_under_budget(freeze_today):
    under = _enriched([_row(1, "2026-03-01", 100.0, "Food")])
    over = _enriched([_row(1, "2026-03-01", 5000.0, "Food")])
    savings = pd.DataFrame({"saved": [0.0]})
    score_under, _, _ = calculate_financial_health(under, savings, monthly_limit_display=1000.0)
    score_over, _, _ = calculate_financial_health(over, savings, monthly_limit_display=1000.0)
    assert score_over < score_under


# ---------------------------------------------------------------------------
# savings_progress
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "saved, target, expected",
    [
        (50.0, 100.0, 0.5),
        (150.0, 100.0, 1.0),  # capped at 1.0
        (0.0, 100.0, 0.0),
        (10.0, 0.0, 0.0),  # target <= 0 -> 0.0, avoids division by zero
    ],
)
def test_savings_progress(saved, target, expected):
    assert savings_progress(saved, target) == expected


# ---------------------------------------------------------------------------
# csv_template
# ---------------------------------------------------------------------------

def test_csv_template_has_expected_header():
    content = csv_template().decode("utf-8")
    header = content.splitlines()[0]
    assert header == "date,amount,currency,category,note,subscription,recurrence,type"
    assert "expense" in content
    assert "income" in content
    assert "yearly" in content


# ---------------------------------------------------------------------------
# check_category_budgets
# ---------------------------------------------------------------------------

def test_check_category_budgets_computes_percentage_and_over_flag(freeze_today):
    df = _enriched(
        [
            _row(1, "2026-03-01", 40.0, "Food"),
            _row(2, "2026-03-02", 30.0, "Food"),
            _row(3, "2026-03-03", 150.0, "Rent"),
        ]
    )
    out = check_category_budgets(df, {"Food": 100.0, "Rent": 100.0}, "EUR")
    by_category = {row["category"]: row for row in out}
    assert by_category["Food"]["spent"] == 70.0
    assert by_category["Food"]["pct"] == 70.0
    assert by_category["Food"]["over"] is False
    assert by_category["Rent"]["spent"] == 150.0
    assert by_category["Rent"]["over"] is True
    # sorted by pct descending
    assert out[0]["category"] == "Rent"


def test_check_category_budgets_ignores_other_months(freeze_today):
    df = _enriched([_row(1, "2026-02-01", 999.0, "Food")])  # not the frozen "current" month
    out = check_category_budgets(df, {"Food": 100.0}, "EUR")
    assert out == []


def test_check_category_budgets_empty_when_no_budgets_set():
    df = _enriched([_row(1, "2026-03-01", 10.0, "Food")])
    assert check_category_budgets(df, {}, "EUR") == []
