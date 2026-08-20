from __future__ import annotations

import os
from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
from supabase import Client, create_client

from config import DEFAULT_CATEGORIES, INCOME_CATEGORIES
from utils import recurrence_period_bounds, safe_float

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


# =========================================================
# AUTH (Supabase Auth) — thin wrappers so callers never touch
# supabase.auth directly. Any AuthApiError raised here is left
# for the caller to interpret/translate.
# =========================================================

def sign_up(email: str, password: str, username: str):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"username": username}},
    })


def sign_in(email: str, password: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})


def sign_out() -> None:
    supabase.auth.sign_out()


def restore_auth_session(access_token: str, refresh_token: str):
    return supabase.auth.set_session(access_token, refresh_token)


def request_password_reset(email: str) -> None:
    supabase.auth.reset_password_email(email)


def verify_otp(token_hash: str, otp_type: str):
    """Exchange the token_hash from an invite/recovery/signup email link for a session.

    Uses the token_hash flow (query-param based) rather than Supabase's default
    implicit flow (which puts tokens after a `#` in the URL) because Streamlit's
    Python backend never receives anything after `#` — only `st.query_params`,
    which is populated from the `?...` part of the URL, is reachable server-side.
    """
    return supabase.auth.verify_otp({"token_hash": token_hash, "type": otp_type})


def update_password(new_password: str):
    return supabase.auth.update_user({"password": new_password})


def username_exists(username: str) -> bool:
    res = supabase.table("profiles").select("id").eq("username", username).limit(1).execute()
    return bool(res.data)


def get_profile_username(user_id: str) -> Optional[str]:
    res = supabase.table("profiles").select("username").eq("id", user_id).limit(1).execute()
    return res.data[0]["username"] if res.data else None


# =========================================================
# USER-DEFINED CATEGORIES (additive to config.py's built-in lists)
# =========================================================

@st.cache_data(ttl=60)
def get_custom_categories(user_id: str, tx_type: str = "expense") -> List[str]:
    """Cached for 60s (see the module docstring-style note above get_rates_map
    for why: Streamlit reruns this whole script on every widget interaction,
    so an uncached read here means a fresh Supabase round trip on every
    click, not just on real data changes). add_custom_category/
    delete_custom_category explicitly clear this cache on write, so a
    user's own change is never hidden behind the 60s TTL — the TTL only
    bounds staleness from *other* sessions/tabs.
    """
    res = (
        supabase.table("categories")
        .select("name")
        .eq("user_id", user_id)
        .eq("type", tx_type)
        .order("created_at")
        .execute()
    )
    return [str(row["name"]) for row in (res.data or [])]


@st.cache_data(ttl=60)
def get_category_options(user_id: str, tx_type: str = "expense") -> List[str]:
    """Built-in defaults (config.py) followed by the user's own categories.

    A custom category that duplicates a default (case-insensitively) is
    skipped so the picker never shows the same name twice.
    """
    defaults = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
    seen = {c.lower() for c in defaults}
    custom: list[str] = []
    for name in get_custom_categories(user_id, tx_type):
        if name.lower() not in seen:
            custom.append(name)
            seen.add(name.lower())
    return list(defaults) + custom


def add_custom_category(user_id: str, name: str, tx_type: str = "expense") -> tuple[bool, str]:
    """Returns (ok, reason). `reason` is a machine-readable code the UI layer
    maps to a translated message: "empty", "duplicate_default", "duplicate",
    "error", or "ok".
    """
    name = (name or "").strip()
    if not name:
        return False, "empty"
    defaults = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
    if name.lower() in {c.lower() for c in defaults}:
        return False, "duplicate_default"
    try:
        supabase.table("categories").insert({
            "user_id": user_id,
            "name": name,
            "type": tx_type,
        }).execute()
    except Exception as exc:
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            return False, "duplicate"
        return False, "error"
    get_custom_categories.clear()
    get_category_options.clear()
    return True, "ok"


def delete_custom_category(user_id: str, name: str, tx_type: str = "expense") -> None:
    supabase.table("categories").delete().eq("user_id", user_id).eq("type", tx_type).eq("name", name).execute()
    get_custom_categories.clear()
    get_category_options.clear()


@st.cache_data(ttl=60)
def get_category_colors(user_id: str) -> Dict[str, str]:
    """User color overrides for any category (built-in or custom), across
    both expense and income, flattened into one {name: "#hex"} dict — this
    matches how config.CATEGORY_COLORS is already shaped and consumed
    (a flat lookup by name), so callers can just merge the two dicts.
    """
    res = supabase.table("category_colors").select("name,color").eq("user_id", user_id).execute()
    return {str(row["name"]): str(row["color"]) for row in (res.data or [])}


def set_category_color(user_id: str, name: str, tx_type: str, color: str) -> None:
    supabase.table("category_colors").upsert(
        {"user_id": user_id, "name": name, "type": tx_type, "color": color},
        on_conflict="user_id,type,name",
    ).execute()
    get_category_colors.clear()


def reset_category_color(user_id: str, name: str, tx_type: str) -> None:
    supabase.table("category_colors").delete().eq("user_id", user_id).eq("type", tx_type).eq("name", name).execute()
    get_category_colors.clear()


def apply_category_color_template(user_id: str, template: Dict[str, str], expense_categories: List[str], income_categories: List[str]) -> None:
    """Bulk-apply a pre-built palette template (config.CATEGORY_COLOR_TEMPLATES)
    as this user's color overrides for every category the template covers.

    One batched upsert instead of one call per category (up to 19 rows) —
    same net effect as calling set_category_color() in a loop, but a single
    round trip. `expense_categories`/`income_categories` decide each row's
    `type` (category_colors' uniqueness is per user+type+name, so a name
    that happens to exist in both gets a row for each type it belongs to).
    """
    rows = []
    for name, color in template.items():
        if name in expense_categories:
            rows.append({"user_id": user_id, "name": name, "type": "expense", "color": color})
        if name in income_categories:
            rows.append({"user_id": user_id, "name": name, "type": "income", "color": color})
    if not rows:
        return
    supabase.table("category_colors").upsert(rows, on_conflict="user_id,type,name").execute()
    get_category_colors.clear()


@st.cache_data(ttl=3600)
def get_rates_map(base: str = "EUR") -> Dict[str, float]:
    """Cached for 1 hour — this is the single biggest performance fix in this
    pass. Uncached, every call here made 2 external HTTP requests (Frankfurter
    + NBU, up to 8s timeout each) with no caching at all. convert_to_eur() and
    convert_from_eur() both call this, and enrich_expenses() (analytics.py)
    calls convert_from_eur() once per transaction row via .apply() — so on a
    production account with 100+ transactions, a single dashboard render was
    issuing 100+ *sequential* external HTTP round trips. FX rates don't need
    to be fresher than an hour for this app's purposes.
    """
    base = base.upper()
    fallback = {
        "EUR": {"EUR": 1.0, "USD": 1.08, "UAH": 50.0},
        "USD": {"USD": 1.0, "EUR": 0.93, "UAH": 43.0},
        "UAH": {"UAH": 1.0, "EUR": 0.02, "USD": 0.023},
    }.get(base, {base: 1.0, "EUR": 1.0, "USD": 1.0, "UAH": 1.0})

    result = {base: 1.0}
    try:
        resp = requests.get(f"https://api.frankfurter.app/latest?from={base}&to=EUR,USD", timeout=8)
        rates = resp.json().get("rates", {})
        if isinstance(rates, dict):
            for cur in ["EUR", "USD"]:
                if cur == base:
                    result[cur] = 1.0
                elif cur in rates:
                    result[cur] = float(rates[cur])
    except Exception:
        pass

    try:
        data = requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json", timeout=8).json()
        eur_uah = usd_uah = None
        for row in data:
            if row.get("cc") == "EUR":
                eur_uah = float(row["rate"])
            if row.get("cc") == "USD":
                usd_uah = float(row["rate"])
        if eur_uah and usd_uah:
            if base == "EUR":
                result["UAH"] = eur_uah
            elif base == "USD":
                result["UAH"] = usd_uah
            elif base == "UAH":
                result["EUR"] = 1 / eur_uah
                result["USD"] = 1 / usd_uah
                result["UAH"] = 1.0
    except Exception:
        pass

    for key, value in fallback.items():
        result.setdefault(key, value)
    return result


def convert_to_eur(amount: float, currency: str) -> float:
    currency = (currency or "EUR").upper()
    if currency == "EUR":
        return round(safe_float(amount), 2)
    return round(safe_float(amount) * safe_float(get_rates_map(currency).get("EUR", 1.0), 1.0), 2)


def convert_from_eur(amount_eur: float, out_currency: str) -> float:
    out_currency = (out_currency or "EUR").upper()
    if out_currency == "EUR":
        return round(safe_float(amount_eur), 2)
    return round(safe_float(amount_eur) * safe_float(get_rates_map("EUR").get(out_currency, 1.0), 1.0), 2)


@st.cache_data(ttl=60)
def load_expenses(user_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    """Load a user's transactions, optionally bounded to a date range.

    Without bounds this pulls the user's entire transaction history in one
    query. Callers that render on every Streamlit rerun (i.e. the main app)
    should pass `start_date` to avoid re-fetching years of history on every
    widget interaction; callers that need guaranteed-complete data (full
    export, subscription bookkeeping) should call this with no bounds.
    """
    query = supabase.table("expenses").select("*").eq("user_id", user_id)
    if start_date is not None:
        query = query.gte("date", start_date.isoformat())
    if end_date is not None:
        query = query.lte("date", end_date.isoformat())
    res = query.order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["id", "user_id", "date", "amount", "category", "currency", "subscription", "recurrence", "note", "type"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["subscription"] = pd.to_numeric(df.get("subscription", 0), errors="coerce").fillna(0).astype(int)
    df["recurrence"] = df.get("recurrence", "monthly").fillna("monthly")
    df["note"] = df.get("note", "").fillna("")
    df["currency"] = df.get("currency", "EUR").fillna("EUR")
    df["category"] = df.get("category", "Other").fillna("Other")
    if "type" in df.columns:
        df["type"] = df["type"].fillna("")
    else:
        df["type"] = ""
    df["type"] = df.apply(lambda r: ("income" if str(r.get("type", "")).lower() == "income" or float(r.get("amount", 0)) < 0 else "expense"), axis=1)
    return df.sort_values(["date", "id"], ascending=[False, False]).reset_index(drop=True)


@st.cache_data(ttl=60)
def load_savings(user_id: str) -> pd.DataFrame:
    res = supabase.table("savings").select("*").eq("user_id", user_id).order("id", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["id", "user_id", "name", "target", "saved"])
    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved"] = pd.to_numeric(df["saved"], errors="coerce").fillna(0.0)
    return df


def add_savings_goal(user_id: str, name: str, target: float, saved: float) -> None:
    supabase.table("savings").insert({
        "user_id": user_id,
        "name": name,
        "target": float(target),
        "saved": float(saved),
    }).execute()
    load_savings.clear()


def update_savings_progress(user_id: str, goal_id: int, new_saved: float) -> None:
    supabase.table("savings").update({"saved": float(new_saved)}).eq("id", int(goal_id)).eq("user_id", user_id).execute()
    load_savings.clear()


def delete_savings_goal(user_id: str, goal_id: int) -> None:
    supabase.table("savings").delete().eq("id", int(goal_id)).eq("user_id", user_id).execute()
    load_savings.clear()


@st.cache_data(ttl=60)
def get_monthly_limit(user_id: str) -> Optional[float]:
    res = supabase.table("budgets").select("monthly_limit").eq("user_id", user_id).limit(1).execute()
    return float(res.data[0]["monthly_limit"]) if res.data else None


def set_monthly_limit(user_id: str, amount_eur: float) -> None:
    exists = supabase.table("budgets").select("user_id").eq("user_id", user_id).limit(1).execute()
    payload = {"user_id": user_id, "monthly_limit": float(amount_eur)}
    if exists.data:
        supabase.table("budgets").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("budgets").insert(payload).execute()
    get_monthly_limit.clear()


@st.cache_data(ttl=60)
def get_category_budgets(user_id: str) -> dict[str, float]:
    res = (
        supabase.table("category_budgets")
        .select("category, monthly_limit")
        .eq("user_id", user_id)
        .execute()
    )
    return {
        str(row["category"]): float(row["monthly_limit"])
        for row in (res.data or [])
        if row.get("category") is not None and row.get("monthly_limit") is not None
    }


def set_category_budget(user_id: str, category: str, amount_eur: float) -> None:
    payload = {
        "user_id": user_id,
        "category": str(category),
        "monthly_limit": float(amount_eur),
    }
    supabase.table("category_budgets").upsert(
        payload,
        on_conflict="user_id,category",
    ).execute()
    get_category_budgets.clear()


def execute_expense_write(write_fn, payload: Dict[str, object]) -> None:
    try:
        write_fn(payload)
    except Exception:
        fallback_payload = dict(payload)
        fallback_payload.pop("type", None)
        write_fn(fallback_payload)


def add_transaction(user_id: str, expense_date: date, amount: float, category: str, currency: str, tx_type: str = "expense", note: str = "", subscription: int = 0, recurrence: str = "monthly") -> None:
    signed_amount = abs(amount) * (-1 if tx_type == "income" else 1)
    amount_eur = convert_to_eur(signed_amount, currency)
    is_subscription = int(subscription if tx_type == "expense" else 0)
    payload = {
        "user_id": user_id,
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "category": category,
        "currency": currency,
        "subscription": is_subscription,
        "recurrence": (recurrence or "monthly") if is_subscription else "monthly",
        "note": (note or "").strip(),
        "type": tx_type,
    }
    execute_expense_write(lambda p: supabase.table("expenses").insert(p).execute(), payload)
    load_expenses.clear()


def add_expense(user_id: str, expense_date: date, amount: float, category: str, currency: str, note: str = "", subscription: int = 0, recurrence: str = "monthly") -> None:
    add_transaction(user_id, expense_date, amount, category, currency, "expense", note, subscription, recurrence)


def update_transaction(user_id: str, expense_id: int, expense_date: date, original_amount: float, original_currency: str,
                   category: str, note: str, subscription: bool, tx_type: str = "expense", recurrence: str = "monthly") -> None:
    signed_amount = abs(original_amount) * (-1 if tx_type == "income" else 1)
    amount_eur = convert_to_eur(signed_amount, original_currency)
    is_subscription = bool(subscription and tx_type == "expense")
    payload = {
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "currency": original_currency,
        "category": category,
        "note": (note or "").strip(),
        "subscription": 1 if is_subscription else 0,
        "recurrence": (recurrence or "monthly") if is_subscription else "monthly",
        "type": tx_type,
    }
    execute_expense_write(
        lambda p: supabase.table("expenses").update(p).eq("id", int(expense_id)).eq("user_id", user_id).execute(),
        payload,
    )
    load_expenses.clear()


def update_expense(user_id: str, expense_id: int, expense_date: date, original_amount: float, original_currency: str,
                   category: str, note: str, subscription: bool, recurrence: str = "monthly") -> None:
    update_transaction(user_id, expense_id, expense_date, original_amount, original_currency, category, note, subscription, "expense", recurrence)


def delete_expense(user_id: str, expense_id: int) -> None:
    supabase.table("expenses").delete().eq("id", int(expense_id)).eq("user_id", user_id).execute()
    load_expenses.clear()


def upsert_recurring_transactions(user_id: str) -> int:
    """Create this period's occurrence for every recurring (subscription) row
    that doesn't already have one.

    "Period" depends on each row's own `recurrence` (weekly/monthly/yearly,
    see `utils.recurrence_period_bounds`) — this generalizes what used to be
    a monthly-only check. Matching an existing occurrence is still done by
    exact category/note/amount/recurrence match within the period, which
    remains the same brittleness the original monthly-only version had: if a
    subscription's note or amount changes, a duplicate (or a missed
    occurrence) can appear. That trade-off is unchanged by this pass.
    """
    df = load_expenses(user_id)
    if df.empty:
        return 0
    subs = df[(df["subscription"] == 1) & (df["type"] == "expense")].copy()
    if subs.empty:
        return 0

    today = date.today()
    created = 0

    for _, row in subs.iterrows():
        recurrence = str(row.get("recurrence") or "monthly")
        period_start, period_end = recurrence_period_bounds(today, recurrence)
        row_date = row["date"].date()
        if period_start <= row_date < period_end:
            # Already has an occurrence in the current period (either the
            # original entry or one generated on an earlier login).
            continue
        exists = (
            supabase.table("expenses")
            .select("id")
            .eq("user_id", user_id)
            .eq("subscription", 1)
            .eq("recurrence", recurrence)
            .eq("category", str(row["category"]))
            .eq("note", str(row["note"]))
            .eq("amount", float(row["amount"]))
            .gte("date", period_start.isoformat())
            .lt("date", period_end.isoformat())
            .limit(1)
            .execute()
        )
        if not exists.data:
            supabase.table("expenses").insert({
                "user_id": user_id,
                "date": period_start.isoformat(),
                "amount": float(row["amount"]),
                "category": str(row["category"]),
                "currency": str(row["currency"] or "EUR"),
                "subscription": 1,
                "recurrence": recurrence,
                "note": str(row["note"]),
            }).execute()
            created += 1
    if created:
        load_expenses.clear()
    return created
