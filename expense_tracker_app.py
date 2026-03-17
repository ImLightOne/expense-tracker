from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import bcrypt
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from supabase import Client, create_client


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Expense Tracker Pro+", page_icon="💸", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Rent", "Entertainment", "Shopping", "Health",
    "Sports", "Bills", "Cafe", "Education", "Travel", "Other"
]
SUPPORTED_CURRENCIES = ["EUR", "USD", "UAH"]
INCOME_CATEGORIES = ["Salary", "Bonus", "Freelance", "Investments", "Gift", "Refund", "Other Income"]
CATEGORY_COLORS = {
    "Food": "#f97316",
    "Transport": "#3b82f6",
    "Rent": "#8b5cf6",
    "Entertainment": "#ec4899",
    "Shopping": "#14b8a6",
    "Health": "#ef4444",
    "Sports": "#22c55e",
    "Bills": "#f59e0b",
    "Cafe": "#d97706",
    "Education": "#6366f1",
    "Travel": "#06b6d4",
    "Other": "#64748b",
    "Salary": "#10b981",
    "Bonus": "#34d399",
    "Freelance": "#22c55e",
    "Investments": "#059669",
    "Gift": "#6ee7b7",
    "Refund": "#2dd4bf",
    "Other Income": "#0f766e",
}

CATEGORY_KEYWORDS = {
    "Food": ["grocery", "groceries", "supermarket", "spar", "billa", "lidl", "hofer", "food", "market"],
    "Transport": ["uber", "taxi", "bolt", "train", "bus", "tram", "metro", "fuel", "gas", "parking"],
    "Rent": ["rent", "miete", "housing", "dorm", "wohnung"],
    "Entertainment": ["movie", "cinema", "netflix", "spotify", "game", "steam", "concert", "party"],
    "Shopping": ["amazon", "shopping", "clothes", "zara", "hm", "h&m", "ikea"],
    "Health": ["pharmacy", "doctor", "medicine", "dentist", "medical"],
    "Sports": ["gym", "sport", "supplement", "protein", "run", "bike", "fitness"],
    "Bills": ["electricity", "internet", "phone", "bill", "utility", "versicherung", "insurance"],
    "Cafe": ["coffee", "cafe", "restaurant", "bar", "mcd", "mcdonald", "burger", "pizza"],
    "Education": ["course", "book", "udemy", "education", "study", "uni", "wu", "exam"],
    "Travel": ["flight", "hotel", "booking", "airbnb", "trip", "travel"],
}

STYLE = """
<style>
.block-container {max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem;}
[data-testid='stSidebar'] {background: linear-gradient(180deg,#111827 0%,#0f172a 100%) !important;}
[data-testid='stSidebar'], [data-testid='stSidebar'] * {color: white !important;}
.section-card {
  background: var(--secondary-background-color);
  border: 1px solid rgba(128,128,128,.18);
  border-radius: 18px; padding: 1rem; margin-bottom: 1rem;
  box-shadow: 0 8px 24px rgba(15,23,42,.06);
}
.metric-card {
  background: linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  color: white; border-radius: 18px; padding: 1rem; min-height: 125px;
  box-shadow: 0 10px 28px rgba(15,23,42,.18);
}
.metric-label {font-size:.95rem; opacity:.8; margin-bottom:.35rem;}
.metric-value {font-size:1.7rem; font-weight:800; line-height:1.08;}
.metric-foot {font-size:.88rem; opacity:.75; margin-top:.4rem;}
.small-muted {opacity:.72; font-size:.92rem;}
.badge {
  display:inline-block; padding:.2rem .55rem; border-radius:999px;
  font-size:.76rem; font-weight:700; color:white;
}
.feed-row {
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  padding:.75rem; border:1px solid rgba(128,128,128,.18); border-radius:14px;
  margin-bottom:.55rem; background:var(--secondary-background-color);
}
.soft-box {
  border:1px dashed rgba(128,128,128,.28); border-radius:16px; padding:1rem;
  background:var(--secondary-background-color);
}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)


# =========================================================
# UTILITIES
# =========================================================

def rerun() -> None:
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def format_money(value: float, currency: str = "EUR") -> str:
    return f"{value:,.2f} {currency}".replace(",", " ")


def month_key(dt: pd.Timestamp | date | datetime) -> str:
    return pd.Timestamp(dt).strftime("%Y-%m")


def section(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def end_section() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str, foot: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-foot">{foot}</div></div>',
        unsafe_allow_html=True,
    )


def show_empty(text: str) -> None:
    st.markdown(f'<div class="soft-box">{text}</div>', unsafe_allow_html=True)


def infer_category(note: str, fallback: str = "Other") -> str:
    text = (note or "").strip().lower()
    if not text:
        return fallback
    income_keywords = {
        "Salary": ["salary", "paycheck", "wage"],
        "Bonus": ["bonus"],
        "Freelance": ["freelance", "client", "invoice"],
        "Investments": ["dividend", "interest", "investment", "stock"],
        "Gift": ["gift", "present"],
        "Refund": ["refund", "cashback", "reimbursement"],
    }
    for category, keywords in income_keywords.items():
        if any(word in text for word in keywords):
            return category
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(word in text for word in keywords):
            return category
    return fallback


def extract_merchant(note: str, category: str) -> str:
    text = (note or "").strip()
    if not text:
        return category
    normalized = re.sub(r"[^\w\s&-]", " ", text).strip()
    parts = [p for p in normalized.split() if p]
    if not parts:
        return category
    return " ".join(parts[:2]).title()


def parse_quick_add(text: str) -> Dict[str, object]:
    raw = (text or "").strip()
    result: Dict[str, object] = {
        "ok": False,
        "amount": None,
        "currency": "EUR",
        "date": date.today(),
        "category": "Other",
        "note": raw,
        "subscription": False,
        "tx_type": "expense",
        "error": "Could not parse the entry. Example: 2026-03-17 12.50 EUR coffee at Starbucks",
    }
    if not raw:
        return result

    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw)
    if date_match:
        try:
            result["date"] = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except Exception:
            pass
    else:
        short_match = re.search(r"\b(\d{1,2}[./-]\d{1,2})(?:[./-](\d{2,4}))?\b", raw)
        if short_match:
            token = short_match.group(0).replace(".", "-").replace("/", "-")
            parts = token.split("-")
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else date.today().year
            if year < 100:
                year += 2000
            try:
                result["date"] = date(year, month, day)
            except Exception:
                pass

    amount_match = re.search(r"(?<!\d)(\d+[\.,]?\d{0,2})(?!\d)", raw)
    if not amount_match:
        return result
    amount = safe_float(amount_match.group(1).replace(",", "."), None)
    if amount is None:
        return result
    result["amount"] = amount

    currency_match = re.search(r"\b(EUR|USD|UAH|€|\$|₴)\b", raw.upper())
    if currency_match:
        token = currency_match.group(1)
        result["currency"] = {"€": "EUR", "$": "USD", "₴": "UAH"}.get(token, token)

    lowered = raw.lower()
    result["subscription"] = any(word in lowered for word in ["subscription", "sub", "abo", "monthly", "netflix", "spotify"])
    income_markers = ["income", "salary", "bonus", "refund", "cashback", "gift", "freelance", "paid", "payment received"]
    result["tx_type"] = "income" if any(word in lowered for word in income_markers) else "expense"
    default_fallback = "Other Income" if result["tx_type"] == "income" else "Other"
    result["category"] = infer_category(raw, fallback=default_fallback)
    result["ok"] = True
    result["error"] = ""
    return result


# =========================================================
# AUTH / DATA ACCESS
# =========================================================

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user(username: str):
    res = supabase.table("users").select("*").eq("username", username.strip()).limit(1).execute()
    return res.data[0] if res.data else None


def register_user(username: str, password: str) -> Tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, "Username must have at least 3 characters."
    if len(password) < 6:
        return False, "Password must have at least 6 characters."
    exists = supabase.table("users").select("id").eq("username", username).limit(1).execute()
    if exists.data:
        return False, "This username already exists."
    supabase.table("users").insert({
        "username": username,
        "password_hash": hash_password(password).decode("utf-8"),
    }).execute()
    return True, "Account created successfully."


def require_login() -> int:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return int(user_id)


@st.cache_data(ttl=1800)
def get_rates_map(base: str = "EUR") -> Dict[str, float]:
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


def load_expenses(user_id: int) -> pd.DataFrame:
    res = supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["id", "user_id", "date", "amount", "category", "currency", "subscription", "note", "type"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["subscription"] = pd.to_numeric(df.get("subscription", 0), errors="coerce").fillna(0).astype(int)
    df["note"] = df.get("note", "").fillna("")
    df["currency"] = df.get("currency", "EUR").fillna("EUR")
    df["category"] = df.get("category", "Other").fillna("Other")
    if "type" in df.columns:
        df["type"] = df["type"].fillna("")
    else:
        df["type"] = ""
    df["type"] = df.apply(lambda r: ("income" if str(r.get("type", "")).lower() == "income" or float(r.get("amount", 0)) < 0 else "expense"), axis=1)
    return df.sort_values(["date", "id"], ascending=[False, False]).reset_index(drop=True)


def load_savings(user_id: int) -> pd.DataFrame:
    res = supabase.table("savings").select("*").eq("user_id", user_id).order("id", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=["id", "user_id", "name", "target", "saved"])
    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved"] = pd.to_numeric(df["saved"], errors="coerce").fillna(0.0)
    return df


def get_monthly_limit(user_id: int) -> Optional[float]:
    res = supabase.table("budgets").select("monthly_limit").eq("user_id", user_id).limit(1).execute()
    return float(res.data[0]["monthly_limit"]) if res.data else None


def set_monthly_limit(user_id: int, amount_eur: float) -> None:
    exists = supabase.table("budgets").select("user_id").eq("user_id", user_id).limit(1).execute()
    payload = {"user_id": user_id, "monthly_limit": float(amount_eur)}
    if exists.data:
        supabase.table("budgets").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("budgets").insert(payload).execute()


def add_transaction(user_id: int, expense_date: date, amount: float, category: str, currency: str, tx_type: str = "expense", note: str = "", subscription: int = 0) -> None:
    signed_amount = abs(amount) * (-1 if tx_type == "income" else 1)
    amount_eur = convert_to_eur(signed_amount, currency)
    payload = {
        "user_id": user_id,
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "category": category,
        "currency": currency,
        "subscription": int(subscription if tx_type == "expense" else 0),
        "note": (note or "").strip(),
    }
    try:
        payload["type"] = tx_type
        supabase.table("expenses").insert(payload).execute()
    except Exception:
        payload.pop("type", None)
        supabase.table("expenses").insert(payload).execute()


def add_expense(user_id: int, expense_date: date, amount: float, category: str, currency: str, note: str = "", subscription: int = 0) -> None:
    add_transaction(user_id, expense_date, amount, category, currency, "expense", note, subscription)


def update_transaction(user_id: int, expense_id: int, expense_date: date, original_amount: float, original_currency: str,
                   category: str, note: str, subscription: bool, tx_type: str = "expense") -> None:
    signed_amount = abs(original_amount) * (-1 if tx_type == "income" else 1)
    amount_eur = convert_to_eur(signed_amount, original_currency)
    payload = {
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "currency": original_currency,
        "category": category,
        "note": (note or "").strip(),
        "subscription": 1 if (subscription and tx_type == "expense") else 0,
    }
    try:
        payload["type"] = tx_type
        supabase.table("expenses").update(payload).eq("id", int(expense_id)).eq("user_id", int(user_id)).execute()
    except Exception:
        payload.pop("type", None)
        supabase.table("expenses").update(payload).eq("id", int(expense_id)).eq("user_id", int(user_id)).execute()


def update_expense(user_id: int, expense_id: int, expense_date: date, original_amount: float, original_currency: str,
                   category: str, note: str, subscription: bool) -> None:
    update_transaction(user_id, expense_id, expense_date, original_amount, original_currency, category, note, subscription, "expense")


def delete_expense(user_id: int, expense_id: int) -> None:
    supabase.table("expenses").delete().eq("id", int(expense_id)).eq("user_id", int(user_id)).execute()


def upsert_monthly_subscriptions(user_id: int) -> int:
    df = load_expenses(user_id)
    if df.empty:
        return 0
    subs = df[(df["subscription"] == 1) & (df["type"] == "expense")].copy()
    if subs.empty:
        return 0

    today = date.today()
    current_month = today.strftime("%Y-%m")
    month_start = date(today.year, today.month, 1).isoformat()
    created = 0

    for _, row in subs.iterrows():
        if month_key(row["date"]) == current_month:
            continue
        exists = (
            supabase.table("expenses")
            .select("id")
            .eq("user_id", user_id)
            .eq("subscription", 1)
            .eq("category", str(row["category"]))
            .eq("note", str(row["note"]))
            .eq("amount", float(row["amount"]))
            .gte("date", f"{current_month}-01")
            .lt("date", f"{current_month}-32")
            .limit(1)
            .execute()
        )
        if not exists.data:
            supabase.table("expenses").insert({
                "user_id": user_id,
                "date": month_start,
                "amount": float(row["amount"]),
                "category": str(row["category"]),
                "currency": str(row["currency"] or "EUR"),
                "subscription": 1,
                "note": str(row["note"]),
            }).execute()
            created += 1
    return created


# =========================================================
# DATA SHAPING / ANALYTICS
# =========================================================

def enrich_expenses(df: pd.DataFrame, display_currency: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["display_amount"] = out["amount"].apply(lambda x: convert_from_eur(x, display_currency))
    out["display_abs_amount"] = out["display_amount"].abs()
    out["original_amount"] = out.apply(lambda r: abs(convert_from_eur(r["amount"], r["currency"])), axis=1)
    out["date_only"] = out["date"].dt.date
    out["month"] = out["date"].dt.to_period("M").astype(str)
    out["year"] = out["date"].dt.year
    out["weekday"] = out["date"].dt.day_name()
    out["day"] = out["date"].dt.day
    out["merchant"] = out.apply(lambda r: extract_merchant(r.get("note", ""), r.get("category", "Other")), axis=1)
    return out


def apply_filters(df: pd.DataFrame, start_date: date, end_date: date, categories: List[str],
                  text_query: str, subs_only: bool) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out = out[(out["date"].dt.date >= start_date) & (out["date"].dt.date <= end_date)]
    if categories:
        out = out[out["category"].isin(categories)]
    if text_query.strip():
        query = text_query.strip().lower()
        mask = (
            out["note"].fillna("").str.lower().str.contains(query, na=False)
            | out["merchant"].fillna("").str.lower().str.contains(query, na=False)
            | out["category"].fillna("").str.lower().str.contains(query, na=False)
        )
        out = out[mask]
    if subs_only:
        out = out[out["subscription"] == 1]
    return out.copy()


def get_month_options(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    return sorted(df["month"].dropna().unique().tolist(), reverse=True)


def monthly_series(df: pd.DataFrame, value_col: str = "display_amount") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", value_col])
    out = df.groupby("month", as_index=False)[value_col].sum().sort_values("month")
    return out


def category_summary(df: pd.DataFrame, value_col: str = "display_amount") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", value_col])
    return df.groupby("category", as_index=False)[value_col].sum().sort_values(value_col, ascending=False)


def merchant_summary(df: pd.DataFrame, value_col: str = "display_amount") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["merchant", value_col])
    return df.groupby("merchant", as_index=False)[value_col].agg(["sum", "count"]).reset_index().rename(columns={"sum": value_col}).sort_values(value_col, ascending=False)


def weekday_summary(df: pd.DataFrame, value_col: str = "display_amount") -> pd.DataFrame:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if df.empty:
        return pd.DataFrame({"weekday": order, value_col: [0] * 7})
    out = df.groupby("weekday", as_index=False)[value_col].sum()
    out["weekday"] = pd.Categorical(out["weekday"], categories=order, ordered=True)
    return out.sort_values("weekday")


def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    dup_cols = ["date_only", "amount", "category", "note"]
    out = df.copy()
    out["dup_count"] = out.groupby(dup_cols)["id"].transform("count")
    return out[out["dup_count"] > 1].sort_values(["date", "amount"], ascending=[False, False])


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 8:
        return pd.DataFrame(columns=df.columns)
    frames = []
    for category, g in df.groupby("category"):
        if len(g) < 4:
            continue
        q1 = g["display_amount"].quantile(0.25)
        q3 = g["display_amount"].quantile(0.75)
        iqr = q3 - q1
        threshold = q3 + 1.5 * iqr
        if threshold <= 0:
            continue
        frames.append(g[g["display_amount"] > threshold])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=df.columns)


def month_forecast(df: pd.DataFrame, today: Optional[date] = None) -> float:
    today = today or date.today()
    current_month = month_key(today)
    cur = df[df["month"] == current_month].copy()
    if cur.empty:
        return 0.0
    spent = cur["display_amount"].sum()
    days_elapsed = today.day
    days_in_month = (pd.Timestamp(today).days_in_month)
    return spent / max(days_elapsed, 1) * days_in_month


def streak_metrics(df: pd.DataFrame) -> Tuple[int, int]:
    if df.empty:
        return 0, 0
    spent_days = sorted(set(df["date_only"].tolist()))
    day_set = set(spent_days)
    today = date.today()

    no_spend_streak = 0
    cursor = today
    while cursor not in day_set:
        no_spend_streak += 1
        cursor -= timedelta(days=1)
        if no_spend_streak > 365:
            break

    max_no_spend = 0
    if spent_days:
        start = min(spent_days)
        end = max(today, max(spent_days))
        streak = 0
        cursor = start
        while cursor <= end:
            if cursor not in day_set:
                streak += 1
                max_no_spend = max(max_no_spend, streak)
            else:
                streak = 0
            cursor += timedelta(days=1)
    return no_spend_streak, max_no_spend




def get_date_range_presets(min_date: date, max_date: date) -> Dict[str, Tuple[date, date]]:
    today = date.today()
    month_start = today.replace(day=1)
    last_30 = max(min_date, today - timedelta(days=29))
    last_90 = max(min_date, today - timedelta(days=89))
    year_start = max(min_date, date(today.year, 1, 1))
    return {
        "This month": (max(min_date, month_start), max_date),
        "Last 30 days": (last_30, max_date),
        "Last 90 days": (last_90, max_date),
        "Year to date": (year_start, max_date),
        "All time": (min_date, max_date),
    }


def calculate_financial_health(expense_df: pd.DataFrame, savings_df: pd.DataFrame, monthly_limit_display: Optional[float]) -> Tuple[int, str, Dict[str, float]]:
    if expense_df.empty:
        return 50, "Add more data to get a reliable score.", {"budget": 50.0, "saving": 50.0, "consistency": 50.0}
    total_spent = safe_float(expense_df["display_abs_amount"].sum())
    monthly_spent = safe_float(expense_df[expense_df["month"] == month_key(date.today())]["display_abs_amount"].sum())
    savings_total = safe_float(savings_df["saved"].sum())
    budget_score = 70.0
    if monthly_limit_display and monthly_limit_display > 0:
        usage = monthly_spent / monthly_limit_display
        if usage <= 0.75:
            budget_score = 95.0
        elif usage <= 1.0:
            budget_score = max(65.0, 95.0 - (usage - 0.75) * 120)
        else:
            budget_score = max(20.0, 65.0 - (usage - 1.0) * 120)
    savings_rate = (savings_total / (savings_total + total_spent) * 100) if (savings_total + total_spent) > 0 else 0.0
    health_score, health_label, health_breakdown = calculate_financial_health(expense_df, savings_df, current_month_limit_display)
    saving_score = min(100.0, savings_rate * 4.0)
    daily = expense_df.groupby("date_only")["display_abs_amount"].sum()
    consistency = 100.0 if len(daily) <= 1 else max(30.0, 100.0 - min(daily.std() / max(daily.mean(), 1e-6), 2.0) * 25)
    score = round(budget_score * 0.4 + saving_score * 0.35 + consistency * 0.25)
    if score >= 80:
        label = "Excellent"
    elif score >= 65:
        label = "Good"
    elif score >= 50:
        label = "Needs attention"
    else:
        label = "Risky"
    return int(score), label, {"budget": round(budget_score, 1), "saving": round(saving_score, 1), "consistency": round(consistency, 1)}


def generate_smart_insights(expense_df: pd.DataFrame, income_df: pd.DataFrame, savings_df: pd.DataFrame, monthly_limit_display: Optional[float], display_currency: str) -> List[str]:
    insights: List[str] = []
    if expense_df.empty and income_df.empty:
        return ["Add a few transactions to unlock smart insights."]
    if not expense_df.empty:
        cat = category_summary(expense_df, "display_abs_amount")
        if not cat.empty:
            insights.append(f"Top expense category: {cat.iloc[0]['category']} — {format_money(cat.iloc[0]['display_abs_amount'], display_currency)}")
        monthly_spent = safe_float(expense_df[expense_df["month"] == month_key(date.today())]["display_abs_amount"].sum())
        if monthly_limit_display and monthly_limit_display > 0:
            usage = monthly_spent / monthly_limit_display
            if usage > 1:
                insights.append("You are over budget this month.")
            elif usage > 0.85:
                insights.append("You are getting close to your monthly budget cap.")
    if not income_df.empty and not expense_df.empty:
        net = safe_float(income_df["display_abs_amount"].sum()) - safe_float(expense_df["display_abs_amount"].sum())
        insights.append(f"Net balance for current filter: {format_money(net, display_currency)}")
    if not savings_df.empty:
        total_saved = safe_float(savings_df["saved"].sum())
        total_target = safe_float(savings_df["target"].sum())
        if total_target > 0:
            insights.append(f"Savings goals progress: {(total_saved / total_target) * 100:.1f}% complete.")
    return insights[:4]

def savings_progress(saved: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return max(0.0, min(saved / target, 1.0))


def plot_pie(cat_df: pd.DataFrame, value_col: str = "display_amount") -> None:
    if cat_df.empty:
        show_empty("Not enough data.")
        return
    colors = [CATEGORY_COLORS.get(c, CATEGORY_COLORS["Other"]) for c in cat_df["category"]]
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.pie(cat_df[value_col], labels=cat_df["category"], autopct="%1.1f%%", startangle=90, colors=colors)
    ax.axis("equal")
    st.pyplot(fig)
    plt.close(fig)


def csv_template() -> bytes:
    template = pd.DataFrame([
        {"date": date.today().isoformat(), "amount": 12.50, "currency": "EUR", "category": "Cafe", "note": "Coffee", "subscription": 0, "type": "expense"},
        {"date": date.today().isoformat(), "amount": 2500.00, "currency": "EUR", "category": "Salary", "note": "Monthly salary", "subscription": 0, "type": "income"},
    ])
    return template.to_csv(index=False).encode("utf-8")


# =========================================================
# SIDEBAR / SESSION
# =========================================================

for key, default in {
    "user_id": None,
    "username": None,
    "smart_note": "",
    "smart_preview": None,
}.items():
    st.session_state.setdefault(key, default)

st.sidebar.markdown("## 💸 Expense Tracker Pro+")
st.sidebar.caption("Improved version with faster entry, deeper analytics, bulk import, duplicate detection, and smarter subscription insights.")

if st.session_state.user_id:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Log out", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.username = None
        rerun()
else:
    mode = st.sidebar.radio("Mode", ["Login", "Register"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if mode == "Login":
        if st.sidebar.button("Login", use_container_width=True):
            user = get_user(username)
            if user and check_password(password, user["password_hash"]):
                st.session_state.user_id = int(user["id"])
                st.session_state.username = user["username"]
                rerun()
            else:
                st.sidebar.error("Invalid username or password.")
    else:
        if st.sidebar.button("Create account", use_container_width=True):
            ok, message = register_user(username, password)
            (st.sidebar.success if ok else st.sidebar.error)(message)

if not st.session_state.user_id:
    st.title("💸 Expense Tracker Pro+")
    st.write("Track spending, subscriptions, savings, imports, anomalies, and trends in one place.")
    a, b, c = st.columns(3)
    with a:
        metric_card("Fast capture", "Quick Add", "Paste natural text like: 2026-03-17 8.5 EUR coffee")
    with b:
        metric_card("Smarter insights", "Analytics+", "Forecasts, duplicates, anomalies, merchants, streaks")
    with c:
        metric_card("Safer data", "Bulk tools", "CSV import, template export, backup-ready downloads")
    st.stop()

user_id = require_login()
created_subs = upsert_monthly_subscriptions(user_id)
if created_subs:
    st.toast(f"Added {created_subs} recurring subscription(s) for this month.")

st.sidebar.divider()
display_currency = st.sidebar.selectbox("Display currency", SUPPORTED_CURRENCIES, index=0)
st.sidebar.caption("Live FX rates via Frankfurter + NBU")

base_df = load_expenses(user_id)
base_display_df = enrich_expenses(base_df, display_currency)
savings_df = load_savings(user_id)

min_date = base_display_df["date"].min().date() if not base_display_df.empty else date.today().replace(day=1)
max_date = base_display_df["date"].max().date() if not base_display_df.empty else date.today()
default_start = max(min_date, date.today().replace(day=1))
default_end = max_date

with st.sidebar:
    st.markdown("### Global filters")
    presets = get_date_range_presets(min_date, max_date)
    preset_name = st.selectbox("Quick range", list(presets.keys()), index=0)
    preset_start, preset_end = presets[preset_name]
    start_date = st.date_input("From", value=preset_start, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    end_date = st.date_input("To", value=preset_end, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    category_filter = st.multiselect("Categories", options=DEFAULT_CATEGORIES)
    search_query = st.text_input("Search text", placeholder="merchant, note, category")
    subs_only_global = st.checkbox("Subscriptions only")

filtered_df = apply_filters(base_display_df, start_date, end_date, category_filter, search_query, subs_only_global)
expense_df = filtered_df[filtered_df["type"] == "expense"].copy()
income_df = filtered_df[filtered_df["type"] == "income"].copy()

PAGES = [
    "Dashboard",
    "Quick Add",
    "Add Expense",
    "Manage Expenses",
    "Subscriptions",
    "Savings",
    "Analytics",
    "Import / Export",
]
page = st.sidebar.radio("Navigation", PAGES)

st.title("💸 Expense Tracker Pro+")
st.caption(f"{start_date.isoformat()} → {end_date.isoformat()} · {len(filtered_df)} filtered transactions")


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":
    total_spent = safe_float(expense_df["display_abs_amount"].sum())
    total_income = safe_float(income_df["display_abs_amount"].sum())
    net_balance = total_income - total_spent
    avg_tx = safe_float(expense_df["display_abs_amount"].mean())
    tx_count = int(len(filtered_df))
    active_days = int(filtered_df["date_only"].nunique()) if not filtered_df.empty else 0
    avg_day = total_spent / active_days if active_days else 0.0
    current_month_limit_eur = get_monthly_limit(user_id)
    current_month_key = month_key(date.today())
    current_month_df = base_display_df[(base_display_df["month"] == current_month_key) & (base_display_df["type"] == "expense")].copy()
    this_month_spent = safe_float(current_month_df["display_abs_amount"].sum())
    current_month_limit_display = convert_from_eur(current_month_limit_eur, display_currency) if current_month_limit_eur is not None else None
    budget_left = max(safe_float(current_month_limit_display) - this_month_spent, 0.0) if current_month_limit_display is not None else None
    forecast_value = month_forecast(base_display_df)
    no_spend_streak, best_no_spend_streak = streak_metrics(base_display_df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total spent", format_money(total_spent, display_currency), f"{tx_count} transactions")
    with c2:
        metric_card("Total income", format_money(total_income, display_currency), f"Net: {format_money(net_balance, display_currency)}")
    with c3:
        metric_card("Average expense", format_money(avg_tx, display_currency), f"Month forecast: {format_money(forecast_value, display_currency)}")
    with c4:
        if current_month_limit_display is not None:
            metric_card("Budget left", format_money(budget_left, display_currency), f"Budget: {format_money(current_month_limit_display, display_currency)}")
        else:
            metric_card("Budget left", "Not set", "Set a monthly budget below")

    m1, m2, m3, m4 = st.columns(4)
    top_cat = category_summary(expense_df, "display_abs_amount")
    top_cat_name = top_cat.iloc[0]["category"] if not top_cat.empty else "—"
    biggest_tx = safe_float(expense_df["display_abs_amount"].max())
    savings_total = safe_float(savings_df["saved"].sum())
    savings_rate = (savings_total / (savings_total + total_spent) * 100) if (savings_total + total_spent) > 0 else 0.0
    health_score, health_label, health_breakdown = calculate_financial_health(expense_df, savings_df, current_month_limit_display)
    with m1:
        st.metric("Top category", top_cat_name)
    with m2:
        st.metric("Largest expense", format_money(biggest_tx, display_currency))
    with m3:
        st.metric("Savings rate", f"{savings_rate:.1f}%")
    with m4:
        st.metric("Health score", f"{health_score}/100", help=f"{health_label} · Budget {health_breakdown['budget']}, Saving {health_breakdown['saving']}, Consistency {health_breakdown['consistency']}")

    left, right = st.columns([1.4, 1])
    with left:
        section("Category overview", "Biggest spending buckets for the current filter set.")
        cat_df = category_summary(expense_df, "display_abs_amount")
        if cat_df.empty:
            show_empty("Add a few transactions to unlock the dashboard.")
        else:
            st.bar_chart(cat_df.set_index("category"))
            share_df = cat_df.copy()
            share_df["share"] = (share_df["display_amount"] / share_df["display_amount"].sum() * 100).round(1)
            st.dataframe(share_df, use_container_width=True, hide_index=True)
        end_section()
    with right:
        section("Category split", "Pie view for the same filtered range.")
        plot_pie(category_summary(expense_df, "display_abs_amount"), "display_abs_amount")
        end_section()

    left2, right2 = st.columns([1.1, 1])
    with left2:
        section("Budget pacing", "Compares this month’s spending with month progress.")
        limit_input = st.number_input(
            f"Monthly budget ({display_currency})",
            min_value=0.0,
            value=safe_float(current_month_limit_display),
            step=10.0,
        )
        if st.button("Save monthly budget", use_container_width=True):
            set_monthly_limit(user_id, convert_to_eur(limit_input, display_currency))
            st.success("Budget saved.")
            rerun()
        if current_month_limit_display:
            elapsed_pct = date.today().day / pd.Timestamp.today().days_in_month
            spent_pct = this_month_spent / current_month_limit_display if current_month_limit_display > 0 else 0
            pace_delta = spent_pct - elapsed_pct
            st.progress(min(max(spent_pct, 0.0), 1.0))
            st.write(f"Spent: **{format_money(this_month_spent, display_currency)}**")
            st.write(f"Month progress: **{elapsed_pct * 100:.1f}%**")
            st.write(f"Budget used: **{spent_pct * 100:.1f}%**")
            if pace_delta > 0.08:
                st.warning("You are spending faster than the month is passing.")
            elif pace_delta < -0.08:
                st.success("You are ahead of budget pace.")
            else:
                st.info("You are roughly on pace.")
            days_left = pd.Timestamp.today().days_in_month - date.today().day
            suggested_daily = budget_left / max(days_left, 1)
            st.caption(f"Suggested daily cap for the rest of the month: {format_money(suggested_daily, display_currency)}")
        else:
            show_empty("Set a monthly budget to unlock budget pacing.")
        end_section()
    with right2:
        section("Live FX widget", "Reference rates used for display conversion.")
        eur_rates = get_rates_map("EUR")
        usd_rates = get_rates_map("USD")
        fx_df = pd.DataFrame([
            {"Pair": "EUR / USD", "Rate": round(eur_rates.get("USD", 0.0), 4)},
            {"Pair": "EUR / UAH", "Rate": round(eur_rates.get("UAH", 0.0), 4)},
            {"Pair": "USD / UAH", "Rate": round(usd_rates.get("UAH", 0.0), 4)},
        ])
        st.dataframe(fx_df, use_container_width=True, hide_index=True)
        end_section()

    insight_box = generate_smart_insights(expense_df, income_df, savings_df, current_month_limit_display, display_currency)
    with st.expander("Smart insights", expanded=True):
        for item in insight_box:
            st.write(f"- {item}")

    low, high = st.columns(2)
    with low:
        section("Recent expenses", "Last 12 items in the filtered range.")
        recent = filtered_df.sort_values("date", ascending=False).head(12)
        if recent.empty:
            show_empty("No expenses in the selected range.")
        else:
            for _, row in recent.iterrows():
                badge = f'<span class="badge" style="background:{CATEGORY_COLORS.get(row["category"], CATEGORY_COLORS["Other"])}">{row["category"]}</span>'
                sub_badge = '<span class="badge" style="background:#3b82f6">Subscription</span>' if int(row["subscription"]) == 1 else ""
                st.markdown(
                    f'<div class="feed-row"><div>{badge} {sub_badge}<br><span class="small-muted">{row["date_only"]} · {row["note"] or row["merchant"]}</span></div>'
                    f'<div><strong>{format_money(row["display_amount"], display_currency)}</strong></div></div>',
                    unsafe_allow_html=True,
                )
        end_section()
    with high:
        section("Savings goals", "Quick progress summary.")
        if savings_df.empty:
            show_empty("No savings goals yet.")
        else:
            for _, row in savings_df.iterrows():
                progress = savings_progress(row["saved"], row["target"])
                st.write(f"**{row['name']}** — {format_money(row['saved'], 'EUR')} / {format_money(row['target'], 'EUR')}")
                st.progress(progress)
        end_section()


# =========================================================
# QUICK ADD
# =========================================================

elif page == "Quick Add":
    section("Quick Add", "Paste a short sentence, preview the parsed entry, then save it.")
    quick_text = st.text_input(
        "Quick entry",
        value=st.session_state.smart_note,
        placeholder="Examples: 2026-03-17 8.5 EUR coffee at Starbucks | 17.03 24.90 groceries | 12 usd uber",
    )
    preview = parse_quick_add(quick_text)
    st.session_state.smart_note = quick_text
    if quick_text and preview["ok"]:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Amount", format_money(preview["amount"], preview["currency"]))
        with c2:
            st.metric("Date", str(preview["date"]))
        with c3:
            st.metric("Category", str(preview["category"]))
        with c4:
            st.metric("Type", preview["tx_type"].title())
        category_options = INCOME_CATEGORIES if preview["tx_type"] == "income" else DEFAULT_CATEGORIES
        default_index = category_options.index(preview["category"]) if preview["category"] in category_options else len(category_options)-1
        manual_category = st.selectbox("Adjust category", category_options, index=default_index)
        note = st.text_input("Note / merchant", value=str(preview["note"]))
        subscription = st.checkbox("Recurring monthly subscription", value=bool(preview["subscription"]), disabled=preview["tx_type"] == "income")
        if st.button("Save quick entry", type="primary", use_container_width=True):
            add_transaction(
                user_id,
                preview["date"],
                preview["amount"],
                manual_category,
                preview["currency"],
                preview["tx_type"],
                note,
                1 if subscription else 0,
            )
            st.success("Quick entry saved.")
            st.session_state.smart_note = ""
            rerun()
    elif quick_text:
        st.warning(preview["error"])
    end_section()

    section("Why this helps", "Useful for mobile, quick logging, and chat-style input.")
    st.write("The parser detects date, amount, currency, subscription hints, and suggests a category from the note.")
    end_section()


# =========================================================
# ADD EXPENSE
# =========================================================

elif page == "Add Expense":
    section("Add transaction", "Manual form for both expenses and income.")
    col1, col2 = st.columns(2)
    with col1:
        tx_type = st.selectbox("Transaction type", ["expense", "income"], format_func=lambda x: x.title())
        amount = st.number_input("Amount", min_value=0.01, step=0.5)
        currency = st.selectbox("Currency", SUPPORTED_CURRENCIES)
        note = st.text_input("Note / description")
        suggested_category = infer_category(note, fallback="Other Income" if tx_type == "income" else "Other") if note else ("Other Income" if tx_type == "income" else "Other")
    with col2:
        expense_date = st.date_input("Date", value=date.today())
        category_options = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
        category = st.selectbox("Category", category_options, index=category_options.index(suggested_category) if suggested_category in category_options else len(category_options)-1)
        is_subscription = st.checkbox("Recurring monthly subscription", disabled=tx_type == "income")

    if note:
        st.caption(f"Suggested category from note: {suggested_category}")
    if st.button("Save transaction", use_container_width=True):
        add_transaction(user_id, expense_date, amount, category, currency, tx_type, note, 1 if is_subscription else 0)
        st.success("Transaction added.")
        rerun()
    end_section()


# =========================================================
# MANAGE EXPENSES
# =========================================================

elif page == "Manage Expenses":
    section("Manage expenses", "Search, edit, delete, and inspect duplicates.")
    if filtered_df.empty:
        show_empty("No matching expenses.")
    else:
        managed = filtered_df.copy().sort_values("date", ascending=False)
        managed["label"] = (
            managed["date"].dt.strftime("%Y-%m-%d") + " | "
            + managed["category"].astype(str) + " | "
            + managed["original_amount"].round(2).astype(str) + " "
            + managed["currency"].astype(str) + " | "
            + managed["note"].fillna("")
        )
        selected_label = st.selectbox("Select transaction", managed["label"].tolist())
        row = managed.loc[managed["label"] == selected_label].iloc[0]

        c1, c2 = st.columns(2)
        with c1:
            edit_date = st.date_input("Date", value=row["date"].date(), key="edit_date")
            edit_original_amount = st.number_input("Original amount", min_value=0.0, value=float(row["original_amount"]), step=0.5)
            edit_currency = st.selectbox("Original currency", SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(row["currency"]))
        with c2:
            edit_type = st.selectbox("Transaction type", ["expense", "income"], index=0 if row["type"] == "expense" else 1, format_func=lambda x: x.title())
            category_options = DEFAULT_CATEGORIES if edit_type == "expense" else INCOME_CATEGORIES
            current_category = row["category"] if row["category"] in category_options else category_options[-1]
            edit_category = st.selectbox("Category", category_options, index=category_options.index(current_category))
            edit_note = st.text_input("Note / description", value=str(row["note"] or ""))
            edit_subscription = st.checkbox("Recurring monthly subscription", value=bool(row["subscription"]), disabled=edit_type == "income")

        b1, b2 = st.columns(2)
        if b1.button("Save changes", use_container_width=True):
            update_transaction(user_id, int(row["id"]), edit_date, edit_original_amount, edit_currency, edit_category, edit_note, edit_subscription, edit_type)
            st.success("Expense updated.")
            rerun()
        if b2.button("Delete expense", use_container_width=True):
            delete_expense(user_id, int(row["id"]))
            st.success("Expense deleted.")
            rerun()

        st.divider()
        st.write("**Filtered table**")
        table = managed[["date_only", "type", "category", "merchant", "note", "original_amount", "currency", "display_amount", "subscription"]].copy()
        st.dataframe(table, use_container_width=True, hide_index=True)
    end_section()

    section("Duplicate finder", "Flags items with the same date, amount, category, and note.")
    dups = detect_duplicates(filtered_df.assign(amount=filtered_df["amount"].abs()))
    if dups.empty:
        show_empty("No duplicates detected in the current filter range.")
    else:
        st.dataframe(
            dups[["date_only", "category", "note", "original_amount", "currency", "dup_count"]],
            use_container_width=True,
            hide_index=True,
        )
    end_section()


# =========================================================
# SUBSCRIPTIONS
# =========================================================

elif page == "Subscriptions":
    section("Recurring subscriptions", "Grouped view, annual cost estimate, and concentration risk.")
    subs = filtered_df[filtered_df["subscription"] == 1].copy()
    if subs.empty:
        show_empty("No subscriptions in the selected range.")
    else:
        grouped = subs.groupby(["category", "merchant", "currency"], as_index=False).agg(
            monthly_eur=("amount", "mean"),
            monthly_display=("display_amount", "mean"),
            transactions=("id", "count"),
            last_seen=("date", "max"),
        ).sort_values("monthly_display", ascending=False)
        total_monthly = safe_float(grouped["monthly_display"].sum())
        annualized = total_monthly * 12
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Estimated monthly total", format_money(total_monthly, display_currency))
        with c2:
            st.metric("Estimated annual total", format_money(annualized, display_currency))
        with c3:
            top_share = grouped.iloc[0]["monthly_display"] / total_monthly * 100 if total_monthly else 0
            st.metric("Largest subscription share", f"{top_share:.1f}%")
        grouped["last_seen"] = pd.to_datetime(grouped["last_seen"]).dt.date
        st.dataframe(grouped, use_container_width=True, hide_index=True)
        st.bar_chart(grouped.set_index("merchant")[["monthly_display"]])
    end_section()


# =========================================================
# SAVINGS
# =========================================================

elif page == "Savings":
    section("Savings goals", "Create goals, add progress, and keep track of totals.")
    c1, c2, c3 = st.columns(3)
    with c1:
        goal_name = st.text_input("Goal name")
    with c2:
        goal_target = st.number_input("Target (€)", min_value=0.0, step=10.0)
    with c3:
        goal_saved = st.number_input("Already saved (€)", min_value=0.0, step=10.0)

    if st.button("Add goal", use_container_width=True):
        if not goal_name.strip():
            st.error("Goal name cannot be empty.")
        else:
            supabase.table("savings").insert({
                "user_id": user_id,
                "name": goal_name.strip(),
                "target": float(goal_target),
                "saved": float(goal_saved),
            }).execute()
            st.success("Savings goal added.")
            rerun()

    if savings_df.empty:
        show_empty("No savings goals yet.")
    else:
        total_target = safe_float(savings_df["target"].sum())
        total_saved = safe_float(savings_df["saved"].sum())
        st.caption(f"Combined progress: {format_money(total_saved, 'EUR')} / {format_money(total_target, 'EUR')}")
        for _, row in savings_df.iterrows():
            st.write(f"### {row['name']}")
            progress = savings_progress(row["saved"], row["target"])
            st.progress(progress)
            st.caption(f"Saved: {format_money(row['saved'], 'EUR')} / Target: {format_money(row['target'], 'EUR')}")
            add_more = st.number_input(f"Add money to {row['name']}", min_value=0.0, step=10.0, key=f"save_{row['id']}")
            x1, x2 = st.columns(2)
            if x1.button(f"Update {row['name']}", key=f"upd_{row['id']}", use_container_width=True):
                supabase.table("savings").update({"saved": float(row["saved"]) + float(add_more)}).eq("id", int(row["id"])).eq("user_id", user_id).execute()
                st.success("Savings updated.")
                rerun()
            if x2.button(f"Delete {row['name']}", key=f"del_{row['id']}", use_container_width=True):
                supabase.table("savings").delete().eq("id", int(row["id"])).eq("user_id", user_id).execute()
                st.success("Goal deleted.")
                rerun()
            st.divider()
    end_section()


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":
    section("Advanced analytics", "Monthly trend, merchants, weekday patterns, anomalies, and Pareto view.")
    analytics_df = expense_df.copy()
    if analytics_df.empty:
        show_empty("No data for analytics in the current range.")
        end_section()
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Monthly trend**")
            monthly = monthly_series(analytics_df, "display_abs_amount")
            if monthly.empty:
                show_empty("Not enough monthly data.")
            else:
                st.line_chart(monthly.set_index("month"))
        with c2:
            st.write("**Weekday pattern**")
            weekdays = weekday_summary(analytics_df, "display_abs_amount")
            st.bar_chart(weekdays.set_index("weekday"))
        end_section()

        left, right = st.columns(2)
        with left:
            section("Top merchants", "Based on the first meaningful words in the note.")
            merchants = merchant_summary(analytics_df, "display_abs_amount")
            if merchants.empty:
                show_empty("No merchant-like notes found.")
            else:
                st.dataframe(merchants.head(15), use_container_width=True, hide_index=True)
            end_section()
        with right:
            section("Anomaly detector", "Flags unusually high transactions within each category.")
            anomalies = detect_anomalies(analytics_df.assign(display_amount=analytics_df["display_abs_amount"]))
            if anomalies.empty:
                show_empty("No strong anomalies detected.")
            else:
                st.dataframe(
                    anomalies[["date_only", "category", "note", "display_amount", "currency"]].sort_values("display_amount", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )
            end_section()

        section("Pareto view", "Shows how much your top categories explain total spending.")
        cat = category_summary(analytics_df, "display_abs_amount")
        if cat.empty:
            show_empty("No data.")
        else:
            pareto = cat.copy()
            pareto["cum_pct"] = (pareto["display_amount"].cumsum() / pareto["display_amount"].sum() * 100).round(1)
            st.dataframe(pareto, use_container_width=True, hide_index=True)
            hits_80 = pareto[pareto["cum_pct"] <= 80.0]
            st.caption(f"{len(hits_80) if not hits_80.empty else 1} category(ies) explain roughly 80% of the selected spending.")
        end_section()

        section("Spending calendar", "Daily total view for the selected period.")
        cal = analytics_df.groupby("date_only", as_index=False)["display_abs_amount"].sum().sort_values("date_only")
        cal = cal.rename(columns={"display_abs_amount": "display_amount"})
        cal["weekday"] = pd.to_datetime(cal["date_only"]).dt.day_name()
        st.dataframe(cal, use_container_width=True, hide_index=True)
        end_section()


# =========================================================
# IMPORT / EXPORT
# =========================================================

elif page == "Import / Export":
    section("Export data", "Filtered or full downloads for backup and analysis.")
    export_df = filtered_df.copy()
    full_df = base_display_df.copy()

    if export_df.empty and full_df.empty:
        show_empty("Nothing to export yet.")
    else:
        def to_excel_bytes(df: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Expenses")
            return output.getvalue()

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download filtered CSV", export_df.to_csv(index=False).encode("utf-8"), "expenses_filtered.csv", "text/csv", use_container_width=True)
            st.download_button("Download filtered Excel", to_excel_bytes(export_df), "expenses_filtered.xlsx", use_container_width=True)
        with c2:
            st.download_button("Download full CSV", full_df.to_csv(index=False).encode("utf-8"), "expenses_full.csv", "text/csv", use_container_width=True)
            st.download_button("Download full Excel", to_excel_bytes(full_df), "expenses_full.xlsx", use_container_width=True)
    end_section()

    section("CSV template", "Use this format for bulk import. You can include type=income or expense.")
    st.download_button("Download CSV template", csv_template(), "expense_import_template.csv", "text/csv", use_container_width=True)
    end_section()

    section("Bulk import", "Expected columns: date, amount, currency, category, note, subscription, type.")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_csv(uploaded)
            st.write("**Preview**")
            st.dataframe(incoming.head(10), use_container_width=True, hide_index=True)
            required = {"date", "amount"}
            if not required.issubset(set(incoming.columns.str.lower())):
                st.error("CSV must contain at least: date, amount")
            else:
                incoming.columns = [c.lower().strip() for c in incoming.columns]
                incoming["currency"] = incoming.get("currency", "EUR").fillna("EUR")
                incoming["category"] = incoming.get("category", "Other").fillna("Other")
                incoming["note"] = incoming.get("note", "").fillna("")
                incoming["subscription"] = pd.to_numeric(incoming.get("subscription", 0), errors="coerce").fillna(0).astype(int)
                incoming["type"] = incoming.get("type", "expense").fillna("expense").astype(str).str.lower()
                valid_rows = []
                for _, row in incoming.iterrows():
                    try:
                        d = pd.to_datetime(row["date"]).date()
                        amt = safe_float(row["amount"])
                        cur = str(row.get("currency", "EUR")).upper()
                        cat = str(row.get("category", "Other"))
                        note = str(row.get("note", ""))
                        sub = int(row.get("subscription", 0))
                        tx_type = "income" if str(row.get("type", "expense")).lower() == "income" else "expense"
                        valid_categories = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
                        if cat not in valid_categories:
                            cat = infer_category(note, fallback="Other Income" if tx_type == "income" else "Other")
                        valid_rows.append((d, amt, cur, cat, note, sub, tx_type))
                    except Exception:
                        continue
                st.caption(f"Valid rows ready to import: {len(valid_rows)}")
                if valid_rows and st.button("Import rows", use_container_width=True, type="primary"):
                    for d, amt, cur, cat, note, sub, tx_type in valid_rows:
                        add_transaction(user_id, d, amt, cat, cur, tx_type, note, sub)
                    st.success(f"Imported {len(valid_rows)} row(s).")
                    rerun()
        except Exception as exc:
            st.error(f"Failed to read CSV: {exc}")
    end_section()
