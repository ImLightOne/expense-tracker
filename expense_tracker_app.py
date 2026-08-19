"""Entry point: session bootstrap, global filters, and page routing.

The actual page bodies live in views/*.py (see Wave 2 of the product plan).
Shared helpers, translations, and the auth flow live in common.py. This file
is deliberately thin: everything it computes here (user_id, display_currency,
the filtered dataframes) is the small set of state every page needs, passed
down through a single `ctx` dict.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import streamlit as st

st.set_page_config(page_title="Expense Tracker Pro+", page_icon="💸", layout="wide")

# Default lookback window for the main interactive load. Bounding this query
# (instead of always pulling a user's entire transaction history on every
# rerun — Streamlit reruns the whole script on every widget interaction)
# keeps the app responsive as history grows. Users can opt into the full,
# unbounded history via the "Load full history" sidebar toggle; exports
# always fetch the complete history regardless of this default.
DEFAULT_HISTORY_DAYS = 730

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
os.environ.setdefault("SUPABASE_URL", SUPABASE_URL)
os.environ.setdefault("SUPABASE_KEY", SUPABASE_KEY)

from config import CATEGORY_COLORS, SUPPORTED_CURRENCIES
from db import get_category_colors, get_category_options, load_expenses, load_savings, upsert_recurring_transactions
from analytics import apply_filters, enrich_expenses
from common import (
    consume_email_link,
    get_date_range_presets,
    inject_style,
    l,
    login_user,
    logout_user,
    metric_card,
    register_user,
    render_set_password_screen,
    request_password_reset,
    require_login,
    rerun,
    restore_session,
    t,
)
from views import (
    add_expense,
    analytics_page,
    categories_page,
    dashboard,
    help_page,
    import_export,
    manage_expenses,
    quick_add,
    savings,
    subscriptions,
)


# Re-injects the <style> block on every run (see inject_style()'s docstring
# in common.py for why this can't just live at common.py's module level).
inject_style()

# =========================================================
# SIDEBAR / SESSION
# =========================================================

for key, default in {
    "user_id": None,
    "username": None,
    "access_token": None,
    "refresh_token": None,
    "must_set_password": False,
    "smart_note": "",
    "smart_preview": None,
    "lang": "en",
}.items():
    st.session_state.setdefault(key, default)

restore_session()
consume_email_link()

email_link_error = st.session_state.pop("email_link_error", None)
if email_link_error:
    st.error(email_link_error)

if st.session_state.get("user_id") and st.session_state.get("must_set_password"):
    render_set_password_screen()

st.sidebar.markdown(t("sidebar_title"))
st.sidebar.caption(t("sidebar_caption"))
st.session_state.lang = st.sidebar.selectbox(t("language"), ["en", "uk", "de"], index=["en", "uk", "de"].index(st.session_state.get("lang", "en")), format_func=lambda x: {"en": "English", "uk": "Українська", "de": "Deutsch"}[x])

if st.session_state.user_id:
    st.sidebar.success(t("logged_in_as", username=st.session_state.username))
    if st.sidebar.button(t("log_out"), use_container_width=True):
        logout_user()
        rerun()
else:
    mode = st.sidebar.radio(t("mode"), [t("login"), t("register"), t("forgot_password")])
    if mode == t("forgot_password"):
        reset_email = st.sidebar.text_input(t("email"))
        if st.sidebar.button(t("send_reset_link"), use_container_width=True):
            ok, message = request_password_reset(reset_email)
            (st.sidebar.success if ok else st.sidebar.error)(message)
    elif mode == t("login"):
        login_email = st.sidebar.text_input(t("email"))
        login_password = st.sidebar.text_input(t("password"), type="password")
        if st.sidebar.button(t("login"), use_container_width=True):
            ok, message = login_user(login_email, login_password)
            if ok:
                rerun()
            else:
                st.sidebar.error(message)
    else:
        reg_username = st.sidebar.text_input(t("username"))
        reg_email = st.sidebar.text_input(t("email"))
        reg_password = st.sidebar.text_input(t("password"), type="password")
        if st.sidebar.button(t("create_account"), use_container_width=True):
            ok, message = register_user(reg_username, reg_email, reg_password)
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
# Generating this period's recurring-transaction occurrences involves an
# unbounded history load plus one Supabase existence-check per stale
# subscription — real work worth doing once, not on every rerun (Streamlit
# reruns this whole script on every widget interaction). A subscription's
# occurrence only needs to be (re)checked once per calendar day, so gate it
# on a date-keyed session flag rather than a plain "ran once" bool — that
# keeps a session open across midnight self-healing instead of getting
# stuck on yesterday's check forever.
recurring_sync_key = f"_recurring_synced_{date.today().isoformat()}"
if not st.session_state.get(recurring_sync_key):
    created_subs = upsert_recurring_transactions(user_id)
    st.session_state[recurring_sync_key] = True
    if created_subs:
        st.toast(f"{created_subs} {l('recurring transaction(s) added.', 'повторюваних транзакцій додано.', 'wiederkehrende Transaktion(en) hinzugefügt.')}")

expense_categories = get_category_options(user_id, "expense")
income_categories = get_category_options(user_id, "income")
# User overrides win over the built-in defaults; anything not overridden
# just falls through to config.CATEGORY_COLORS via the merge.
category_colors = {**CATEGORY_COLORS, **get_category_colors(user_id)}

st.sidebar.divider()
display_currency = st.sidebar.selectbox(t("display_currency"), SUPPORTED_CURRENCIES, index=0)
st.sidebar.caption(t("fx_caption"))

show_full_history = st.sidebar.checkbox(
    t("show_full_history"),
    value=False,
    help=t("show_full_history_help", days=DEFAULT_HISTORY_DAYS),
)
history_start = None if show_full_history else date.today() - timedelta(days=DEFAULT_HISTORY_DAYS)

base_df = load_expenses(user_id, start_date=history_start)
base_display_df = enrich_expenses(base_df, display_currency)
savings_df = load_savings(user_id)

min_date = base_display_df["date"].min().date() if not base_display_df.empty else date.today().replace(day=1)
max_date = base_display_df["date"].max().date() if not base_display_df.empty else date.today()
default_start = max(min_date, date.today().replace(day=1))
default_end = max_date

with st.sidebar:
    st.markdown(f"### {t('global_filters')}")
    presets = get_date_range_presets(min_date, max_date)
    preset_name = st.selectbox(t("quick_range"), list(presets.keys()), index=0)
    preset_start, preset_end = presets[preset_name]
    start_date = st.date_input(t("from"), value=preset_start, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    end_date = st.date_input(t("to"), value=preset_end, min_value=min_date, max_value=max_date if max_date >= min_date else None)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    all_categories = list(dict.fromkeys(expense_categories + income_categories))
    category_filter = st.multiselect(t("categories"), options=all_categories)
    search_query = st.text_input(t("search_text"), placeholder=t("search_placeholder"))
    subs_only_global = st.checkbox(t("subscriptions_only"))

filtered_df = apply_filters(base_display_df, start_date, end_date, category_filter, search_query, subs_only_global)
expense_df = filtered_df[filtered_df["type"] == "expense"].copy()
income_df = filtered_df[filtered_df["type"] == "income"].copy()

ctx = {
    "user_id": user_id,
    "display_currency": display_currency,
    "base_display_df": base_display_df,
    "filtered_df": filtered_df,
    "expense_df": expense_df,
    "income_df": income_df,
    "savings_df": savings_df,
    "start_date": start_date,
    "end_date": end_date,
    "history_is_complete": show_full_history,
    "expense_categories": expense_categories,
    "income_categories": income_categories,
    "category_colors": category_colors,
}

st.title(t("app_title"))
st.caption(f"{start_date.isoformat()} → {end_date.isoformat()} · {len(filtered_df)} {t('filtered_transactions')}")

# Page objects are created here (rather than inline in a list literal) and
# stashed on ctx["pages"] so individual views can build real st.page_link
# cross-links to each other (e.g. an empty state on the dashboard linking
# straight to Quick Add) instead of only relying on the sidebar nav. The
# lambdas below still close over `ctx` by reference, so adding the "pages"
# key to it afterwards is picked up fine when a page actually renders.
page_dashboard = st.Page(lambda v=dashboard: v.render(ctx), title=t("dashboard"), icon="📊", url_path="dashboard", default=True)
page_quick_add = st.Page(lambda v=quick_add: v.render(ctx), title=t("quick_add"), icon="⚡", url_path="quick-add")
page_add_expense = st.Page(lambda v=add_expense: v.render(ctx), title=t("add_expense"), icon="➕", url_path="add-expense")
page_manage_expenses = st.Page(lambda v=manage_expenses: v.render(ctx), title=t("manage_expenses"), icon="🗂️", url_path="manage-expenses")
page_subscriptions = st.Page(lambda v=subscriptions: v.render(ctx), title=t("subscriptions"), icon="🔁", url_path="subscriptions")
page_savings = st.Page(lambda v=savings: v.render(ctx), title=t("savings"), icon="💰", url_path="savings")
page_analytics = st.Page(lambda v=analytics_page: v.render(ctx), title=t("analytics"), icon="📈", url_path="analytics")
page_import_export = st.Page(lambda v=import_export: v.render(ctx), title=t("import_export"), icon="📤", url_path="import-export")
page_categories = st.Page(lambda v=categories_page: v.render(ctx), title=t("categories_page"), icon="🏷️", url_path="categories")
page_help = st.Page(lambda v=help_page: v.render(ctx), title=t("help_page"), icon="❓", url_path="help")

ctx["pages"] = {
    "dashboard": page_dashboard,
    "quick_add": page_quick_add,
    "add_expense": page_add_expense,
    "manage_expenses": page_manage_expenses,
    "subscriptions": page_subscriptions,
    "savings": page_savings,
    "analytics": page_analytics,
    "import_export": page_import_export,
    "categories": page_categories,
    "help": page_help,
}

pages = [
    page_dashboard,
    page_quick_add,
    page_add_expense,
    page_manage_expenses,
    page_subscriptions,
    page_savings,
    page_analytics,
    page_import_export,
    page_categories,
    page_help,
]
navigation = st.navigation(pages, position="sidebar")
st.sidebar.markdown(f"### {t('navigation')}")
navigation.run()
