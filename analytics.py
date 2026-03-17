from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from config import CATEGORY_COLORS
from db import convert_from_eur
from utils import extract_merchant, format_money, month_key, safe_float


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
        l("This month", "Цей місяць", "Dieser Monat"): (max(min_date, month_start), max_date),
        l("Last 30 days", "Останні 30 днів", "Letzte 30 Tage"): (last_30, max_date),
        l("Last 90 days", "Останні 90 днів", "Letzte 90 Tage"): (last_90, max_date),
        l("Year to date", "Від початку року", "Jahr bis heute"): (year_start, max_date),
        l("All time", "Увесь час", "Gesamter Zeitraum"): (min_date, max_date),
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
        return [l("Add a few transactions to unlock smart insights.", "Додай кілька транзакцій, щоб відкрити розумні інсайти.", "Füge einige Transaktionen hinzu, um smarte Insights freizuschalten.")]
    if not expense_df.empty:
        cat = category_summary(expense_df, "display_abs_amount")
        if not cat.empty:
            insights.append(
                l(
                    "Top expense category: {category} — {amount}",
                    "Найбільша категорія витрат: {category} — {amount}",
                    "Größte Ausgabenkategorie: {category} — {amount}",
                ).format(category=lcat(cat.iloc[0]["category"]), amount=format_money(cat.iloc[0]["display_abs_amount"], display_currency))
            )
        monthly_spent = safe_float(expense_df[expense_df["month"] == month_key(date.today())]["display_abs_amount"].sum())
        if monthly_limit_display and monthly_limit_display > 0:
            usage = monthly_spent / monthly_limit_display
            if usage > 1:
                insights.append(l("You are over budget this month.", "Цього місяця ти перевищив бюджет.", "Diesen Monat liegst du über dem Budget."))
            elif usage > 0.85:
                insights.append(l("You are getting close to your monthly budget cap.", "Ти наближаєшся до місячного ліміту бюджету.", "Du näherst dich deinem monatlichen Budgetlimit."))
    if not income_df.empty and not expense_df.empty:
        net = safe_float(income_df["display_abs_amount"].sum()) - safe_float(expense_df["display_abs_amount"].sum())
        insights.append(
            l("Net balance for current filter: {amount}", "Чистий баланс для поточного фільтра: {amount}", "Nettosaldo für den aktuellen Filter: {amount}").format(amount=format_money(net, display_currency))
        )
    if not savings_df.empty:
        total_saved = safe_float(savings_df["saved"].sum())
        total_target = safe_float(savings_df["target"].sum())
        if total_target > 0:
            insights.append(
                l("Savings goals progress: {pct:.1f}% complete.", "Прогрес цілей заощаджень: {pct:.1f}% виконано.", "Fortschritt der Sparziele: {pct:.1f}% erreicht.").format(pct=(total_saved / total_target) * 100)
            )
    return insights[:4]


def savings_progress(saved: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return max(0.0, min(saved / target, 1.0))


def plot_pie(cat_df: pd.DataFrame, value_col: str = "display_amount") -> None:
    if cat_df.empty:
        show_empty(l("Not enough data.", "Недостатньо даних.", "Nicht genug Daten."))
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
