
import io
import sqlite3
from datetime import date
from calendar import monthrange
from contextlib import contextmanager

import bcrypt
import pandas as pd
import requests
import streamlit as st

DB_PATH = "expense_tracker_multi.db"
DEFAULT_CATEGORIES = [
    "Food", "Transport", "Rent", "Entertainment", "Shopping", "Health",
    "Sports", "Bills", "Cafe", "Education", "Travel", "Other"
]
SUPPORTED_CURRENCIES = ["EUR", "USD", "UAH"]

st.set_page_config(page_title="Expense Tracker Pro", page_icon="💸", layout="wide")


# =========================
# DB LAYER
# =========================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def safe_add_column(conn: sqlite3.Connection, table: str, column: str, definition: str, backfill_current_timestamp: bool = False):
    if not table_has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        if backfill_current_timestamp:
            conn.execute(f"UPDATE {table} SET {column} = CURRENT_TIMESTAMP WHERE {column} IS NULL")


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                currency TEXT DEFAULT 'EUR',
                subscription INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS savings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target REAL NOT NULL,
                saved REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
                user_id INTEGER PRIMARY KEY,
                monthly_limit REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        safe_add_column(conn, "users", "created_at", "TEXT", backfill_current_timestamp=True)
        safe_add_column(conn, "expenses", "currency", "TEXT DEFAULT 'EUR'")
        safe_add_column(conn, "expenses", "subscription", "INTEGER DEFAULT 0")
        safe_add_column(conn, "expenses", "note", "TEXT DEFAULT ''")
        safe_add_column(conn, "expenses", "created_at", "TEXT", backfill_current_timestamp=True)
        safe_add_column(conn, "savings", "created_at", "TEXT", backfill_current_timestamp=True)


init_db()


# =========================
# AUTH
# =========================
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def check_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def get_user(username: str):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()


def register_user(username: str, password: str):
    username = username.strip()
    if len(username) < 3:
        return False, "Username must have at least 3 characters."
    if len(password) < 6:
        return False, "Password must have at least 6 characters."

    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "This username already exists."
    except sqlite3.OperationalError as e:
        return False, f"Database error: {e}"


def require_login() -> int:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return int(user_id)


# =========================
# FX HELPERS
# =========================
@st.cache_data(ttl=3600)
def get_rates_map(base: str = "EUR") -> dict:
    if base == "EUR":
        fallback = {"EUR": 1.0, "USD": 1.08, "UAH": 42.0}
    elif base == "USD":
        fallback = {"USD": 1.0, "EUR": 0.93, "UAH": 39.0}
    else:
        fallback = {base: 1.0, "EUR": 1.0, "USD": 1.0, "UAH": 1.0}

    try:
        resp = requests.get(
            f"https://api.exchangerate.host/latest?base={base}&symbols=EUR,USD,UAH",
            timeout=10,
        )
        data = resp.json()
        rates = data.get("rates", {})
        if not isinstance(rates, dict) or not rates:
            return fallback
        rates[base] = 1.0
        return {k: float(v) for k, v in rates.items()}
    except Exception:
        return fallback


def convert_to_eur(amount: float, currency: str) -> float:
    if currency == "EUR":
        return round(float(amount), 2)
    rates = get_rates_map(currency)
    eur_rate = rates.get("EUR", 1.0)
    return round(float(amount) * float(eur_rate), 2)


def convert_from_eur(amount_eur: float, out_currency: str) -> float:
    if out_currency == "EUR":
        return round(float(amount_eur), 2)
    rates = get_rates_map("EUR")
    out_rate = rates.get(out_currency, 1.0)
    return round(float(amount_eur) * float(out_rate), 2)


def format_money(value: float, currency: str = "EUR") -> str:
    return f"{value:,.2f} {currency}".replace(",", " ")


# =========================
# DATA HELPERS
# =========================
def load_expenses(user_id: int) -> pd.DataFrame:
    with db() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC",
            conn,
            params=(user_id,),
        )
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["subscription"] = pd.to_numeric(df["subscription"], errors="coerce").fillna(0).astype(int)
    df["note"] = df["note"].fillna("")
    df["currency"] = df["currency"].fillna("EUR")
    return df


def load_savings(user_id: int) -> pd.DataFrame:
    with db() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM savings WHERE user_id = ? ORDER BY id DESC",
            conn,
            params=(user_id,),
        )
    if df.empty:
        return df
    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved"] = pd.to_numeric(df["saved"], errors="coerce").fillna(0.0)
    return df


def make_display_df(df: pd.DataFrame, output_currency: str) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["display_amount"] = out["amount"].apply(lambda x: convert_from_eur(x, output_currency))
    out["date_only"] = out["date"].dt.date
    out["month"] = out["date"].dt.to_period("M").astype(str)
    return out


def add_expense(user_id: int, expense_date: date, amount: float, category: str, currency: str, note: str = "", subscription: int = 0):
    amount_eur = convert_to_eur(amount, currency)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO expenses (user_id, date, amount, category, currency, subscription, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, expense_date.isoformat(), amount_eur, category, currency, int(subscription), note.strip()),
        )


def get_monthly_limit(user_id: int):
    with db() as conn:
        row = conn.execute("SELECT monthly_limit FROM budgets WHERE user_id = ?", (user_id,)).fetchone()
    return float(row["monthly_limit"]) if row else None


def set_monthly_limit(user_id: int, amount_eur: float):
    with db() as conn:
        conn.execute(
            """
            INSERT INTO budgets (user_id, monthly_limit)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (user_id, float(amount_eur)),
        )


def upsert_monthly_subscriptions(user_id: int) -> int:
    df = load_expenses(user_id)
    if df.empty:
        return 0

    today = date.today()
    month_start = date(today.year, today.month, 1).isoformat()
    current_month_key = today.strftime("%Y-%m")

    subs = df[df["subscription"] == 1].copy()
    if subs.empty:
        return 0

    created = 0
    with db() as conn:
        for _, row in subs.iterrows():
            row_month_key = pd.to_datetime(row["date"]).strftime("%Y-%m")
            if row_month_key == current_month_key:
                continue

            exists = conn.execute(
                """
                SELECT 1
                FROM expenses
                WHERE user_id = ?
                  AND subscription = 1
                  AND category = ?
                  AND note = ?
                  AND amount = ?
                  AND substr(date, 1, 7) = ?
                LIMIT 1
                """,
                (
                    user_id,
                    str(row["category"]),
                    str(row["note"]),
                    float(row["amount"]),
                    current_month_key,
                ),
            ).fetchone()

            if not exists:
                conn.execute(
                    """
                    INSERT INTO expenses (user_id, date, amount, category, currency, subscription, note)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        user_id,
                        month_start,
                        float(row["amount"]),
                        str(row["category"]),
                        str(row["currency"] or "EUR"),
                        str(row["note"]),
                    ),
                )
                created += 1

    return created


# =========================
# SESSION
# =========================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None


# =========================
# SIDEBAR / AUTH
# =========================
st.sidebar.title("👤 Account")

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
            if ok:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)

if not st.session_state.user_id:
    st.title("💸 Expense Tracker Pro")
    st.caption("Log in or register in the sidebar.")
    st.stop()


# =========================
# NAVIGATION
# =========================
user_id = require_login()
created_subs = upsert_monthly_subscriptions(user_id)
if created_subs:
    st.toast(f"Added {created_subs} recurring subscription(s) for this month.")

st.sidebar.divider()
display_currency = st.sidebar.selectbox("Display currency", SUPPORTED_CURRENCIES, index=0)
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Expense", "Manage Expenses", "Subscriptions", "Savings", "Analytics", "Export"],
)

st.title("💸 Expense Tracker Pro")
st.caption("Multi-user tracker with subscriptions, savings, analytics, and export.")

df = load_expenses(user_id)
display_df = make_display_df(df, display_currency)
savings_df = load_savings(user_id)


# =========================
# DASHBOARD
# =========================
if page == "Dashboard":
    today = pd.Timestamp.today()
    if display_df.empty:
        this_month_df = pd.DataFrame()
    else:
        this_month_df = display_df[
            (display_df["date"].dt.year == today.year) &
            (display_df["date"].dt.month == today.month)
        ].copy()

    total_spent = float(display_df["display_amount"].sum()) if not display_df.empty else 0.0
    month_spent = float(this_month_df["display_amount"].sum()) if not this_month_df.empty else 0.0
    avg_spent = float(display_df["display_amount"].mean()) if not display_df.empty else 0.0
    tx_count = int(len(display_df))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total spent", format_money(total_spent, display_currency))
    c2.metric("This month", format_money(month_spent, display_currency))
    c3.metric("Average expense", format_money(avg_spent, display_currency))
    c4.metric("Transactions", tx_count)

    st.divider()
    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("Expenses by category")
        if display_df.empty:
            st.info("No expenses yet.")
        else:
            cat_df = (
                display_df.groupby("category", as_index=False)["display_amount"]
                .sum()
                .sort_values("display_amount", ascending=False)
            )
            cat_df = cat_df.set_index("category")
            st.bar_chart(cat_df)

    with right:
        st.subheader("Budget")
        current_limit_eur = get_monthly_limit(user_id)
        current_limit_display = convert_from_eur(current_limit_eur, display_currency) if current_limit_eur is not None else 0.0
        new_limit_display = st.number_input(
            f"Monthly limit ({display_currency})",
            min_value=0.0,
            value=float(current_limit_display),
            step=10.0,
        )
        if st.button("Save monthly limit", use_container_width=True):
            new_limit_eur = convert_to_eur(new_limit_display, display_currency)
            set_monthly_limit(user_id, new_limit_eur)
            st.success("Monthly limit saved.")
            rerun()

        if current_limit_eur is not None:
            limit_display = convert_from_eur(current_limit_eur, display_currency)
            progress = min(month_spent / limit_display, 1.0) if limit_display > 0 else 0.0
            st.progress(progress)
            if month_spent > limit_display:
                st.warning(f"You are over budget by {format_money(month_spent - limit_display, display_currency)}.")
            else:
                st.success(f"Left this month: {format_money(limit_display - month_spent, display_currency)}")
        else:
            st.info("No monthly limit set.")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Top categories this month")
        if this_month_df.empty:
            st.info("No expenses this month.")
        else:
            top = (
                this_month_df.groupby("category", as_index=False)["display_amount"]
                .sum()
                .sort_values("display_amount", ascending=False)
                .head(5)
            )
            top = top.rename(columns={"display_amount": f"Amount ({display_currency})"})
            st.dataframe(top, use_container_width=True, hide_index=True)

    with c2:
        st.subheader("Savings progress")
        if savings_df.empty:
            st.info("No savings goals yet.")
        else:
            for _, row in savings_df.iterrows():
                progress = (row["saved"] / row["target"]) if row["target"] > 0 else 0.0
                st.write(f"**{row['name']}** — {format_money(row['saved'], 'EUR')} / {format_money(row['target'], 'EUR')}")
                st.progress(float(min(max(progress, 0.0), 1.0)))

    st.divider()
    st.subheader("Recent expenses")
    if display_df.empty:
        st.info("No expenses to show.")
    else:
        recent = display_df[["date_only", "category", "display_amount", "currency", "subscription", "note"]].head(15).copy()
        recent["subscription"] = recent["subscription"].map({1: "Yes", 0: "No"})
        recent = recent.rename(columns={
            "date_only": "Date",
            "category": "Category",
            "display_amount": f"Amount ({display_currency})",
            "currency": "Original currency",
            "subscription": "Subscription",
            "note": "Note",
        })
        st.dataframe(recent, use_container_width=True, hide_index=True)

elif page == "Add Expense":
    st.subheader("Add a new expense")

    c1, c2 = st.columns(2)
    with c1:
        amount = st.number_input("Amount", min_value=0.01, step=0.5)
        currency = st.selectbox("Currency", SUPPORTED_CURRENCIES)
        category = st.selectbox("Category", DEFAULT_CATEGORIES)
    with c2:
        expense_date = st.date_input("Date", value=date.today())
        note = st.text_input("Note / description")
        is_subscription = st.checkbox("Recurring monthly subscription")

    if st.button("Add expense", use_container_width=True):
        add_expense(
            user_id=user_id,
            expense_date=expense_date,
            amount=amount,
            category=category,
            currency=currency,
            note=note,
            subscription=1 if is_subscription else 0,
        )
        st.success("Expense added.")
        rerun()

elif page == "Manage Expenses":
    st.subheader("Manage expenses")

    if df.empty:
        st.info("No expenses yet.")
    else:
        filter_category = st.selectbox("Filter by category", ["All"] + sorted(df["category"].dropna().unique().tolist()))
        show_subs_only = st.checkbox("Only subscriptions")

        filtered = df.copy()
        if filter_category != "All":
            filtered = filtered[filtered["category"] == filter_category]
        if show_subs_only:
            filtered = filtered[filtered["subscription"] == 1]

        if filtered.empty:
            st.info("No matching expenses.")
        else:
            filtered = filtered.copy()
            filtered["label"] = (
                filtered["date"].dt.strftime("%Y-%m-%d")
                + " | " + filtered["category"].astype(str)
                + " | " + filtered["amount"].round(2).astype(str) + " EUR"
                + " | " + filtered["note"].fillna("")
            )
            selected_label = st.selectbox("Select expense", filtered["label"].tolist())
            expense = filtered.loc[filtered["label"] == selected_label].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                edit_amount_eur = st.number_input("Amount in EUR", min_value=0.0, value=float(expense["amount"]), step=0.5)
                current_category = expense["category"] if expense["category"] in DEFAULT_CATEGORIES else "Other"
                edit_category = st.selectbox("Category", DEFAULT_CATEGORIES, index=DEFAULT_CATEGORIES.index(current_category))
                edit_subscription = st.checkbox("Recurring subscription", value=bool(expense["subscription"]))
            with c2:
                edit_date = st.date_input("Date", value=pd.to_datetime(expense["date"]).date())
                edit_note = st.text_input("Note", value=str(expense["note"] or ""))
                current_currency = expense["currency"] if expense["currency"] in SUPPORTED_CURRENCIES else "EUR"
                edit_currency = st.selectbox("Original currency label", SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(current_currency))

            b1, b2 = st.columns(2)
            if b1.button("Save changes", use_container_width=True):
                with db() as conn:
                    conn.execute(
                        """
                        UPDATE expenses
                        SET amount = ?, category = ?, date = ?, note = ?, currency = ?, subscription = ?
                        WHERE id = ? AND user_id = ?
                        """,
                        (
                            float(edit_amount_eur),
                            edit_category,
                            edit_date.isoformat(),
                            edit_note.strip(),
                            edit_currency,
                            1 if edit_subscription else 0,
                            int(expense["id"]),
                            user_id,
                        ),
                    )
                st.success("Expense updated.")
                rerun()

            if b2.button("Delete expense", use_container_width=True):
                with db() as conn:
                    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (int(expense["id"]), user_id))
                st.success("Expense deleted.")
                rerun()

elif page == "Subscriptions":
    st.subheader("Recurring subscriptions")
    st.caption("Subscriptions are stored in the expenses table and auto-added once per month.")

    subs = df[df["subscription"] == 1].copy() if not df.empty else pd.DataFrame()

    if subs.empty:
        st.info("No subscriptions yet. Add one from 'Add Expense' and tick the recurring option.")
    else:
        subs["date"] = subs["date"].dt.date
        show = subs[["date", "category", "amount", "currency", "note"]].rename(columns={
            "date": "Start date",
            "category": "Category",
            "amount": "Amount (EUR)",
            "currency": "Original currency",
            "note": "Name / note",
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

elif page == "Savings":
    st.subheader("Savings goals")

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
            with db() as conn:
                conn.execute(
                    "INSERT INTO savings (user_id, name, target, saved) VALUES (?, ?, ?, ?)",
                    (user_id, goal_name.strip(), float(goal_target), float(goal_saved)),
                )
            st.success("Savings goal added.")
            rerun()

    st.divider()
    if savings_df.empty:
        st.info("No savings goals yet.")
    else:
        for _, row in savings_df.iterrows():
            st.write(f"### {row['name']}")
            progress = row["saved"] / row["target"] if row["target"] > 0 else 0.0
            st.progress(float(min(max(progress, 0.0), 1.0)))
            st.write(f"Saved: {format_money(row['saved'], 'EUR')} / Target: {format_money(row['target'], 'EUR')}")

            add_more = st.number_input(
                f"Add money to {row['name']}",
                min_value=0.0,
                step=10.0,
                key=f"add_goal_{row['id']}",
            )
            x1, x2 = st.columns(2)
            if x1.button(f"Update {row['name']}", key=f"update_goal_{row['id']}", use_container_width=True):
                with db() as conn:
                    conn.execute(
                        "UPDATE savings SET saved = saved + ? WHERE id = ? AND user_id = ?",
                        (float(add_more), int(row["id"]), user_id),
                    )
                st.success("Savings updated.")
                rerun()

            if x2.button(f"Delete {row['name']}", key=f"delete_goal_{row['id']}", use_container_width=True):
                with db() as conn:
                    conn.execute("DELETE FROM savings WHERE id = ? AND user_id = ?", (int(row["id"]), user_id))
                st.success("Goal deleted.")
                rerun()

            st.divider()

elif page == "Analytics":
    st.subheader("Analytics")

    if display_df.empty:
        st.info("No data to analyze yet.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Monthly trend**")
            monthly = display_df.groupby("month", as_index=False)["display_amount"].sum()
            monthly = monthly.set_index("month")
            st.line_chart(monthly)

        with c2:
            st.markdown("**Daily spending this month**")
            now = pd.Timestamp.today()
            this_month = display_df[
                (display_df["date"].dt.year == now.year) &
                (display_df["date"].dt.month == now.month)
            ].copy()

            if this_month.empty:
                st.info("No expenses this month.")
            else:
                this_month["day"] = this_month["date"].dt.day
                daily = this_month.groupby("day", as_index=False)["display_amount"].sum().set_index("day")
                st.bar_chart(daily)

        st.divider()
        st.markdown("**Month-over-month category comparison**")

        now = pd.Timestamp.today()
        this_month_key = now.strftime("%Y-%m")
        prev_month_date = (now.replace(day=1) - pd.Timedelta(days=1))
        prev_month_key = prev_month_date.strftime("%Y-%m")

        grouped = display_df.groupby(["month", "category"], as_index=False)["display_amount"].sum()

        this_df = grouped[grouped["month"] == this_month_key][["category", "display_amount"]].rename(
            columns={"display_amount": "this_month"}
        )
        prev_df = grouped[grouped["month"] == prev_month_key][["category", "display_amount"]].rename(
            columns={"display_amount": "last_month"}
        )

        comparison = pd.merge(this_df, prev_df, on="category", how="outer").fillna(0.0)
        comparison["diff"] = comparison["this_month"] - comparison["last_month"]
        comparison["pct_change"] = comparison.apply(
            lambda row: ((row["diff"] / row["last_month"]) * 100.0)
            if row["last_month"] > 0 else (100.0 if row["this_month"] > 0 else 0.0),
            axis=1
        )
        st.dataframe(comparison.sort_values("diff", ascending=False), use_container_width=True, hide_index=True)

        days_passed = max(now.day, 1)
        days_total = monthrange(now.year, now.month)[1]
        this_month_total = float(this_df["this_month"].sum()) if not this_df.empty else 0.0
        forecast = (this_month_total / days_passed) * days_total if days_passed > 0 else 0.0
        st.metric("Forecast for this month", format_money(forecast, display_currency))

elif page == "Export":
    st.subheader("Export your data")

    if df.empty and savings_df.empty:
        st.info("Nothing to export yet.")
    else:
        export_expenses = df.copy()
        if not export_expenses.empty:
            export_expenses["date"] = export_expenses["date"].dt.strftime("%Y-%m-%d")

        st.download_button(
            "Download expenses CSV",
            data=export_expenses.to_csv(index=False).encode("utf-8"),
            file_name="expenses.csv",
            mime="text/csv",
            use_container_width=True,
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            export_expenses.to_excel(writer, index=False, sheet_name="Expenses")
            savings_df.to_excel(writer, index=False, sheet_name="Savings")
        excel_buffer.seek(0)

        st.download_button(
            "Download Excel workbook",
            data=excel_buffer.getvalue(),
            file_name="finance_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
