from datetime import date, datetime

import pandas as pd
import pytest

from utils import (
    detect_merchant_candidate,
    format_money,
    infer_category,
    month_key,
    normalize_quick_text,
    parse_quick_add,
    safe_float,
    tokenize_quick_text,
)


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, default, expected",
    [
        ("12.5", 0.0, 12.5),
        (12, 0.0, 12.0),
        (None, 0.0, 0.0),
        ("", 0.0, 0.0),
        ("not a number", 0.0, 0.0),
        ("not a number", -1.0, -1.0),
        ("3,5", 0.0, 0.0),  # comma decimals are not accepted, falls back to default
    ],
)
def test_safe_float(value, default, expected):
    assert safe_float(value, default) == expected


# ---------------------------------------------------------------------------
# format_money
# ---------------------------------------------------------------------------

def test_format_money_uses_space_as_thousands_separator():
    assert format_money(1234.5, "EUR") == "1 234.50 EUR"


def test_format_money_rounds_to_two_decimals():
    assert format_money(9.999, "USD") == "10.00 USD"


# ---------------------------------------------------------------------------
# month_key
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [date(2026, 3, 17), datetime(2026, 3, 17, 8, 30), pd.Timestamp("2026-03-17")],
)
def test_month_key_accepts_date_datetime_and_timestamp(value):
    assert month_key(value) == "2026-03"


# ---------------------------------------------------------------------------
# normalize_quick_text / tokenize_quick_text
# ---------------------------------------------------------------------------

def test_normalize_quick_text_strips_dates_amounts_and_currency():
    normalized = normalize_quick_text("2026-03-17 12.50 EUR coffee at Starbucks")
    assert "2026" not in normalized
    assert "12" not in normalized
    assert "eur" not in normalized
    assert "coffee" in normalized
    assert "starbucks" in normalized


def test_tokenize_quick_text_drops_stopwords():
    tokens = tokenize_quick_text("lunch at the cafe")
    assert "at" not in tokens
    assert "the" not in tokens
    assert "lunch" in tokens
    assert "cafe" in tokens


# ---------------------------------------------------------------------------
# detect_merchant_candidate
# ---------------------------------------------------------------------------

def test_detect_merchant_candidate_prefers_known_merchant():
    assert detect_merchant_candidate("coffee at Starbucks", tx_type="expense") == "starbucks"


def test_detect_merchant_candidate_falls_back_to_first_tokens():
    # no known merchant in this text -> falls back to the first couple of tokens
    guess = detect_merchant_candidate("random unknown thing bought", tx_type="expense")
    assert guess  # non-empty
    assert "random" in guess


# ---------------------------------------------------------------------------
# infer_category
# ---------------------------------------------------------------------------

def test_infer_category_empty_note_returns_fallback_with_low_confidence():
    result = infer_category("", fallback="Other")
    assert result["category"] == "Other"
    assert result["confidence"] == "low"
    assert result["reason"] == "empty"


def test_infer_category_merchant_match_is_high_confidence():
    result = infer_category("coffee at starbucks", fallback="Other")
    assert result["category"] == "Cafe"
    assert result["confidence"] == "high"
    assert result["reason"] == "merchant"


def test_infer_category_keyword_match():
    result = infer_category("monthly netflix subscription", fallback="Other")
    assert result["category"] == "Entertainment"


def test_infer_category_income_keyword_match():
    result = infer_category("salary payment", fallback="Other Income", tx_type="income")
    assert result["category"] == "Salary"


def test_infer_category_no_match_returns_fallback():
    result = infer_category("xyzxyz unmatched gibberish", fallback="Other")
    assert result["category"] == "Other"
    assert result["confidence"] == "low"


def test_infer_category_uses_history_when_no_direct_match():
    # "spar" is a known merchant (-> Food) so build history around a note
    # that has no keyword/merchant match of its own, but matches prior notes.
    history = pd.DataFrame(
        [
            {"note": "weekly shop xyz", "category": "Food", "type": "expense"},
            {"note": "weekly shop xyz", "category": "Food", "type": "expense"},
            {"note": "weekly shop xyz", "category": "Food", "type": "expense"},
        ]
    )
    result = infer_category("weekly shop xyz", fallback="Other", history_df=history)
    assert result["category"] == "Food"
    assert result["reason"].startswith("history:")


# ---------------------------------------------------------------------------
# parse_quick_add
# ---------------------------------------------------------------------------

def test_parse_quick_add_full_example():
    result = parse_quick_add("2026-03-17 12.50 EUR coffee at Starbucks")
    assert result["ok"] is True
    assert result["date"] == date(2026, 3, 17)
    assert result["amount"] == 12.50
    assert result["currency"] == "EUR"
    assert result["category"] == "Cafe"
    assert result["tx_type"] == "expense"
    assert result["subscription"] is False


def test_parse_quick_add_detects_income():
    result = parse_quick_add("2026-03-01 2500 EUR salary")
    assert result["ok"] is True
    assert result["tx_type"] == "income"
    assert result["category"] == "Salary"


def test_parse_quick_add_detects_subscription():
    result = parse_quick_add("9.99 EUR netflix monthly subscription")
    assert result["ok"] is True
    assert result["subscription"] is True


def test_parse_quick_add_defaults_date_to_today_when_missing():
    # Use an integer amount (no "." or "/") so it can't be misread by the
    # short-date regex -- see test_parse_quick_add_decimal_amount_without_date_is_ambiguous.
    result = parse_quick_add("45 EUR lunch")
    assert result["ok"] is True
    assert result["date"] == date.today()


def test_parse_quick_add_decimal_amount_without_date_is_ambiguous():
    # Known quirk: with no explicit date, a bare decimal amount like "8.5"
    # matches the short-date regex (day.month) before the amount regex gets
    # a chance to run, so the entry is misdated instead of defaulting to
    # today. Documented here so a future fix doesn't regress silently.
    result = parse_quick_add("8.5 EUR lunch")
    assert result["ok"] is True
    assert result["date"] == date(date.today().year, 5, 8)


def test_parse_quick_add_without_amount_fails_gracefully():
    result = parse_quick_add("just a note with no numbers")
    assert result["ok"] is False
    assert result["amount"] is None
    assert result["error"]


def test_parse_quick_add_empty_input_fails_gracefully():
    result = parse_quick_add("")
    assert result["ok"] is False


def test_parse_quick_add_short_date_format():
    result = parse_quick_add("17.03.2026 5 EUR bread")
    assert result["ok"] is True
    assert result["date"] == date(2026, 3, 17)


def test_parse_quick_add_comma_decimal_amount():
    result = parse_quick_add("12,50 EUR taxi")
    assert result["ok"] is True
    assert result["amount"] == 12.50
