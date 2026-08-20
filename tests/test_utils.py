from datetime import date, datetime

import pandas as pd
import pytest

from utils import (
    darken_hex,
    detect_merchant_candidate,
    format_money,
    infer_category,
    lighten_hex,
    monthly_equivalent,
    month_key,
    normalize_quick_text,
    parse_quick_add,
    readable_text_color,
    recurrence_period_bounds,
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
    result = parse_quick_add("45 EUR lunch")
    assert result["ok"] is True
    assert result["date"] == date.today()


def test_parse_quick_add_decimal_amount_without_date_defaults_to_today():
    # A bare decimal amount like "8.5" is shaped like a day.month date, but
    # since there's no second number in the text to serve as the amount, it
    # must be treated as the amount and the date must fall back to today --
    # not be misread as day=8, month=5.
    result = parse_quick_add("8.5 EUR lunch")
    assert result["ok"] is True
    assert result["date"] == date.today()
    assert result["amount"] == 8.5


def test_parse_quick_add_distinguishes_date_from_amount_when_both_present():
    # "17.03" (a real date, March 17) and "24.90" (the amount) both look
    # like day.month-shaped numbers. The date candidate's own span must be
    # excluded from the amount search so the real amount is found instead of
    # re-matching the date fragment.
    result = parse_quick_add("17.03 24.90 groceries")
    assert result["ok"] is True
    assert result["date"] == date(date.today().year, 3, 17)
    assert result["amount"] == 24.90


def test_parse_quick_add_skips_invalid_date_candidate_for_a_later_valid_one():
    # "24.90" isn't a valid date (month=90), so it must be skipped in favor
    # of the later, valid "17.03" candidate -- rather than giving up on
    # date-parsing entirely after the first candidate fails.
    result = parse_quick_add("24.90 17.03 groceries")
    assert result["ok"] is True
    assert result["date"] == date(date.today().year, 3, 17)
    assert result["amount"] == 24.90


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


# ---------------------------------------------------------------------------
# recurrence_period_bounds (Wave 3: flexible recurring-transaction periods)
# ---------------------------------------------------------------------------

def test_recurrence_period_bounds_monthly_matches_calendar_month():
    # 2026-02-15 is a Sunday in a 28-day February.
    start, end = recurrence_period_bounds(date(2026, 2, 15), "monthly")
    assert start == date(2026, 2, 1)
    assert end == date(2026, 3, 1)


def test_recurrence_period_bounds_monthly_handles_leap_february():
    start, end = recurrence_period_bounds(date(2028, 2, 10), "monthly")
    assert start == date(2028, 2, 1)
    assert end == date(2028, 3, 1)


def test_recurrence_period_bounds_weekly_starts_on_monday():
    # 2026-03-19 is a Thursday.
    start, end = recurrence_period_bounds(date(2026, 3, 19), "weekly")
    assert start == date(2026, 3, 16)  # the preceding Monday
    assert end == date(2026, 3, 23)


def test_recurrence_period_bounds_yearly_spans_calendar_year():
    start, end = recurrence_period_bounds(date(2026, 7, 4), "yearly")
    assert start == date(2026, 1, 1)
    assert end == date(2027, 1, 1)


def test_recurrence_period_bounds_unrecognized_value_falls_back_to_monthly():
    start, end = recurrence_period_bounds(date(2026, 5, 5), "biweekly")
    assert start == date(2026, 5, 1)
    assert end == date(2026, 6, 1)


def test_recurrence_period_bounds_defaults_to_monthly_when_omitted():
    start, end = recurrence_period_bounds(date(2026, 5, 5))
    assert start == date(2026, 5, 1)
    assert end == date(2026, 6, 1)


# ---------------------------------------------------------------------------
# monthly_equivalent
# ---------------------------------------------------------------------------

def test_monthly_equivalent_monthly_is_unchanged():
    assert monthly_equivalent(100.0, "monthly") == 100.0


def test_monthly_equivalent_weekly_uses_average_weeks_per_month():
    assert monthly_equivalent(10.0, "weekly") == pytest.approx(10.0 * 52 / 12)


def test_monthly_equivalent_yearly_divides_by_twelve():
    assert monthly_equivalent(120.0, "yearly") == pytest.approx(10.0)


def test_monthly_equivalent_defaults_to_monthly_when_omitted():
    assert monthly_equivalent(50.0) == 50.0


# ---------------------------------------------------------------------------
# readable_text_color
# ---------------------------------------------------------------------------

def test_readable_text_color_picks_dark_text_on_light_background():
    assert readable_text_color("#FFEB3B") == "#1a1d29"  # bright yellow


def test_readable_text_color_picks_light_text_on_dark_background():
    assert readable_text_color("#1A237E") == "#ffffff"  # dark indigo


def test_readable_text_color_is_case_insensitive():
    assert readable_text_color("#ffeb3b") == readable_text_color("#FFEB3B")


def test_readable_text_color_falls_back_to_light_on_bad_input():
    assert readable_text_color("not-a-color") == "#ffffff"


# ---------------------------------------------------------------------------
# lighten_hex / darken_hex
# ---------------------------------------------------------------------------

def test_lighten_hex_zero_amount_is_unchanged():
    assert lighten_hex("#1d4ed8", 0) == "#1d4ed8"


def test_lighten_hex_full_amount_is_white():
    assert lighten_hex("#1d4ed8", 1) == "#ffffff"


def test_lighten_hex_moves_toward_white():
    lightened = lighten_hex("#1d4ed8", 0.5)
    # every channel should be >= the original channel, and the result should
    # not equal the original or pure white
    orig = (0x1d, 0x4e, 0xd8)
    r, g, b = (int(lightened.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    assert (r, g, b) != orig
    assert r >= orig[0] and g >= orig[1] and b >= orig[2]


def test_darken_hex_zero_amount_is_unchanged():
    assert darken_hex("#1d4ed8", 0) == "#1d4ed8"


def test_darken_hex_full_amount_is_black():
    assert darken_hex("#1d4ed8", 1) == "#000000"
