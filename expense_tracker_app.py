from __future__ import annotations

import io
import os
import calendar
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
os.environ.setdefault("SUPABASE_URL", SUPABASE_URL)
os.environ.setdefault("SUPABASE_KEY", SUPABASE_KEY)

from config import (
    CATEGORY_COLORS,
    CATEGORY_TRANSLATIONS,
    DEFAULT_CATEGORIES,
    INCOME_CATEGORIES,
    STYLE,
    SUPPORTED_CURRENCIES,
)
from utils import format_money, infer_category, month_key, parse_quick_add, safe_float
from db import (
    add_transaction,
    check_password,
    convert_from_eur,
    convert_to_eur,
    delete_expense,
    get_category_budgets,
    get_monthly_limit,
    get_rates_map as db_get_rates_map,
    get_user,
    load_expenses,
    load_savings,
    set_category_budget,
    set_monthly_limit,
    update_transaction,
    upsert_monthly_subscriptions,
    hash_password,
)
from analytics import (
    apply_filters,
    category_summary,
    check_category_budgets,
    csv_template,
    detect_anomalies,
    detect_duplicates,
    enrich_expenses,
    get_month_options,
    merchant_summary,
    monthly_series,
    savings_progress,
    streak_metrics,
    weekday_summary,
    month_forecast,
    calculate_financial_health,
)

st.markdown(STYLE, unsafe_allow_html=True)


# =========================================================
# UTILITIES
# =========================================================

def rerun() -> None:
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


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


# =========================================================
# AUTH / DATA ACCESS
# =========================================================

def require_login() -> int:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return int(user_id)


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, l("Username must have at least 3 characters.", "Ім'я користувача має містити щонайменше 3 символи.", "Der Benutzername muss mindestens 3 Zeichen lang sein.")
    if len(password) < 6:
        return False, l("Password must have at least 6 characters.", "Пароль має містити щонайменше 6 символів.", "Das Passwort muss mindestens 6 Zeichen lang sein.")
    exists = supabase.table("users").select("id").eq("username", username).limit(1).execute()
    if exists.data:
        return False, l("This username already exists.", "Такий користувач уже існує.", "Dieser Benutzername existiert bereits.")
    supabase.table("users").insert({
        "username": username,
        "password_hash": hash_password(password).decode("utf-8"),
    }).execute()
    return True, l("Account created successfully.", "Акаунт успішно створено.", "Konto erfolgreich erstellt.")


@st.cache_data(ttl=3600)
def get_rates_map_cached(base: str = "EUR"):
    return db_get_rates_map(base)


def get_rates_map(base: str = "EUR"):
    return get_rates_map_cached(base)


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
        monthly_spent = safe_float(expense_df[expense_df["month"] == pd.Timestamp.today().strftime("%Y-%m")]["display_abs_amount"].sum())
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


# =========================================================
# DATA SHAPING / ANALYTICS
# =========================================================

TRANSLATIONS = {
    "en": {
        "app_title": "💸 Expense Tracker Pro+",
        "sidebar_title": "## 💸 Expense Tracker Pro+",
        "sidebar_caption": "Improved version with faster entry, deeper analytics, bulk import, duplicate detection, and smarter subscription insights.",
        "language": "Language",
        "logged_in_as": "Logged in as {username}",
        "log_out": "Log out",
        "mode": "Mode",
        "login": "Login",
        "register": "Register",
        "username": "Username",
        "password": "Password",
        "create_account": "Create account",
        "invalid_credentials": "Invalid username or password.",
        "welcome_text": "Track spending, subscriptions, savings, imports, anomalies, and trends in one place.",
        "fast_capture": "Fast capture",
        "quick_add": "Quick Add",
        "quick_add_desc": "Paste natural text like: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Smarter insights",
        "analytics_plus": "Analytics+",
        "analytics_plus_desc": "Forecasts, duplicates, anomalies, merchants, streaks",
        "safe_data": "Safer data",
        "bulk_tools": "Bulk tools",
        "bulk_tools_desc": "CSV import, template export, backup-ready downloads",
        "display_currency": "Display currency",
        "fx_caption": "Live FX rates via Frankfurter + NBU",
        "global_filters": "Global filters",
        "quick_range": "Quick range",
        "from": "From",
        "to": "To",
        "categories": "Categories",
        "search_text": "Search text",
        "search_placeholder": "merchant, note, category",
        "subscriptions_only": "Subscriptions only",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "add_expense": "Add Expense",
        "manage_expenses": "Manage Expenses",
        "subscriptions": "Subscriptions",
        "savings": "Savings",
        "analytics": "Analytics",
        "import_export": "Import / Export",
        "filtered_transactions": "filtered transactions",
        "top_category": "Top category",
        "largest_expense": "Largest expense",
        "savings_rate": "Savings rate",
        "health_score": "Health score",
        "budget": "Budget",
        "saving": "Saving",
        "consistency": "Consistency",
    },
    "uk": {
        "app_title": "💸 Трекер витрат Pro+",
        "sidebar_title": "## 💸 Трекер витрат Pro+",
        "sidebar_caption": "Покращена версія з швидким додаванням, глибшою аналітикою, імпортом, пошуком дублікатів і розумнішими підписками.",
        "language": "Мова",
        "logged_in_as": "Ви увійшли як {username}",
        "log_out": "Вийти",
        "mode": "Режим",
        "login": "Увійти",
        "register": "Реєстрація",
        "username": "Ім'я користувача",
        "password": "Пароль",
        "create_account": "Створити акаунт",
        "invalid_credentials": "Неправильне ім'я користувача або пароль.",
        "welcome_text": "Відстежуй витрати, підписки, заощадження, імпорт, аномалії та тренди в одному місці.",
        "fast_capture": "Швидке внесення",
        "quick_add": "Швидке додавання",
        "quick_add_desc": "Встав текст у стилі: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Розумні інсайти",
        "analytics_plus": "Аналітика+",
        "analytics_plus_desc": "Прогнози, дублікати, аномалії, продавці, streaks",
        "safe_data": "Безпечні дані",
        "bulk_tools": "Масові інструменти",
        "bulk_tools_desc": "CSV імпорт, шаблон експорту, резервні копії",
        "display_currency": "Валюта відображення",
        "fx_caption": "Актуальні курси через Frankfurter + NBU",
        "global_filters": "Глобальні фільтри",
        "quick_range": "Швидкий період",
        "from": "Від",
        "to": "До",
        "categories": "Категорії",
        "search_text": "Пошук",
        "search_placeholder": "продавець, нотатка, категорія",
        "subscriptions_only": "Лише підписки",
        "navigation": "Навігація",
        "dashboard": "Дашборд",
        "add_expense": "Додати витрату",
        "manage_expenses": "Керування витратами",
        "subscriptions": "Підписки",
        "savings": "Заощадження",
        "analytics": "Аналітика",
        "import_export": "Імпорт / Експорт",
        "filtered_transactions": "відфільтрованих транзакцій",
        "top_category": "Топ категорія",
        "largest_expense": "Найбільша витрата",
        "savings_rate": "Норма заощаджень",
        "health_score": "Фінансовий рейтинг",
        "budget": "Бюджет",
        "saving": "Заощадження",
        "consistency": "Стабільність",
    },
    "de": {
        "app_title": "💸 Ausgaben-Tracker Pro+",
        "sidebar_title": "## 💸 Ausgaben-Tracker Pro+",
        "sidebar_caption": "Verbesserte Version mit schneller Erfassung, tieferen Analysen, Import, Duplikat-Erkennung und intelligenteren Abos.",
        "language": "Sprache",
        "logged_in_as": "Angemeldet als {username}",
        "log_out": "Abmelden",
        "mode": "Modus",
        "login": "Anmelden",
        "register": "Registrieren",
        "username": "Benutzername",
        "password": "Passwort",
        "create_account": "Konto erstellen",
        "invalid_credentials": "Ungültiger Benutzername oder Passwort.",
        "welcome_text": "Verfolge Ausgaben, Abos, Sparziele, Importe, Anomalien und Trends an einem Ort.",
        "fast_capture": "Schnelle Erfassung",
        "quick_add": "Schnell hinzufügen",
        "quick_add_desc": "Natürlichen Text einfügen wie: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Smarte Insights",
        "analytics_plus": "Analytics+",
        "analytics_plus_desc": "Prognosen, Duplikate, Anomalien, Händler, Streaks",
        "safe_data": "Sichere Daten",
        "bulk_tools": "Bulk-Tools",
        "bulk_tools_desc": "CSV-Import, Vorlagenexport, Backup-Downloads",
        "display_currency": "Anzeigewährung",
        "fx_caption": "Live-Wechselkurse via Frankfurter + NBU",
        "global_filters": "Globale Filter",
        "quick_range": "Schnellbereich",
        "from": "Von",
        "to": "Bis",
        "categories": "Kategorien",
        "search_text": "Suche",
        "search_placeholder": "Händler, Notiz, Kategorie",
        "subscriptions_only": "Nur Abos",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "add_expense": "Ausgabe hinzufügen",
        "manage_expenses": "Ausgaben verwalten",
        "subscriptions": "Abos",
        "savings": "Sparen",
        "analytics": "Analysen",
        "import_export": "Import / Export",
        "filtered_transactions": "gefilterte Transaktionen",
        "top_category": "Top-Kategorie",
        "largest_expense": "Größte Ausgabe",
        "savings_rate": "Sparquote",
        "health_score": "Finanz-Score",
        "budget": "Budget",
        "saving": "Sparen",
        "consistency": "Konstanz",
    },
}

def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "en")
    template = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template

def l(en: str, uk: str, de: str) -> str:
    lang = st.session_state.get("lang", "en")
    return {"en": en, "uk": uk, "de": de}.get(lang, en)


def lcat(category: str) -> str:
    lang = st.session_state.get("lang", "en")
    if lang == "en":
        return str(category)
    return CATEGORY_TRANSLATIONS.get(str(category), {}).get(lang, str(category))

def ltx(tx_type: str) -> str:
    mapping = {
        "expense": l("Expense", "Витрата", "Ausgabe"),
        "income": l("Income", "Дохід", "Einnahme"),
    }
    return mapping.get(str(tx_type).lower(), str(tx_type).title())

# =========================================================
# SIDEBAR / SESSION
# =========================================================

for key, default in {
    "user_id": None,
    "username": None,
    "smart_note": "",
    "smart_preview": None,
    "lang": "en",
}.items():
    st.session_state.setdefault(key, default)

st.sidebar.markdown(t("sidebar_title"))
st.sidebar.caption(t("sidebar_caption"))
st.session_state.lang = st.sidebar.selectbox(t("language"), ["en", "uk", "de"], index=["en","uk","de"].index(st.session_state.get("lang","en")), format_func=lambda x: {"en":"English","uk":"Українська","de":"Deutsch"}[x])

if st.session_state.user_id:
    st.sidebar.success(t("logged_in_as", username=st.session_state.username))
    if st.sidebar.button(t("log_out"), use_container_width=True):
        st.session_state.user_id = None
        st.session_state.username = None
        rerun()
else:
    mode = st.sidebar.radio(t("mode"), [t("login"), t("register")])
    username = st.sidebar.text_input(t("username"))
    password = st.sidebar.text_input(t("password"), type="password")
    if mode == t("login"):
        if st.sidebar.button(t("login"), use_container_width=True):
            user = get_user(username)
            if user and check_password(password, user["password_hash"]):
                st.session_state.user_id = int(user["id"])
                st.session_state.username = user["username"]
                rerun()
            else:
                st.sidebar.error(t("invalid_credentials"))
    else:
        if st.sidebar.button(t("create_account"), use_container_width=True):
            ok, message = register_user(username, password)
            (st.sidebar.success if ok else st.sidebar.error)(message)

if not st.session_state.user_id:
    st.title(t("app_title"))
    st.write(t("welcome_text"))
    a, b, c = st.columns(3)
    with a:
        metric_card(t("fast_capture"), t("quick_add"), t("quick_add_desc"))
    with b:
        metric_card(t("smart_insights"), t("analytics_plus"), t("analytics_plus_desc"))
    with c:
        metric_card(t("safe_data"), t("bulk_tools"), t("bulk_tools_desc"))
    st.stop()

user_id = require_login()
created_subs = upsert_monthly_subscriptions(user_id)
if created_subs:
    st.toast(f"{created_subs} {l("recurring subscription(s) added for this month.", "повторюваних підписок додано за цей місяць.", "wiederkehrende(s) Abonnement(s) für diesen Monat hinzugefügt.")}")

st.sidebar.divider()
display_currency = st.sidebar.selectbox(t("display_currency"), SUPPORTED_CURRENCIES, index=0)
st.sidebar.caption(t("fx_caption"))

base_df = load_expenses(user_id)
base_display_df = enrich_expenses(base_df, display_currency)
savings_df = load_savings(user_id)

min_date = base_display_df["date"].min().date() if not base_display_df.empty else date.today().replace(day=1)
max_date = base_display_df["date"].max().date() if not base_display_df.empty else date.today()
default_start = max(min_date, date.today().replace(day=1))
default_end = max_date

with st.sidebar:
    st.markdown(f"### {t("global_filters")}")
    presets = get_date_range_presets(min_date, max_date)
    preset_name = st.selectbox(t("quick_range"), list(presets.keys()), index=0)
    preset_start, preset_end = presets[preset_name]
    start_date = st.date_input(t("from"), value=preset_start, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    end_date = st.date_input(t("to"), value=preset_end, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    category_filter = st.multiselect(t("categories"), options=DEFAULT_CATEGORIES)
    search_query = st.text_input(t("search_text"), placeholder=t("search_placeholder"))
    subs_only_global = st.checkbox(t("subscriptions_only"))

filtered_df = apply_filters(base_display_df, start_date, end_date, category_filter, search_query, subs_only_global)
expense_df = filtered_df[filtered_df["type"] == "expense"].copy()
income_df = filtered_df[filtered_df["type"] == "income"].copy()

PAGES = [
    t("dashboard"),
    t("quick_add"),
    t("add_expense"),
    t("manage_expenses"),
    t("subscriptions"),
    t("savings"),
    t("analytics"),
    t("import_export"),
]
page = st.sidebar.radio(t("navigation"), PAGES)

st.title(t("app_title"))
st.caption(f"{start_date.isoformat()} → {end_date.isoformat()} · {len(filtered_df)} {t("filtered_transactions")}")


# =========================================================
# DASHBOARD
# =========================================================

if page == t("dashboard"):
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
    health_score, health_label, health_breakdown = calculate_financial_health(expense_df, savings_df, current_month_limit_display)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(l("Total spent", "Усього витрачено", "Gesamtausgaben"), format_money(total_spent, display_currency), f"{tx_count} transactions")
    with c2:
        metric_card(l("Total income", "Усього доходів", "Gesamteinnahmen"), format_money(total_income, display_currency), f"{l("Net", "Баланс", "Netto")}: {format_money(net_balance, display_currency)}")
    with c3:
        metric_card(l("Average expense", "Середня витрата", "Durchschnittliche Ausgabe"), format_money(avg_tx, display_currency), f"{l("Month forecast", "Прогноз на місяць", "Monatsprognose")}: {format_money(forecast_value, display_currency)}")
    with c4:
        if current_month_limit_display is not None:
            metric_card(l("Budget left", "Залишок бюджету", "Verbleibendes Budget"), format_money(budget_left, display_currency), f"Budget: {format_money(current_month_limit_display, display_currency)}")
        else:
            metric_card(l("Budget left", "Залишок бюджету", "Verbleibendes Budget"), l("Not set", "Не задано", "Nicht festgelegt"), l("Set a monthly budget below", "Задай місячний бюджет нижче", "Lege unten ein Monatsbudget fest"))

    m1, m2, m3, m4 = st.columns(4)
    top_cat = category_summary(expense_df, "display_abs_amount")
    top_cat_name = lcat(top_cat.iloc[0]["category"]) if not top_cat.empty else "—"
    biggest_tx = safe_float(expense_df["display_abs_amount"].max())
    savings_total = safe_float(savings_df["saved"].sum())
    savings_rate = (savings_total / (savings_total + total_spent) * 100) if (savings_total + total_spent) > 0 else 0.0
    with m1:
        st.metric(t("top_category"), top_cat_name)
    with m2:
        st.metric(t("largest_expense"), format_money(biggest_tx, display_currency))
    with m3:
        st.metric(t("savings_rate"), f"{savings_rate:.1f}%")
    with m4:
        hb = health_breakdown if isinstance(health_breakdown, dict) else {}
        st.metric(t("health_score"), f"{health_score}/100", help=f"{health_label} · {t('budget')} {hb.get('budget', '—')}, {t('saving')} {hb.get('saving', '—')}, {t('consistency')} {hb.get('consistency', '—')}")

    left, right = st.columns([1.4, 1])
    with left:
        section(l("Category overview", "Огляд категорій", "Kategorieübersicht"), l("Biggest spending buckets for the current filter set.", "Найбільші категорії витрат для поточного фільтра.", "Größte Ausgabenkategorien für den aktuellen Filter."))
        cat_df = category_summary(expense_df, "display_abs_amount")
        if cat_df.empty:
            show_empty(l("Add a few transactions to unlock the dashboard.", "Додай кілька транзакцій, щоб активувати дашборд.", "Füge ein paar Transaktionen hinzu, um das Dashboard zu aktivieren."))
        else:
            cat_df_view = cat_df.copy()
            cat_df_view["category"] = cat_df_view["category"].map(lcat)
            st.bar_chart(cat_df_view.set_index("category"))
            share_df = cat_df.copy()
            share_df["share"] = (share_df["display_abs_amount"] / share_df["display_abs_amount"].sum() * 100).round(1)
            st.dataframe(share_df, use_container_width=True, hide_index=True)
        end_section()
    with right:
        section(l("Category split", "Розподіл категорій", "Kategorieverteilung"), l("Pie view for the same filtered range.", "Кругова діаграма для того ж фільтра.", "Kreisdiagramm für denselben Filter."))
        pie_df = category_summary(expense_df, "display_abs_amount").copy()
        pie_df["category"] = pie_df["category"].map(lcat)
        plot_pie(pie_df, "display_abs_amount")
        end_section()

    left2, right2 = st.columns([1.1, 1])
    with left2:
        section(l("Budget pacing", "Темп витрат бюджету", "Budgetverlauf"), l("Compares this month’s spending with month progress.", "Порівнює витрати цього місяця з прогресом місяця.", "Vergleicht die Ausgaben dieses Monats mit dem Monatsfortschritt."))
        limit_input = st.number_input(
            f"{l("Monthly budget", "Місячний бюджет", "Monatsbudget")} ({display_currency})",
            min_value=0.0,
            value=safe_float(current_month_limit_display),
            step=10.0,
        )
        if st.button(l("Save monthly budget", "Зберегти місячний бюджет", "Monatsbudget speichern"), use_container_width=True):
            set_monthly_limit(user_id, convert_to_eur(limit_input, display_currency))
            st.success(l("Budget saved.", "Бюджет збережено.", "Budget gespeichert."))
            rerun()

        st.markdown("---")
        st.subheader(l("Category budgets", "Бюджети по категоріях", "Kategorie-Budgets"))
        category_budgets = get_category_budgets(user_id)
        selected_budget_categories = st.multiselect(
            l("Choose categories for monthly limits", "Оберіть категорії для місячних лімітів", "Kategorien für Monatslimits auswählen"),
            options=DEFAULT_CATEGORIES,
            default=[c for c in DEFAULT_CATEGORIES if c in category_budgets],
            key="selected_budget_categories",
            format_func=lcat,
        )
        category_budget_inputs = {}
        for cat in selected_budget_categories:
            current_limit_display = get_rates_map("EUR").get(display_currency, 1.0)
            current_limit_display = category_budgets.get(cat, 0.0) * current_limit_display
            category_budget_inputs[cat] = st.number_input(
                f"{l('Monthly limit for', 'Місячний ліміт для', 'Monatslimit für')} {lcat(cat)} ({display_currency})",
                min_value=0.0,
                value=float(current_limit_display),
                step=10.0,
                key=f"cat_budget_{cat}",
            )
        if st.button(l("Save category budgets", "Зберегти бюджети категорій", "Kategorie-Budgets speichern"), use_container_width=True):
            for cat in selected_budget_categories:
                amount_display = category_budget_inputs[cat]
                amount_eur = convert_to_eur(amount_display, display_currency)
                set_category_budget(user_id, cat, amount_eur)
            st.success(l("Category budgets saved.", "Бюджети категорій збережено.", "Kategorie-Budgets gespeichert."))
            rerun()
        budget_status = check_category_budgets(expense_df, get_category_budgets(user_id), display_currency)
        if budget_status:
            st.markdown(f"**{l('Category budget usage', 'Використання бюджетів категорій', 'Nutzung der Kategorie-Budgets')}**")
            for row in budget_status:
                st.write(
                    f"**{lcat(row['category'])}** — {row['spent']:.2f} / {row['limit']:.2f} {display_currency} ({row['pct']:.1f}%)"
                )
                st.progress(min(row["pct"] / 100, 1.0))
                if row["over"]:
                    st.warning(l("This category is over budget.", "Ця категорія перевищила бюджет.", "Diese Kategorie liegt über dem Budget."))
        if current_month_limit_display:
            elapsed_pct = date.today().day / pd.Timestamp.today().days_in_month
            spent_pct = this_month_spent / current_month_limit_display if current_month_limit_display > 0 else 0
            pace_delta = spent_pct - elapsed_pct
            st.progress(min(max(spent_pct, 0.0), 1.0))
            st.write(f"{l("Spent", "Витрачено", "Ausgegeben")}: **{format_money(this_month_spent, display_currency)}**")
            st.write(f"{l("Month progress", "Прогрес місяця", "Monatsfortschritt")}: **{elapsed_pct * 100:.1f}%**")
            st.write(f"{l("Budget used", "Використано бюджету", "Budget genutzt")}: **{spent_pct * 100:.1f}%**")
            if pace_delta > 0.08:
                st.warning(l("You are spending faster than the month is passing.", "Ти витрачаєш швидше, ніж минає місяць.", "Du gibst schneller aus, als der Monat vergeht."))
            elif pace_delta < -0.08:
                st.success(l("You are ahead of budget pace.", "Ти випереджаєш план бюджету.", "Du liegst besser als dein Budgetplan."))
            else:
                st.info(l("You are roughly on pace.", "Ти приблизно в межах плану.", "Du liegst ungefähr im Plan."))
            days_left = pd.Timestamp.today().days_in_month - date.today().day
            suggested_daily = budget_left / max(days_left, 1)
            st.caption(f"{l("Suggested daily cap for the rest of the month", "Рекомендований денний ліміт до кінця місяця", "Empfohlenes Tageslimit für den Rest des Monats")}: {format_money(suggested_daily, display_currency)}")
        else:
            show_empty(l("Set a monthly budget to unlock budget pacing.", "Задай місячний бюджет, щоб активувати темп бюджету.", "Lege ein Monatsbudget fest, um den Budgetverlauf zu sehen."))
        end_section()
    with right2:
        section(l("Live FX widget", "Віджет курсу валют", "Live-Wechselkurse"), l("Reference rates used for display conversion.", "Довідкові курси для конвертації відображення.", "Referenzkurse für die Anzeigekonvertierung."))
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
    with st.expander(l("Smart insights", "Розумні інсайти", "Smarte Insights"), expanded=True):
        for item in insight_box:
            st.write(f"- {item}")

    low, high = st.columns(2)
    with low:
        section(l("Recent expenses", "Останні витрати", "Letzte Ausgaben"), l("Last 12 items in the filtered range.", "Останні 12 записів у вибраному фільтрі.", "Letzte 12 Einträge im aktuellen Filter."))
        recent = filtered_df.sort_values("date", ascending=False).head(12)
        if recent.empty:
            show_empty(l("No expenses in the selected range.", "У вибраному діапазоні немає витрат.", "Keine Ausgaben im ausgewählten Bereich."))
        else:
            for _, row in recent.iterrows():
                badge = f'<span class="badge" style="background:{CATEGORY_COLORS.get(row["category"], CATEGORY_COLORS["Other"])}">{lcat(row["category"])}</span>'
                sub_badge = f'<span class="badge" style="background:#3b82f6">{l("Subscription", "Підписка", "Abo")}</span>' if int(row["subscription"]) == 1 else ""
                st.markdown(
                    f'<div class="feed-row"><div>{badge} {sub_badge}<br><span class="small-muted">{row["date_only"]} · {row["note"] or row["merchant"]}</span></div>'
                    f'<div><strong>{format_money(row["display_amount"], display_currency)}</strong></div></div>',
                    unsafe_allow_html=True,
                )
        end_section()
    with high:
        section(l("Savings goals", "Цілі заощаджень", "Sparziele"), l("Quick progress summary.", "Короткий підсумок прогресу.", "Kurze Fortschrittsübersicht."))
        if savings_df.empty:
            show_empty(l("No savings goals yet.", "Цілей заощаджень ще немає.", "Noch keine Sparziele vorhanden."))
        else:
            for _, row in savings_df.iterrows():
                progress = savings_progress(row["saved"], row["target"])
                st.write(f"**{row['name']}** — {format_money(row['saved'], 'EUR')} / {format_money(row['target'], 'EUR')}")
                st.progress(progress)
        end_section()


# =========================================================
# QUICK ADD
# =========================================================

elif page == t("quick_add"):
    section(l("Quick Add", "Швидке додавання", "Schnell hinzufügen"), l("Paste a short sentence, preview the parsed entry, then save it.", "Встав коротке речення, переглянь розбір і збережи.", "Füge einen kurzen Satz ein, prüfe die Erkennung und speichere dann."))
    quick_text = st.text_input(
        l("Quick entry", "Швидкий запис", "Schnelleingabe"),
        value=st.session_state.smart_note,
        placeholder="Examples: 2026-03-17 8.5 EUR coffee at Starbucks | 17.03 24.90 groceries | 12 usd uber",
    )
    preview = parse_quick_add(quick_text, history_df=expense_df)
    st.session_state.smart_note = quick_text
    if quick_text and preview["ok"]:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(l("Amount", "Сума", "Betrag"), format_money(preview["amount"], preview["currency"]))
        with c2:
            st.metric(l("Date", "Дата", "Datum"), str(preview["date"]))
        with c3:
            st.metric(l("Category", "Категорія", "Kategorie"), lcat(str(preview["category"])))
        with c4:
            st.metric("Type", ltx(preview["tx_type"]))
        confidence_labels = {
            "high": l("High confidence", "Висока впевненість", "Hohe Sicherheit"),
            "medium": l("Medium confidence", "Середня впевненість", "Mittlere Sicherheit"),
            "low": l("Low confidence", "Низька впевненість", "Niedrige Sicherheit"),
        }
        st.caption(
            f"{l('Category source', 'Джерело категорії', 'Kategoriequelle')}: {preview.get('category_reason', 'fallback')} · "
            f"{confidence_labels.get(str(preview.get('confidence', 'low')), str(preview.get('confidence', 'low')).title())}"
            + (f" · {l('Merchant guess', 'Ймовірний продавець', 'Vermuteter Händler')}: {preview.get('merchant_guess')}" if preview.get('merchant_guess') else "")
        )
        category_options = INCOME_CATEGORIES if preview["tx_type"] == "income" else DEFAULT_CATEGORIES
        default_index = category_options.index(preview["category"]) if preview["category"] in category_options else len(category_options)-1
        manual_category = st.selectbox(l("Adjust category", "Змінити категорію", "Kategorie anpassen"), category_options, index=default_index, format_func=lcat)
        note = st.text_input(l("Note / merchant", "Нотатка / продавець", "Notiz / Händler"), value=str(preview["note"]))
        subscription = st.checkbox(l("Recurring monthly subscription", "Щомісячна повторювана підписка", "Monatlich wiederkehrendes Abo"), value=bool(preview["subscription"]), disabled=preview["tx_type"] == "income")
        if st.button(l("Save quick entry", "Зберегти швидкий запис", "Schnelleingabe speichern"), type="primary", use_container_width=True):
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
            st.success(l("Quick entry saved.", "Швидкий запис збережено.", "Schnelleingabe gespeichert."))
            st.session_state.smart_note = ""
            rerun()
    elif quick_text:
        st.warning(preview["error"])
    end_section()

    section(l("Why this helps", "Чому це корисно", "Warum das hilft"), l("Useful for mobile, quick logging, and chat-style input.", "Зручно для телефону, швидкого внесення і вводу як у чаті.", "Nützlich für Handy, schnelle Erfassung und chatartigen Input."))
    st.write(l("The parser detects date, amount, currency, subscription hints, and suggests a category from the note.", "Парсер визначає дату, суму, валюту, ознаки підписки та пропонує категорію з нотатки.", "Der Parser erkennt Datum, Betrag, Währung, Abo-Hinweise und schlägt anhand der Notiz eine Kategorie vor."))
    end_section()


# =========================================================
# ADD EXPENSE
# =========================================================

elif page == t("add_expense"):
    section(l("Add transaction", "Додати транзакцію", "Transaktion hinzufügen"), l("Manual form for both expenses and income.", "Ручна форма для витрат і доходів.", "Manuelles Formular für Ausgaben und Einnahmen."))
    col1, col2 = st.columns(2)
    with col1:
        tx_type = st.selectbox(l("Transaction type", "Тип транзакції", "Transaktionstyp"), ["expense", "income"], format_func=lambda x: ltx(x))
        amount = st.number_input(l("Amount", "Сума", "Betrag"), min_value=0.01, step=0.5)
        currency = st.selectbox(l("Currency", "Валюта", "Währung"), SUPPORTED_CURRENCIES)
        note = st.text_input(l("Note / description", "Нотатка / опис", "Notiz / Beschreibung"))
        suggested_category = infer_category(note, fallback="Other Income" if tx_type == "income" else "Other") if note else ("Other Income" if tx_type == "income" else "Other")
    with col2:
        expense_date = st.date_input(l("Date", "Дата", "Datum"), value=date.today())
        category_options = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
        category = st.selectbox(l("Category", "Категорія", "Kategorie"), category_options, index=category_options.index(suggested_category) if suggested_category in category_options else len(category_options)-1, format_func=lcat)
        is_subscription = st.checkbox(l("Recurring monthly subscription", "Щомісячна повторювана підписка", "Monatlich wiederkehrendes Abo"), disabled=tx_type == "income")

    if note:
        st.caption(fl("Suggested category from note: {suggested_category}", "Запропонована категорія з нотатки: {suggested_category}", "Vorgeschlagene Kategorie aus der Notiz: {suggested_category}"))
    if st.button(l("Save transaction", "Зберегти транзакцію", "Transaktion speichern"), use_container_width=True):
        add_transaction(user_id, expense_date, amount, category, currency, tx_type, note, 1 if is_subscription else 0)
        st.success(l("Transaction added.", "Транзакцію додано.", "Transaktion hinzugefügt."))
        rerun()
    end_section()


# =========================================================
# MANAGE EXPENSES
# =========================================================

elif page == t("manage_expenses"):
    section(l("Manage expenses", "Керування транзакціями", "Transaktionen verwalten"), l("Search, edit, delete, and inspect duplicates.", "Пошук, редагування, видалення і перевірка дублікатів.", "Suchen, bearbeiten, löschen und Duplikate prüfen."))
    if filtered_df.empty:
        show_empty(l("No matching expenses.", "Немає відповідних витрат.", "Keine passenden Ausgaben."))
    else:
        managed = filtered_df.copy().sort_values("date", ascending=False)
        managed["label"] = (
            managed["date"].dt.strftime("%Y-%m-%d") + " | "
            + managed["category"].astype(str) + " | "
            + managed["original_amount"].round(2).astype(str) + " "
            + managed["currency"].astype(str) + " | "
            + managed["note"].fillna("")
        )
        selected_label = st.selectbox(l("Select transaction", "Обрати транзакцію", "Transaktion auswählen"), managed["label"].tolist())
        row = managed.loc[managed["label"] == selected_label].iloc[0]

        c1, c2 = st.columns(2)
        with c1:
            edit_date = st.date_input(l("Date", "Дата", "Datum"), value=row["date"].date(), key="edit_date")
            edit_original_amount = st.number_input("Original amount", min_value=0.0, value=float(row["original_amount"]), step=0.5)
            edit_currency = st.selectbox(l("Original currency", "Початкова валюта", "Originalwährung"), SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(row["currency"]))
        with c2:
            edit_type = st.selectbox(l("Transaction type", "Тип транзакції", "Transaktionstyp"), ["expense", "income"], index=0 if row["type"] == "expense" else 1, format_func=lambda x: x.title())
            category_options = DEFAULT_CATEGORIES if edit_type == "expense" else INCOME_CATEGORIES
            current_category = row["category"] if row["category"] in category_options else category_options[-1]
            edit_category = st.selectbox(l("Category", "Категорія", "Kategorie"), category_options, index=category_options.index(current_category), format_func=lcat)
            edit_note = st.text_input(l("Note / description", "Нотатка / опис", "Notiz / Beschreibung"), value=str(row["note"] or ""))
            edit_subscription = st.checkbox(l("Recurring monthly subscription", "Щомісячна повторювана підписка", "Monatlich wiederkehrendes Abo"), value=bool(row["subscription"]), disabled=edit_type == "income")

        b1, b2 = st.columns(2)
        if b1.button("Save changes", use_container_width=True):
            update_transaction(user_id, int(row["id"]), edit_date, edit_original_amount, edit_currency, edit_category, edit_note, edit_subscription, edit_type)
            st.success(l("Expense updated.", "Транзакцію оновлено.", "Transaktion aktualisiert."))
            rerun()
        if b2.button("Delete expense", use_container_width=True):
            delete_expense(user_id, int(row["id"]))
            st.success(l("Expense deleted.", "Транзакцію видалено.", "Transaktion gelöscht."))
            rerun()

        st.divider()
        st.write(f"**{l("Filtered table", "Відфільтрована таблиця", "Gefilterte Tabelle")}**")
        table = managed[["date_only", "type", "category", "merchant", "note", "original_amount", "currency", "display_amount", "subscription"]].copy()
        table["type"] = table["type"].map(ltx)
        table["category"] = table["category"].map(lcat)
        st.dataframe(table, use_container_width=True, hide_index=True)
    end_section()

    section(l("Duplicate finder", "Пошук дублікатів", "Duplikatfinder"), l("Flags items with the same date, amount, category, and note.", "Позначає записи з однаковими датою, сумою, категорією і нотаткою.", "Markiert Einträge mit gleichem Datum, Betrag, Kategorie und Notiz."))
    dups = detect_duplicates(filtered_df.assign(amount=filtered_df["amount"].abs()))
    if dups.empty:
        show_empty(l("No duplicates detected in the current filter range.", "У поточному фільтрі дублікатів не виявлено.", "Im aktuellen Filterbereich wurden keine Duplikate erkannt."))
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

elif page == t("subscriptions"):
    section(l("Recurring subscriptions", "Повторювані підписки", "Wiederkehrende Abos"), l("Grouped view, annual cost estimate, and concentration risk.", "Групування, оцінка річної вартості та ризик концентрації.", "Gruppierte Ansicht, jährliche Kostenschätzung und Konzentrationsrisiko."))
    subs = filtered_df[filtered_df["subscription"] == 1].copy()
    if subs.empty:
        show_empty(l("No subscriptions in the selected range.", "У вибраному діапазоні немає підписок.", "Keine Abos im ausgewählten Bereich."))
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
            st.metric(l("Estimated monthly total", "Орієнтовна сума за місяць", "Geschätzte Monatssumme"), format_money(total_monthly, display_currency))
        with c2:
            st.metric(l("Estimated annual total", "Орієнтовна сума за рік", "Geschätzte Jahressumme"), format_money(annualized, display_currency))
        with c3:
            top_share = grouped.iloc[0]["monthly_display"] / total_monthly * 100 if total_monthly else 0
            st.metric(l("Largest subscription share", "Найбільша частка підписки", "Größter Abo-Anteil"), f"{top_share:.1f}%")
        grouped["last_seen"] = pd.to_datetime(grouped["last_seen"]).dt.date
        st.dataframe(grouped, use_container_width=True, hide_index=True)
        st.bar_chart(grouped.set_index("merchant")[["monthly_display"]])
    end_section()


# =========================================================
# SAVINGS
# =========================================================

elif page == t("savings"):
    section(l("Savings goals", "Цілі заощаджень", "Sparziele"), l("Create goals, add progress, and keep track of totals.", "Створюй цілі, додавай прогрес і відстежуй підсумки.", "Erstelle Ziele, füge Fortschritt hinzu und behalte Summen im Blick."))
    c1, c2, c3 = st.columns(3)
    with c1:
        goal_name = st.text_input(l("Goal name", "Назва цілі", "Zielname"))
    with c2:
        goal_target = st.number_input(l("Target (€)", "Ціль (€)", "Ziel (€)"), min_value=0.0, step=10.0)
    with c3:
        goal_saved = st.number_input(l("Already saved (€)", "Вже відкладено (€)", "Bereits gespart (€)"), min_value=0.0, step=10.0)

    if st.button(l("Add goal", "Додати ціль", "Ziel hinzufügen"), use_container_width=True):
        if not goal_name.strip():
            st.error(l("Goal name cannot be empty.", "Назва цілі не може бути порожньою.", "Der Zielname darf nicht leer sein."))
        else:
            supabase.table("savings").insert({
                "user_id": user_id,
                "name": goal_name.strip(),
                "target": float(goal_target),
                "saved": float(goal_saved),
            }).execute()
            st.success(l("Savings goal added.", "Ціль заощаджень додано.", "Sparziel hinzugefügt."))
            rerun()

    if savings_df.empty:
        show_empty(l("No savings goals yet.", "Цілей заощаджень ще немає.", "Noch keine Sparziele vorhanden."))
    else:
        total_target = safe_float(savings_df["target"].sum())
        total_saved = safe_float(savings_df["saved"].sum())
        st.caption(f"{l("Combined progress", "Загальний прогрес", "Gesamtfortschritt")}: {format_money(total_saved, 'EUR')} / {format_money(total_target, 'EUR')}")
        for _, row in savings_df.iterrows():
            st.write(f"### {row['name']}")
            progress = savings_progress(row["saved"], row["target"])
            st.progress(progress)
            st.caption(f"{l("Saved", "Відкладено", "Gespart")}: {format_money(row['saved'], 'EUR')} / {l("Target", "Ціль", "Ziel")}: {format_money(row['target'], 'EUR')}")
            add_more = st.number_input(f"{l("Add money to", "Додати гроші до", "Geld hinzufügen zu")} {row['name']}", min_value=0.0, step=10.0, key=f"save_{row['id']}")
            x1, x2 = st.columns(2)
            if x1.button(f"{l("Update", "Оновити", "Aktualisieren")} {row['name']}", key=f"upd_{row['id']}", use_container_width=True):
                supabase.table("savings").update({"saved": float(row["saved"]) + float(add_more)}).eq("id", int(row["id"])).eq("user_id", user_id).execute()
                st.success(l("Savings updated.", "Заощадження оновлено.", "Sparziel aktualisiert."))
                rerun()
            if x2.button(f"{l("Delete", "Видалити", "Löschen")} {row['name']}", key=f"del_{row['id']}", use_container_width=True):
                supabase.table("savings").delete().eq("id", int(row["id"])).eq("user_id", user_id).execute()
                st.success(l("Goal deleted.", "Ціль видалено.", "Ziel gelöscht."))
                rerun()
            st.divider()
    end_section()


# =========================================================
# ANALYTICS
# =========================================================

elif page == t("analytics"):
    section(l("Advanced analytics", "Розширена аналітика", "Erweiterte Analysen"), l("Monthly trend, merchants, weekday patterns, anomalies, and Pareto view.", "Місячний тренд, продавці, патерни по днях, аномалії та Pareto-аналіз.", "Monatstrend, Händler, Wochentagsmuster, Anomalien und Pareto-Ansicht."))
    analytics_df = expense_df.copy()
    if analytics_df.empty:
        show_empty(l("No data for analytics in the current range.", "Немає даних для аналітики в цьому діапазоні.", "Keine Daten für Analysen im aktuellen Bereich."))
        end_section()
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**{l("Monthly trend", "Місячний тренд", "Monatstrend")}**")
            monthly = monthly_series(analytics_df, "display_abs_amount")
            if monthly.empty:
                show_empty(l("Not enough monthly data.", "Недостатньо місячних даних.", "Nicht genug Monatsdaten."))
            else:
                st.line_chart(monthly.set_index("month"))
        with c2:
            st.write(f"**{l("Weekday pattern", "Патерн по днях тижня", "Wochentagsmuster")}**")
            weekdays = weekday_summary(analytics_df, "display_abs_amount")
            st.bar_chart(weekdays.set_index("weekday"))
        end_section()

        left, right = st.columns(2)
        with left:
            section(l("Top merchants", "Топ продавців", "Top-Händler"), l("Based on the first meaningful words in the note.", "На основі перших змістовних слів у нотатці.", "Basierend auf den ersten sinnvollen Wörtern in der Notiz."))
            merchants = merchant_summary(analytics_df, "display_abs_amount")
            if merchants.empty:
                show_empty(l("No merchant-like notes found.", "Схожих на продавця нотаток не знайдено.", "Keine händlerähnlichen Notizen gefunden."))
            else:
                merchants_view = merchants.head(15).copy()
                merchants_view["category"] = merchants_view["category"].map(lcat) if "category" in merchants_view.columns else merchants_view.get("category")
                st.dataframe(merchants_view, use_container_width=True, hide_index=True)
            end_section()
        with right:
            section(l("Anomaly detector", "Пошук аномалій", "Anomalie-Erkennung"), l("Flags unusually high transactions within each category.", "Позначає незвично великі транзакції в межах кожної категорії.", "Markiert ungewöhnlich hohe Transaktionen innerhalb jeder Kategorie."))
            anomalies = detect_anomalies(analytics_df.assign(display_amount=analytics_df["display_abs_amount"]))
            if anomalies.empty:
                show_empty(l("No strong anomalies detected.", "Сильних аномалій не виявлено.", "Keine starken Anomalien erkannt."))
            else:
                anomalies_view = anomalies[["date_only", "category", "note", "display_amount", "currency"]].sort_values("display_amount", ascending=False).copy()
                anomalies_view["category"] = anomalies_view["category"].map(lcat)
                st.dataframe(
                    anomalies_view,
                    use_container_width=True,
                    hide_index=True,
                )
            end_section()

        section(l("Pareto view", "Pareto-аналіз", "Pareto-Ansicht"), l("Shows how much your top categories explain total spending.", "Показує, яку частку загальних витрат пояснюють топ-категорії.", "Zeigt, wie stark die Top-Kategorien die Gesamtausgaben erklären."))
        cat = category_summary(analytics_df, "display_abs_amount")
        if cat.empty:
            show_empty(l("No data.", "Немає даних.", "Keine Daten."))
        else:
            pareto = cat.copy()
            pareto["category"] = pareto["category"].map(lcat)
            pareto["cum_pct"] = (pareto["display_abs_amount"].cumsum() / pareto["display_abs_amount"].sum() * 100).round(1)
            st.dataframe(pareto, use_container_width=True, hide_index=True)
            hits_80 = pareto[pareto["cum_pct"] <= 80.0]
            st.caption(f"{len(hits_80) if not hits_80.empty else 1} " + l("category(ies) explain roughly 80% of the selected spending.", "категорій пояснюють приблизно 80% вибраних витрат.", "Kategorie(n) erklären ungefähr 80% der ausgewählten Ausgaben."))
        end_section()

        section(l("Spending calendar", "Календар витрат", "Ausgabenkalender"), l("Daily total view for the selected period.", "Щоденний підсумок за вибраний період.", "Tagesgesamtansicht für den ausgewählten Zeitraum."))
        cal = analytics_df.groupby("date_only", as_index=False)["display_abs_amount"].sum().sort_values("date_only")
        cal = cal.rename(columns={"display_abs_amount": "display_amount"})
        cal["weekday"] = pd.to_datetime(cal["date_only"]).dt.day_name()
        st.dataframe(cal, use_container_width=True, hide_index=True)
        end_section()


# =========================================================
# IMPORT / EXPORT
# =========================================================

elif page == t("import_export"):
    section(l("Export data", "Експорт даних", "Datenexport"), l("Filtered or full downloads for backup and analysis.", "Завантаження відфільтрованих або повних даних для резерву та аналізу.", "Gefilterte oder vollständige Downloads für Backup und Analyse."))
    export_df = filtered_df.copy()
    full_df = base_display_df.copy()

    if export_df.empty and full_df.empty:
        show_empty(l("Nothing to export yet.", "Поки нічого експортувати.", "Noch nichts zu exportieren."))
    else:
        def to_excel_bytes(df: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Expenses")
            return output.getvalue()

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(l("Download filtered CSV", "Завантажити відфільтрований CSV", "Gefiltertes CSV herunterladen"), export_df.to_csv(index=False).encode("utf-8"), "expenses_filtered.csv", "text/csv", use_container_width=True)
            st.download_button(l("Download filtered Excel", "Завантажити відфільтрований Excel", "Gefiltertes Excel herunterladen"), to_excel_bytes(export_df), "expenses_filtered.xlsx", use_container_width=True)
        with c2:
            st.download_button(l("Download full CSV", "Завантажити повний CSV", "Vollständiges CSV herunterladen"), full_df.to_csv(index=False).encode("utf-8"), "expenses_full.csv", "text/csv", use_container_width=True)
            st.download_button(l("Download full Excel", "Завантажити повний Excel", "Vollständiges Excel herunterladen"), to_excel_bytes(full_df), "expenses_full.xlsx", use_container_width=True)
    end_section()

    section(l("CSV template", "CSV-шаблон", "CSV-Vorlage"), l("Use this format for bulk import. You can include type=income or expense.", "Використовуй цей формат для масового імпорту. Можна вказати type=income або expense.", "Nutze dieses Format für den Massenimport. Du kannst type=income oder expense angeben."))
    st.download_button(l("Download CSV template", "Завантажити CSV-шаблон", "CSV-Vorlage herunterladen"), csv_template(), "expense_import_template.csv", "text/csv", use_container_width=True)
    end_section()

    section(l("Bulk import", "Масовий імпорт", "Massenimport"), l("Expected columns: date, amount, currency, category, note, subscription, type.", "Очікувані колонки: date, amount, currency, category, note, subscription, type.", "Erwartete Spalten: date, amount, currency, category, note, subscription, type."))
    uploaded = st.file_uploader(l("Upload CSV", "Завантажити CSV", "CSV hochladen"), type=["csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_csv(uploaded)
            st.write(f"**{l("Preview", "Попередній перегляд", "Vorschau")}**")
            st.dataframe(incoming.head(10), use_container_width=True, hide_index=True)
            required = {"date", "amount"}
            if not required.issubset(set(incoming.columns.str.lower())):
                st.error(l("CSV must contain at least: date, amount", "CSV має містити щонайменше: date, amount", "CSV muss mindestens enthalten: date, amount"))
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
                    except Exception as e:
                        st.warning(f"Skipped: {e}")
                        continue
                st.caption(f"{l("Valid rows ready to import", "Валідних рядків готово до імпорту", "Gültige Zeilen bereit für den Import")}: {len(valid_rows)}")
                if valid_rows and st.button(l("Import rows", "Імпортувати рядки", "Zeilen importieren"), use_container_width=True, type="primary"):
                    for d, amt, cur, cat, note, sub, tx_type in valid_rows:
                        add_transaction(user_id, d, amt, cat, cur, tx_type, note, sub)
                    st.success(f"{l("Imported", "Імпортовано", "Importiert")} {len(valid_rows)} {l("row(s).", "рядків.", "Zeile(n).")}")
                    rerun()
        except Exception as exc:
            st.error(f"{l("Failed to read CSV", "Не вдалося прочитати CSV", "CSV konnte nicht gelesen werden")}: {exc}")
    end_section()
