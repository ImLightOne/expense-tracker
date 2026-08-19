"""Shared helpers, auth flow, and translations used by the entry point and
every page in views/. Keeping this in one module (instead of duplicating
across pages, or relying on Streamlit script-global state) is the whole
point of the Wave 2 page split: each page imports what it needs from here
instead of re-declaring it.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from analytics import category_summary
from config import CATEGORY_COLORS, CATEGORY_TRANSLATIONS, STYLE
from db import (
    get_profile_username,
    get_rates_map as db_get_rates_map,
    request_password_reset as db_request_password_reset,
    restore_auth_session,
    sign_in,
    sign_out,
    sign_up,
    update_password,
    username_exists,
    verify_otp,
)
from utils import format_money, safe_float

def inject_style() -> None:
    """Injects the app's <style> block. Must be called explicitly from the
    main script body on every run — NOT left as module-level code here.

    Streamlit reruns expense_tracker_app.py (the main script) top to bottom
    on every interaction, but a `from common import ...` on those reruns
    hits Python's sys.modules cache: common.py's top-level statements only
    execute once, the first time the module is ever imported in this
    process. A bare `st.markdown(STYLE, ...)` at module level here used to
    rely on that one-time execution — so the stylesheet was only ever
    present on a session's very first script run, and vanished from the
    DOM on every rerun after (which is effectively always, since logging
    in alone triggers one). Calling this from the main script instead
    means it re-runs — and re-injects the <style> tag — every single time,
    same as everything else the main script does on every rerun.
    """
    st.markdown(STYLE, unsafe_allow_html=True)


# =========================================================
# UI UTILITIES
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


# Fixed status colors (never themed — same hex regardless of light/dark mode).
# Used only as a chip's own background+ink pair, never as page text color, so
# contrast never depends on Streamlit's current theme: the chip carries its own
# background, so it always clears contrast against its own ink.
_TONE_CHIP_STYLE = {
    "good": ("#0ca30c", "#ffffff"),
    "warning": ("#fab219", "#1a1a19"),
    "serious": ("#ec835a", "#1a1a19"),
    "critical": ("#d03b3b", "#ffffff"),
}


def metric_card(label: str, value: str, foot: str = "", tone: Optional[str] = None, chip: Optional[str] = None) -> None:
    """Render a stat tile.

    `tone` (None / "good" / "warning" / "serious" / "critical") colors the card's
    top accent bar and, when `chip` is also given, renders `chip` as a small solid
    pill badge. The headline `value` always stays in the page's normal text color —
    status is carried by the label text, the chip text, and the accent bar together,
    never by tinting the number itself (that would fail contrast on a light theme
    for the warning/serious hues, and color-alone isn't an accessible signal anyway).
    """
    tone_class = f" tone-{tone}" if tone in _TONE_CHIP_STYLE else ""
    chip_html = ""
    if chip and tone in _TONE_CHIP_STYLE:
        bg, ink = _TONE_CHIP_STYLE[tone]
        chip_html = f'<span class="tone-chip" style="background:{bg};color:{ink};">{chip}</span>'
    foot_html = f'<div class="metric-foot">{foot}</div>' if foot else ""
    st.markdown(
        f'<div class="metric-card{tone_class}"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'{chip_html}{foot_html}</div>',
        unsafe_allow_html=True,
    )


def show_empty(text: str) -> None:
    st.markdown(f'<div class="soft-box">{text}</div>', unsafe_allow_html=True)


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
# AUTH / SESSION
# =========================================================

def require_login() -> str:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return str(user_id)


def restore_session() -> None:
    """Re-attach a previously established Supabase Auth session on this rerun.

    Streamlit re-executes the whole script on every interaction, so the
    module-level `supabase` client starts anonymous each time. If we already
    signed in during an earlier run, replay the saved tokens so RLS-protected
    queries keep carrying the user's identity instead of silently returning
    zero rows.
    """
    if st.session_state.get("user_id"):
        return
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")
    if not access_token or not refresh_token:
        return
    try:
        res = restore_auth_session(access_token, refresh_token)
    except Exception:
        res = None
    if res and res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = get_profile_username(res.user.id) or res.user.email
    else:
        for key in ("access_token", "refresh_token", "user_id", "username"):
            st.session_state.pop(key, None)


def login_user(email: str, password: str) -> tuple[bool, str]:
    email = email.strip()
    if not email or not password:
        return False, t("invalid_credentials")
    try:
        res = sign_in(email, password)
    except Exception:
        return False, t("invalid_credentials")
    if not res.session or not res.user:
        return False, t("invalid_credentials")
    st.session_state.access_token = res.session.access_token
    st.session_state.refresh_token = res.session.refresh_token
    st.session_state.user_id = res.user.id
    st.session_state.username = get_profile_username(res.user.id) or res.user.email
    return True, ""


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    email = email.strip()
    if len(username) < 3:
        return False, l("Username must have at least 3 characters.", "Ім'я користувача має містити щонайменше 3 символи.", "Der Benutzername muss mindestens 3 Zeichen lang sein.")
    if not email or "@" not in email:
        return False, l("Enter a valid email address.", "Введи коректну email-адресу.", "Gib eine gültige E-Mail-Adresse ein.")
    if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        return False, l("Password must be at least 8 characters and include a letter and a number.", "Пароль має містити щонайменше 8 символів, літеру та цифру.", "Das Passwort muss mindestens 8 Zeichen sowie einen Buchstaben und eine Zahl enthalten.")
    if username_exists(username):
        return False, l("This username already exists.", "Такий користувач уже існує.", "Dieser Benutzername existiert bereits.")
    try:
        res = sign_up(email, password, username)
    except Exception as exc:
        message = str(exc).lower()
        if "already registered" in message or "already exists" in message or "user_repeated_signup" in message:
            return False, l("This email is already registered.", "Ця email-адреса вже зареєстрована.", "Diese E-Mail-Adresse ist bereits registriert.")
        return False, l("Could not create account. Please try again.", "Не вдалося створити акаунт. Спробуй ще раз.", "Konto konnte nicht erstellt werden. Bitte versuche es erneut.")
    if res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = username
        return True, l("Account created successfully.", "Акаунт успішно створено.", "Konto erfolgreich erstellt.")
    return True, l(
        "Account created. Check your email to confirm it before logging in.",
        "Акаунт створено. Перевір пошту й підтверди його перед входом.",
        "Konto erstellt. Bitte bestätige es per E-Mail, bevor du dich anmeldest.",
    )


def request_password_reset(email: str) -> tuple[bool, str]:
    email = email.strip()
    if not email or "@" not in email:
        return False, l("Enter a valid email address.", "Введи коректну email-адресу.", "Gib eine gültige E-Mail-Adresse ein.")
    try:
        db_request_password_reset(email)
    except Exception:
        pass
    # Deliberately generic regardless of outcome, so this can't be used to
    # probe which email addresses have an account.
    return True, l(
        "If that email is registered, a reset link is on its way.",
        "Якщо ця пошта зареєстрована, лист із посиланням уже надіслано.",
        "Falls diese E-Mail registriert ist, ist ein Reset-Link unterwegs.",
    )


def logout_user() -> None:
    try:
        sign_out()
    except Exception:
        pass
    for key in ("access_token", "refresh_token", "user_id", "username", "must_set_password"):
        st.session_state.pop(key, None)


def consume_email_link() -> None:
    """Handle an invite/recovery/signup-confirmation link the user just clicked.

    Supabase's default email templates redirect with the session tokens after a
    `#`, which never reaches Streamlit's Python side. Our email templates are
    configured (in the Supabase dashboard) to link to `{{ .SiteURL }}?token_hash=
    {{ .TokenHash }}&type=...` instead, which Streamlit *can* read via
    `st.query_params`. We exchange that token_hash for a real session here.
    """
    token_hash = st.query_params.get("token_hash")
    otp_type = st.query_params.get("type")
    if not token_hash or not otp_type or st.session_state.get("user_id"):
        return
    try:
        res = verify_otp(token_hash, otp_type)
    except Exception:
        res = None
    st.query_params.clear()
    if res and res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = get_profile_username(res.user.id) or res.user.email
        # Invite/recovery links prove the email is theirs but don't carry a
        # password — make them set one before they can use the app.
        st.session_state.must_set_password = otp_type in ("invite", "recovery")
    else:
        st.session_state["email_link_error"] = l(
            "This link is invalid or has expired. Please request a new one.",
            "Це посилання недійсне або застаріло. Запроси нове.",
            "Dieser Link ist ungültig oder abgelaufen. Bitte fordere einen neuen an.",
        )


def render_set_password_screen() -> None:
    st.title(l("Set your password", "Встанови пароль", "Passwort festlegen"))
    st.caption(l(
        "Choose a password to finish setting up your account.",
        "Обери пароль, щоб завершити налаштування акаунта.",
        "Wähle ein Passwort, um dein Konto einzurichten.",
    ))
    new_password = st.text_input(t("password"), type="password", key="set_pw_new")
    confirm_password = st.text_input(
        l("Confirm password", "Підтвердь пароль", "Passwort bestätigen"), type="password", key="set_pw_confirm"
    )
    if st.button(l("Save password", "Зберегти пароль", "Passwort speichern"), use_container_width=True):
        if len(new_password) < 8 or not (any(c.isalpha() for c in new_password) and any(c.isdigit() for c in new_password)):
            st.error(l(
                "Password must be at least 8 characters and include a letter and a number.",
                "Пароль має містити щонайменше 8 символів, літеру та цифру.",
                "Das Passwort muss mindestens 8 Zeichen sowie einen Buchstaben und eine Zahl enthalten.",
            ))
        elif new_password != confirm_password:
            st.error(l("Passwords don't match.", "Паролі не збігаються.", "Passwörter stimmen nicht überein."))
        else:
            try:
                update_password(new_password)
            except Exception:
                st.error(l("Could not save the password. Please try again.", "Не вдалося зберегти пароль. Спробуй ще раз.", "Passwort konnte nicht gespeichert werden. Bitte versuche es erneut."))
            else:
                st.session_state.must_set_password = False
                st.success(l("Password set. You're all set.", "Пароль встановлено.", "Passwort festgelegt."))
                rerun()
    if st.button(l("Cancel and log out", "Скасувати й вийти", "Abbrechen und abmelden")):
        logout_user()
        rerun()
    st.stop()


# =========================================================
# FX RATES (cached)
# =========================================================

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


# =========================================================
# TRANSLATIONS
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
        "forgot_password": "Forgot password",
        "username": "Username",
        "email": "Email",
        "password": "Password",
        "create_account": "Create account",
        "send_reset_link": "Send reset link",
        "invalid_credentials": "Invalid email or password.",
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
        "show_full_history": "Load full history",
        "show_full_history_help": "By default only the last {days} days load, to keep the app fast. Turn this on to include older transactions (search, edit, and charts will include everything, but rendering may be slower).",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "add_expense": "Add Expense",
        "manage_expenses": "Manage Expenses",
        "subscriptions": "Subscriptions",
        "savings": "Savings",
        "analytics": "Analytics",
        "import_export": "Import / Export",
        "categories_page": "Categories",
        "help_page": "Help & Privacy",
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
        "forgot_password": "Забув пароль",
        "username": "Ім'я користувача",
        "email": "Email",
        "password": "Пароль",
        "create_account": "Створити акаунт",
        "send_reset_link": "Надіслати посилання",
        "invalid_credentials": "Неправильний email або пароль.",
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
        "show_full_history": "Завантажити всю історію",
        "show_full_history_help": "За замовчуванням завантажуються лише останні {days} днів, щоб застосунок працював швидко. Увімкни, щоб включити старіші транзакції (пошук, редагування й графіки враховуватимуть усе, але може працювати повільніше).",
        "navigation": "Навігація",
        "dashboard": "Дашборд",
        "add_expense": "Додати витрату",
        "manage_expenses": "Керування витратами",
        "subscriptions": "Підписки",
        "savings": "Заощадження",
        "analytics": "Аналітика",
        "import_export": "Імпорт / Експорт",
        "categories_page": "Категорії",
        "help_page": "Довідка й приватність",
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
        "forgot_password": "Passwort vergessen",
        "username": "Benutzername",
        "email": "E-Mail",
        "password": "Passwort",
        "create_account": "Konto erstellen",
        "send_reset_link": "Link senden",
        "invalid_credentials": "Ungültige E-Mail-Adresse oder ungültiges Passwort.",
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
        "show_full_history": "Vollständige Historie laden",
        "show_full_history_help": "Standardmäßig werden nur die letzten {days} Tage geladen, damit die App schnell bleibt. Aktiviere dies, um ältere Transaktionen einzubeziehen (Suche, Bearbeitung und Diagramme berücksichtigen dann alles, das Laden kann aber langsamer sein).",
        "navigation": "Navigation",
        "dashboard": "Dashboard",
        "add_expense": "Ausgabe hinzufügen",
        "manage_expenses": "Ausgaben verwalten",
        "subscriptions": "Abos",
        "savings": "Sparen",
        "analytics": "Analysen",
        "import_export": "Import / Export",
        "categories_page": "Kategorien",
        "help_page": "Hilfe & Datenschutz",
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


def lrec(recurrence: str) -> str:
    mapping = {
        "weekly": l("Weekly", "Щотижня", "Wöchentlich"),
        "monthly": l("Monthly", "Щомісяця", "Monatlich"),
        "yearly": l("Yearly", "Щорічно", "Jährlich"),
    }
    return mapping.get(str(recurrence).lower(), str(recurrence).title())
