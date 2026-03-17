from __future__ import annotations

import calendar
import os
from datetime import date, timedelta
from typing import Dict, Optional

import bcrypt
import pandas as pd
import requests
from supabase import Client, create_client

from utils import month_key, safe_float

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user(username: str):
    res = supabase.table("users").select("*").eq("username", username.strip()).limit(1).execute()
    return res.data[0] if res.data else None


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


def get_category_budgets(user_id: int) -> dict[str, float]:
    res = (
        supabase.table("category_budgets")
        .select("category, monthly_limit")
        .eq("user_id", int(user_id))
        .execute()
    )
    return {
        str(row["category"]): float(row["monthly_limit"])
        for row in (res.data or [])
        if row.get("category") is not None and row.get("monthly_limit") is not None
    }


def set_category_budget(user_id: int, category: str, amount_eur: float) -> None:
    payload = {
        "user_id": int(user_id),
        "category": str(category),
        "monthly_limit": float(amount_eur),
    }
    supabase.table("category_budgets").upsert(
        payload,
        on_conflict="user_id,category",
    ).execute()


def execute_expense_write(write_fn, payload: Dict[str, object]) -> None:
    try:
        write_fn(payload)
    except Exception:
        fallback_payload = dict(payload)
        fallback_payload.pop("type", None)
        write_fn(fallback_payload)


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
        "type": tx_type,
    }
    execute_expense_write(lambda p: supabase.table("expenses").insert(p).execute(), payload)


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
        "type": tx_type,
    }
    execute_expense_write(
        lambda p: supabase.table("expenses").update(p).eq("id", int(expense_id)).eq("user_id", int(user_id)).execute(),
        payload,
    )


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
    month_start = date(today.year, today.month, 1)
    month_end_day = calendar.monthrange(today.year, today.month)[1]
    next_month_start = month_start + timedelta(days=month_end_day)
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
            .gte("date", month_start.isoformat())
            .lt("date", next_month_start.isoformat())
            .limit(1)
            .execute()
        )
        if not exists.data:
            supabase.table("expenses").insert({
                "user_id": user_id,
                "date": month_start.isoformat(),
                "amount": float(row["amount"]),
                "category": str(row["category"]),
                "currency": str(row["currency"] or "EUR"),
                "subscription": 1,
                "note": str(row["note"]),
            }).execute()
            created += 1
    return created
