
import io
from datetime import date
from calendar import monthrange
from supabase import create_client, Client

import bcrypt
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

from pathlib import Path
import shutil
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def init_db():
    # Supabase uses pre-created tables, so nothing to initialize here.
    return
DEFAULT_CATEGORIES = ["Food","Transport","Rent","Entertainment","Shopping","Health","Sports","Bills","Cafe","Education","Travel","Other"]
SUPPORTED_CURRENCIES = ["EUR","USD","UAH"]
CATEGORY_COLORS = {
    "Food":"#f97316","Transport":"#3b82f6","Rent":"#8b5cf6","Entertainment":"#ec4899",
    "Shopping":"#14b8a6","Health":"#ef4444","Sports":"#22c55e","Bills":"#f59e0b",
    "Cafe":"#d97706","Education":"#6366f1","Travel":"#06b6d4","Other":"#64748b",
}

st.set_page_config(page_title="Expense Tracker Pro", page_icon="💸", layout="wide")

st.markdown("""
<style>
/* ---------- LOGIN / REGISTER INPUT FIX ---------- */

section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background: #ffffff !important;
}

section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder {
    color: #666666 !important;
    -webkit-text-fill-color: #666666 !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="input"] > div {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
}

section[data-testid="stSidebar"] div[data-baseweb="input"] > div * {
    color: #111111 !important;
}

/* ---------- STREAMLIT THEME VARIABLES ----------
   var(--background-color)
   var(--secondary-background-color)
   var(--text-color)
   var(--primary-color)
------------------------------------------------- */

.block-container{
    padding-top:1rem;
    padding-bottom:2rem;
    max-width:1300px;
}

/* ---------- SIDEBAR ---------- */

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#111827 0%,#0f172a 100%) !important;
}

[data-testid="stSidebar"],
[data-testid="stSidebar"] *{
    color:#ffffff !important;
}

/* ---------- MAIN TYPOGRAPHY ---------- */

.main-title{
    font-size:clamp(1.6rem,2vw,2.15rem);
    font-weight:800;
    margin-bottom:.2rem;
    line-height:1.15;
    color:var(--text-color) !important;
}

.main-subtitle{
    color:var(--text-color) !important;
    opacity:.8;
    margin-bottom:1rem;
    line-height:1.45;
}

/* ---------- PAGE SHELL ---------- */

.page-shell{
    background:var(--background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:24px;
    padding:1rem 1rem .4rem 1rem;
    box-shadow:0 10px 30px rgba(15,23,42,.08);
    color:var(--text-color) !important;
}

/* ---------- SECTION CARDS ---------- */

.section-card{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:18px;
    padding:1rem 1rem .9rem 1rem;
    margin-bottom:1rem;
    box-shadow:0 8px 24px rgba(15,23,42,.08);
    color:var(--text-color) !important;
}

.section-card *{
    color:var(--text-color);
}

.section-title{
    font-size:1.12rem;
    font-weight:700;
    margin-bottom:.1rem;
    color:var(--text-color) !important;
}

.section-subtitle{
    font-size:.93rem;
    margin-bottom:.9rem;
    color:var(--text-color) !important;
    opacity:.75;
}

/* ---------- KPI CARDS (INTENTIONALLY DARK) ---------- */

.metric-card{
    background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%) !important;
    border-radius:18px;
    padding:1rem;
    min-height:126px;
    box-shadow:0 10px 28px rgba(15,23,42,.18);
    color:#ffffff !important;
}

.metric-card *{
    color:#ffffff !important;
}

.metric-label{
    font-size:.95rem;
    margin-bottom:.35rem;
    color:rgba(255,255,255,.78) !important;
}

.metric-value{
    font-size:1.75rem;
    font-weight:800;
    line-height:1.08;
    color:#ffffff !important;
}

.metric-foot{
    margin-top:.45rem;
    font-size:.9rem;
    color:rgba(255,255,255,.78) !important;
}

/* ---------- NATIVE ST.METRIC ---------- */

div[data-testid="stMetric"]{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:12px 14px;
    box-shadow:0 8px 22px rgba(15,23,42,.05);
}

div[data-testid="stMetric"],
div[data-testid="stMetric"] *{
    color:var(--text-color) !important;
}

/* ---------- SAVINGS ---------- */

.goal-card{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:.9rem;
    margin-bottom:.8rem;
    color:var(--text-color) !important;
}

.goal-card *{
    color:var(--text-color);
}

.goal-wrap{
    margin-bottom:.9rem;
}

.goal-head{
    display:flex;
    justify-content:space-between;
    gap:12px;
    align-items:center;
    margin-bottom:.35rem;
    flex-wrap:wrap;
}

.goal-name{
    font-weight:700;
    color:var(--text-color) !important;
}

.goal-nums{
    color:var(--text-color) !important;
    opacity:.8;
}

.goal-bar{
    width:100%;
    height:12px;
    background:rgba(148,163,184,.25) !important;
    border-radius:999px;
    overflow:hidden;
}

.goal-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#22c55e 0%,#06b6d4 100%) !important;
}

/* ---------- BADGES ---------- */

.badge{
    display:inline-block;
    padding:.25rem .6rem;
    border-radius:999px;
    font-size:.78rem;
    font-weight:700;
}

.badge-good{background:#22c55e !important;color:#ffffff !important;}
.badge-warn{background:#f59e0b !important;color:#ffffff !important;}
.badge-info{background:#3b82f6 !important;color:#ffffff !important;}
.badge-neutral{background:#64748b !important;color:#ffffff !important;}

/* ---------- CATEGORY BADGES ---------- */

.cat-badge{
    display:inline-block;
    padding:.24rem .62rem;
    border-radius:999px;
    font-size:.76rem;
    font-weight:700;
    color:#ffffff !important;
}

/* ---------- EXPENSE FEED ---------- */

.expense-row{
    display:flex;
    justify-content:space-between;
    gap:12px;
    align-items:center;
    padding:.72rem .78rem;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:14px;
    margin-bottom:.55rem;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
}

.expense-left,.expense-right{
    display:flex;
    align-items:center;
    gap:8px;
    flex-wrap:wrap;
}

.expense-row,
.expense-row *{
    color:var(--text-color);
}

.expense-note{
    font-size:.87rem;
    color:var(--text-color) !important;
    opacity:.75;
}

.expense-row .badge,
.expense-row .cat-badge{
    color:#ffffff !important;
}

/* ---------- FX WIDGET ---------- */

.fx-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:.55rem .7rem;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:12px;
    margin-bottom:.5rem;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
}

.fx-row,
.fx-row *{
    color:var(--text-color) !important;
}

/* ---------- EMPTY STATES ---------- */

.empty-box{
    background:var(--secondary-background-color) !important;
    border:1px dashed rgba(128,128,128,.28) !important;
    border-radius:16px;
    padding:1rem;
    color:var(--text-color) !important;
}

.empty-box *{
    color:var(--text-color) !important;
}

/* ---------- FORECAST ---------- */

.forecast-box{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:.95rem 1rem;
    margin-top:1rem;
    color:var(--text-color) !important;
}

.forecast-box *{
    color:var(--text-color) !important;
}

.forecast-label{
    font-size:.92rem;
    color:var(--text-color) !important;
    opacity:.8;
}

.forecast-value{
    font-size:1.7rem;
    font-weight:800;
    color:var(--text-color) !important;
}

.kpi-inline{
    color:var(--text-color) !important;
    opacity:.8;
}

/* ---------- TABLES / DATAFRAMES ---------- */

[data-testid="stDataFrame"]{
    background:var(--secondary-background-color) !important;
    border-radius:14px;
}

[data-testid="stDataFrame"] *{
    color:var(--text-color) !important;
}

/* ---------- INPUTS ---------- */

div.stButton > button{
    border-radius:12px;
    border:0;
    min-height:2.8rem;
    font-weight:700;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stDateInput > div > div{
    border-radius:12px;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
}

input, textarea{
    color:var(--text-color) !important;
    -webkit-text-fill-color:var(--text-color) !important;
}

/* ---------- ALERTS ---------- */

div[data-testid="stAlertContent"],
div[data-testid="stAlertContent"] *{
    color:var(--text-color) !important;
}

</style>
""", unsafe_allow_html=True)
def get_conn():
    conn=sqlite3.connect(DB_PATH,timeout=30,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

@contextmanager
def db():
    conn=get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def rerun():
    try: st.rerun()
    except Exception: st.experimental_rerun()

def table_has_column(conn, table, column):
    rows=conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"]==column for r in rows)

def safe_add_column(conn, table, column, definition, backfill_current_timestamp=False):
    if not table_has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        if backfill_current_timestamp:
            conn.execute(f"UPDATE {table} SET {column} = CURRENT_TIMESTAMP WHERE {column} IS NULL")

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash BLOB NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,date TEXT NOT NULL,amount REAL NOT NULL,category TEXT NOT NULL,currency TEXT DEFAULT 'EUR',subscription INTEGER DEFAULT 0,note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS savings(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,target REAL NOT NULL,saved REAL NOT NULL DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS budgets(user_id INTEGER PRIMARY KEY,monthly_limit REAL NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id))""")
        safe_add_column(conn,"users","created_at","TEXT",True)
        safe_add_column(conn,"expenses","currency","TEXT DEFAULT 'EUR'")
        safe_add_column(conn,"expenses","subscription","INTEGER DEFAULT 0")
        safe_add_column(conn,"expenses","note","TEXT DEFAULT ''")
        safe_add_column(conn,"expenses","created_at","TEXT",True)
        safe_add_column(conn,"savings","created_at","TEXT",True)
init_db()

def hash_password(password): return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
def check_password(password, password_hash): return bcrypt.checkpw(password.encode("utf-8"), password_hash)
def get_user(username: str):
    res = (
        supabase.table("users")
        .select("*")
        .eq("username", username.strip())
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None
def register_user(username: str, password: str):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must have at least 3 characters."
    if len(password) < 6:
        return False, "Password must have at least 6 characters."

    existing = (
        supabase.table("users")
        .select("id")
        .eq("username", username)
        .limit(1)
        .execute()
    )

    if existing.data:
        return False, "This username already exists."

    supabase.table("users").insert({
        "username": username,
        "password_hash": hash_password(password).decode("utf-8")
    }).execute()

    return True, "Account created successfully."
def require_login():
    user_id=st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return int(user_id)
def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
@st.cache_data(ttl=1800)
def get_rates_map(base="EUR"):
    base=base.upper()
    if base=="EUR": fallback={"EUR":1.0,"USD":1.08,"UAH":50.0}
    elif base=="USD": fallback={"USD":1.0,"EUR":0.93,"UAH":43.0}
    elif base=="UAH": fallback={"UAH":1.0,"EUR":0.02,"USD":0.023}
    else: fallback={base:1.0,"EUR":1.0,"USD":1.0,"UAH":1.0}
    result={base:1.0}
    try:
        resp=requests.get(f"https://api.frankfurter.app/latest?from={base}&to=EUR,USD",timeout=10)
        rates=resp.json().get("rates",{})
        if isinstance(rates,dict):
            if base=="EUR": result.update({"USD":float(rates.get("USD",fallback["USD"])),"EUR":1.0})
            elif base=="USD": result.update({"EUR":float(rates.get("EUR",fallback["EUR"])),"USD":1.0})
            else: result.update({"EUR":float(rates.get("EUR",fallback["EUR"])),"USD":float(rates.get("USD",fallback["USD"]))})
    except Exception:
        result.update({k:v for k,v in fallback.items() if k in ["EUR","USD"]})
    try:
        data=requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json",timeout=10).json()
        eur_uah=usd_uah=None
        for row in data:
            if row.get("cc")=="EUR": eur_uah=float(row["rate"])
            if row.get("cc")=="USD": usd_uah=float(row["rate"])
        if eur_uah and usd_uah:
            if base=="EUR": result["UAH"]=eur_uah
            elif base=="USD": result["UAH"]=usd_uah
            elif base=="UAH": result.update({"EUR":1/eur_uah,"USD":1/usd_uah,"UAH":1.0})
    except Exception:
        result["UAH"]=fallback["UAH"]
    for k,v in fallback.items(): result.setdefault(k,v)
    return result

def convert_to_eur(amount,currency):
    if currency=="EUR": return round(float(amount),2)
    return round(float(amount)*float(get_rates_map(currency).get("EUR",1.0)),2)

def convert_from_eur(amount_eur,out_currency):
    if out_currency=="EUR": return round(float(amount_eur),2)
    return round(float(amount_eur)*float(get_rates_map("EUR").get(out_currency,1.0)),2)

def format_money(value,currency="EUR"): return f"{value:,.2f} {currency}".replace(",", " ")

def load_expenses(user_id: int) -> pd.DataFrame:
    res = (
        supabase.table("expenses")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .execute()
    )

    df = pd.DataFrame(res.data)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["subscription"] = pd.to_numeric(df["subscription"], errors="coerce").fillna(0).astype(int)
    df["note"] = df["note"].fillna("")
    df["currency"] = df["currency"].fillna("EUR")
    return df.sort_values(["date", "id"], ascending=[False, False])
def load_savings(user_id: int) -> pd.DataFrame:
    res = (
        supabase.table("savings")
        .select("*")
        .eq("user_id", user_id)
        .order("id", desc=True)
        .execute()
    )

    df = pd.DataFrame(res.data)

    if df.empty:
        return df

    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved"] = pd.to_numeric(df["saved"], errors="coerce").fillna(0.0)
    return df
def make_display_df(df, output_currency):
    if df.empty: return df
    out=df.copy()
    out["display_amount"]=out["amount"].apply(lambda x: convert_from_eur(x, output_currency))
    out["date_only"]=out["date"].dt.date
    out["month"]=out["date"].dt.to_period("M").astype(str)
    return out

def add_expense(user_id: int, expense_date: date, amount: float, category: str, currency: str, note: str = "", subscription: int = 0):
    amount_eur = convert_to_eur(amount, currency)

    supabase.table("expenses").insert({
        "user_id": user_id,
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "category": category,
        "currency": currency,
        "subscription": int(subscription),
        "note": note.strip(),
    }).execute()
def get_monthly_limit(user_id: int):
    res = (
        supabase.table("budgets")
        .select("monthly_limit")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return float(res.data[0]["monthly_limit"]) if res.data else None
def set_monthly_limit(user_id: int, amount_eur: float):
    existing = (
        supabase.table("budgets")
        .select("user_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    payload = {"user_id": user_id, "monthly_limit": float(amount_eur)}

    if existing.data:
        supabase.table("budgets").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("budgets").insert(payload).execute()
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

    for _, row in subs.iterrows():
        row_month_key = pd.to_datetime(row["date"]).strftime("%Y-%m")
        if row_month_key == current_month_key:
            continue

        existing = (
            supabase.table("expenses")
            .select("id")
            .eq("user_id", user_id)
            .eq("subscription", 1)
            .eq("category", str(row["category"]))
            .eq("note", str(row["note"]))
            .eq("amount", float(row["amount"]))
            .gte("date", f"{current_month_key}-01")
            .lt("date", f"{current_month_key}-32")
            .limit(1)
            .execute()
        )

        if not existing.data:
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
def section_start(title, subtitle=None):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle: st.markdown(f'<div class="section-subtitle">{subtitle}</div>', unsafe_allow_html=True)
def section_end(): st.markdown("</div>", unsafe_allow_html=True)
def metric_card(label, value, foot=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-foot">{foot}</div></div>', unsafe_allow_html=True)
def empty_state(text): st.markdown(f'<div class="empty-box">{text}</div>', unsafe_allow_html=True)
def category_badge(category): return f'<span class="cat-badge" style="background:{CATEGORY_COLORS.get(category,CATEGORY_COLORS["Other"])};">{category}</span>'
def savings_bar(saved,target):
    progress=0.0 if target<=0 else max(0.0,min(saved/target,1.0))
    pct=round(progress*100,1); width=max(progress*100,4 if progress>0 else 0)
    st.markdown(f'<div class="goal-wrap"><div class="goal-head"><div class="goal-name">Progress</div><div class="goal-nums">{pct}%</div></div><div class="goal-bar"><div class="goal-fill" style="width:{width}%;"></div></div></div>', unsafe_allow_html=True)
def savings_status(saved,target):
    if target<=0: return '<span class="badge badge-neutral">No target</span>'
    ratio=saved/target
    if ratio>=1: return '<span class="badge badge-good">Completed</span>'
    if ratio>=0.8: return '<span class="badge badge-info">Almost there</span>'
    if ratio>0: return '<span class="badge badge-neutral">In progress</span>'
    return '<span class="badge badge-warn">Started</span>'
def category_pie_chart(cat_df,value_col,label_col):
    if cat_df.empty: return empty_state("Not enough data for pie chart.")
    colors=[CATEGORY_COLORS.get(cat,CATEGORY_COLORS["Other"]) for cat in cat_df[label_col]]
    fig,ax=plt.subplots(figsize=(6,6))
    ax.pie(cat_df[value_col],labels=cat_df[label_col],autopct="%1.1f%%",startangle=90,colors=colors,wedgeprops={"linewidth":1,"edgecolor":"white"},textprops={"fontsize":9})
    ax.axis("equal"); st.pyplot(fig); plt.close(fig)
def render_expense_cards(cards_df, display_currency, show_subscription=True):
    if cards_df.empty: return empty_state("No items to show.")
    for _,row in cards_df.iterrows():
        parts=[category_badge(str(row["category"])),f'<span>{row["date_only"]}</span>']
        if show_subscription and int(row.get("subscription",0))==1: parts.append('<span class="badge badge-info">Subscription</span>')
        note=str(row.get("note","") or "")
        if note: parts.append(f'<span class="expense-note">{note}</span>')
        st.markdown(f'<div class="expense-row"><div class="expense-left">{"".join(parts)}</div><div class="expense-right"><strong>{format_money(float(row["display_amount"]), display_currency)}</strong></div></div>', unsafe_allow_html=True)
def recent_month_options(display_df):
    if display_df.empty or "month" not in display_df.columns: return ["All months"]
    return ["All months"] + sorted(display_df["month"].dropna().unique().tolist(), reverse=True)
def filter_by_month(df, month_value):
    if df.empty or month_value=="All months": return df.copy()
    return df[df["month"]==month_value].copy()

if "user_id" not in st.session_state: st.session_state.user_id=None
if "username" not in st.session_state: st.session_state.username=None

st.sidebar.markdown("## 💸 Expense Tracker")
st.sidebar.caption("Professional personal finance dashboard")
if st.session_state.user_id:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Log out", use_container_width=True):
        st.session_state.user_id=None; st.session_state.username=None; rerun()
else:
    st.sidebar.markdown("### Welcome")
    mode=st.sidebar.radio("Choose mode", ["Login","Register"])
    username=st.sidebar.text_input("Username")
    password=st.sidebar.text_input("Password", type="password")
    if mode=="Login":
        if st.sidebar.button("Login", use_container_width=True):
            user=get_user(username)
            if user and check_password(password,user["password_hash"]):
                st.session_state.user_id=int(user["id"]); st.session_state.username=user["username"]; rerun()
            else: st.sidebar.error("Invalid username or password.")
    else:
        if st.sidebar.button("Create account", use_container_width=True):
            ok,message=register_user(username,password)
            if ok: st.sidebar.success(message)
            else: st.sidebar.error(message)

if not st.session_state.user_id:
    st.markdown('<div class="page-shell">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">💸 Expense Tracker Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">Track spending, subscriptions, savings, and analytics in one place.</div>', unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a: metric_card("Expenses","Smart","Track daily spending with categories")
    with b: metric_card("Savings","Visible","Watch progress toward your goals")
    with c: metric_card("Analytics","Clear","See trends, monthly totals, and export")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

user_id=require_login()
created_subs=upsert_monthly_subscriptions(user_id)
if created_subs: st.toast(f"Added {created_subs} recurring subscription(s) for this month.")

st.sidebar.divider()
display_currency=st.sidebar.selectbox("Display currency", SUPPORTED_CURRENCIES, index=0)
st.sidebar.caption("Live FX rates via ECB + NBU")
page=st.sidebar.radio("Navigation", ["Dashboard","Add Expense","Manage Expenses","Subscriptions","Savings","Analytics","Export"])

st.markdown('<div class="page-shell">', unsafe_allow_html=True)
st.markdown('<div class="main-title">💸 Expense Tracker Pro</div>', unsafe_allow_html=True)
st.markdown(f'<div class="main-subtitle">Welcome back, <b>{st.session_state.username}</b>. Metrics first, then trends, then details.</div>', unsafe_allow_html=True)

df=load_expenses(user_id)
display_df=make_display_df(df, display_currency)
savings_df=load_savings(user_id)
month_options=recent_month_options(display_df)

if page=="Dashboard":
    dashboard_filter=st.selectbox("Month filter", month_options, index=0)
    filtered_df=filter_by_month(display_df, dashboard_filter)
    today=pd.Timestamp.today(); this_month_key=today.strftime("%Y-%m")
    this_month_df=filter_by_month(display_df, this_month_key)
    total_spent=float(filtered_df["display_amount"].sum()) if not filtered_df.empty else 0.0
    month_spent=float(this_month_df["display_amount"].sum()) if not this_month_df.empty else 0.0
    avg_spent=float(filtered_df["display_amount"].mean()) if not filtered_df.empty else 0.0
    tx_count=int(len(filtered_df))
    current_limit_eur=get_monthly_limit(user_id)
    current_limit_display=convert_from_eur(current_limit_eur, display_currency) if current_limit_eur is not None else 0.0
    left_budget=max(current_limit_display-month_spent,0.0) if current_limit_eur is not None else 0.0
    prev_month_key=(today.replace(day=1)-pd.Timedelta(days=1)).strftime("%Y-%m")
    prev_month_df=filter_by_month(display_df, prev_month_key)
    prev_month_total=float(prev_month_df["display_amount"].sum()) if not prev_month_df.empty else 0.0
    delta_vs_last=month_spent-prev_month_total
    c1,c2,c3,c4=st.columns(4)
    with c1: metric_card("Total spent", format_money(total_spent, display_currency), dashboard_filter if dashboard_filter!="All months" else "Selected range")
    with c2: metric_card("This month", format_money(month_spent, display_currency), f"vs last month: {format_money(delta_vs_last, display_currency)}")
    with c3: metric_card("Average expense", format_money(avg_spent, display_currency), f"{tx_count} transactions")
    with c4: metric_card("Budget left", format_money(current_limit_display, display_currency) if current_limit_eur is not None else "Not set", f"{format_money(left_budget, display_currency)} left" if current_limit_eur is not None else "No budget set")
    o1,o2,o3,o4=st.columns(4)
    highest_cat="—"
    if not filtered_df.empty:
        topcat=filtered_df.groupby("category")["display_amount"].sum().sort_values(ascending=False)
        if not topcat.empty: highest_cat=topcat.index[0]
    biggest_tx=float(filtered_df["display_amount"].max()) if not filtered_df.empty else 0.0
    savings_rate=(float(savings_df["saved"].sum())/(float(savings_df["saved"].sum())+total_spent))*100 if total_spent>0 and not savings_df.empty else 0.0
    with o1: st.metric("Transactions", tx_count)
    with o2: st.metric("Top category", highest_cat)
    with o3: st.metric("Largest expense", format_money(biggest_tx, display_currency))
    with o4: st.metric("Savings rate", f"{savings_rate:.1f}%")
    left,right=st.columns([1.35,1])
    with left:
        section_start("Expenses by category","Biggest spending buckets for the selected range.")
        if filtered_df.empty: empty_state("Add your first transaction to see category analytics.")
        else:
            cat_df=filtered_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False)
            st.bar_chart(cat_df.set_index("category"))
            st.dataframe(cat_df.rename(columns={"display_amount": f"Amount ({display_currency})"}), use_container_width=True, hide_index=True)
        section_end()
    with right:
        section_start("Category split","Pie chart with consistent category colors.")
        if filtered_df.empty: empty_state("No category split yet.")
        else:
            category_pie_chart(filtered_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False), "display_amount", "category")
        section_end()
    l2,r2=st.columns([1.05,1])
    with l2:
        section_start("Monthly budget","Use the current month to track whether spending is on target.")
        new_limit_display=st.number_input(f"Monthly limit ({display_currency})", min_value=0.0, value=float(current_limit_display), step=10.0)
        if st.button("Save monthly limit", use_container_width=True):
            set_monthly_limit(user_id, convert_to_eur(new_limit_display, display_currency))
            st.success("Monthly limit saved.")
            rerun()
        if current_limit_eur is not None:
            limit_display=convert_from_eur(current_limit_eur, display_currency)
            progress=min(month_spent/limit_display,1.0) if limit_display>0 else 0.0
            st.progress(progress)
            pct=(month_spent/limit_display*100) if limit_display>0 else 0
            st.markdown(f'<div class="kpi-inline">Used {pct:.1f}% of monthly budget</div>', unsafe_allow_html=True)
            if month_spent>limit_display: st.markdown('<span class="badge badge-warn">Over budget</span>', unsafe_allow_html=True)
            elif pct>=85: st.markdown('<span class="badge badge-info">Close to limit</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="badge badge-good">On track</span>', unsafe_allow_html=True)
        else: empty_state("Set a monthly limit to unlock budget tracking.")
        section_end()
    with r2:
        section_start("Live FX widget","Reference rates for the selected display currency.")
        eur_rates=get_rates_map("EUR"); usd_rates=get_rates_map("USD")
        for label,val in [("EUR / USD",eur_rates.get("USD",0)),("EUR / UAH",eur_rates.get("UAH",0)),("USD / UAH",usd_rates.get("UAH",0))]:
            st.markdown(f'<div class="fx-row"><span>{label}</span><strong>{val:.4f}</strong></div>', unsafe_allow_html=True)
        section_end()
    c5,c6=st.columns(2)
    with c5:
        section_start("Savings goals","Progress cards with statuses and percentages.")
        if savings_df.empty: empty_state("No savings goals yet.")
        else:
            for _,row in savings_df.iterrows():
                st.markdown('<div class="goal-card">', unsafe_allow_html=True)
                st.markdown(f"**{row['name']}**")
                st.markdown(savings_status(float(row["saved"]), float(row["target"])), unsafe_allow_html=True)
                savings_bar(float(row["saved"]), float(row["target"]))
                st.caption(f"{format_money(row['saved'], 'EUR')} / {format_money(row['target'], 'EUR')}")
                st.markdown('</div>', unsafe_allow_html=True)
        section_end()
    with c6:
        section_start("Recent subscriptions","Recurring payments detected in your tracker.")
        subs=filtered_df[filtered_df["subscription"]==1].copy() if not filtered_df.empty else pd.DataFrame()
        if subs.empty: empty_state("No subscriptions in this range.")
        else: render_expense_cards(subs[["date_only","category","display_amount","subscription","note"]].head(6), display_currency, True)
        section_end()
    section_start("Recent expenses","Styled transaction feed with category colors, notes, and badges.")
    if filtered_df.empty: empty_state("No expenses to show for the selected range.")
    else: render_expense_cards(filtered_df[["date_only","category","display_amount","subscription","note"]].head(12), display_currency, True)
    section_end()

elif page=="Add Expense":
    section_start("Detailed expense form","Record a transaction with category, currency, note, and optional recurring status.")
    c1,c2=st.columns(2)
    with c1:
        amount=st.number_input("Amount", min_value=0.01, step=0.5)
        currency=st.selectbox("Currency", SUPPORTED_CURRENCIES)
        category=st.selectbox("Category", DEFAULT_CATEGORIES)
    with c2:
        expense_date=st.date_input("Date", value=date.today())
        note=st.text_input("Note / description")
        is_subscription=st.checkbox("Recurring monthly subscription")
    if st.button("Add expense", use_container_width=True):
        add_expense(user_id, expense_date, amount, category, currency, note, 1 if is_subscription else 0)
        st.success("Expense added."); rerun()
    section_end()

elif page=="Manage Expenses":
    month_filter=st.selectbox("Month filter", month_options, index=0, key="manage_month_filter")
    section_start("Manage expenses","Filter, edit, or delete your existing transactions.")
    if df.empty: empty_state("No expenses yet.")
    else:
        c1,c2=st.columns(2)
        with c1:
            base_filtered=filter_by_month(make_display_df(df,"EUR"), month_filter)
            categories=sorted(base_filtered["category"].dropna().unique().tolist()) if not base_filtered.empty else []
            filter_category=st.selectbox("Filter by category", ["All"]+categories)
        with c2: show_subs_only=st.checkbox("Only subscriptions")
        filtered=filter_by_month(df.copy().assign(month=df["date"].dt.to_period("M").astype(str)), month_filter)
        if filter_category!="All": filtered=filtered[filtered["category"]==filter_category]
        if show_subs_only: filtered=filtered[filtered["subscription"]==1]
        if filtered.empty: empty_state("No matching expenses.")
        else:
            filtered=filtered.copy()
            filtered["label"]=filtered["date"].dt.strftime("%Y-%m-%d")+" | "+filtered["category"].astype(str)+" | "+filtered["amount"].round(2).astype(str)+" EUR | "+filtered["note"].fillna("")
            expense=filtered.loc[filtered["label"]==st.selectbox("Select expense", filtered["label"].tolist())].iloc[0]
            c3,c4=st.columns(2)
            with c3:
                edit_amount_eur=st.number_input("Amount in EUR", min_value=0.0, value=float(expense["amount"]), step=0.5)
                current_category=expense["category"] if expense["category"] in DEFAULT_CATEGORIES else "Other"
                edit_category=st.selectbox("Category", DEFAULT_CATEGORIES, index=DEFAULT_CATEGORIES.index(current_category))
                edit_subscription=st.checkbox("Recurring subscription", value=bool(expense["subscription"]))
            with c4:
                edit_date=st.date_input("Date", value=pd.to_datetime(expense["date"]).date())
                edit_note=st.text_input("Note", value=str(expense["note"] or ""))
                current_currency=expense["currency"] if expense["currency"] in SUPPORTED_CURRENCIES else "EUR"
                edit_currency=st.selectbox("Original currency label", SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(current_currency))
            b1,b2=st.columns(2)
            if b1.button("Save changes", use_container_width=True):
                supabase.table("expenses").update({
                    "amount": float(edit_amount_eur),
                    "category": edit_category,
                    "date": edit_date.isoformat(),
                    "note": edit_note.strip(),
                    "currency": edit_currency,
                    "subscription": 1 if edit_subscription else 0,
                }).eq("id", int(expense["id"])).eq("user_id", user_id).execute()
            
                st.success("Expense updated.")
                rerun()
            if b2.button("Delete expense", use_container_width=True):
                supabase.table("expenses").delete().eq("id", int(expense["id"])).eq("user_id", user_id).execute()
            
                st.success("Expense deleted.")
                rerun()

elif page=="Subscriptions":
    month_filter=st.selectbox("Month filter", month_options, index=0, key="subs_month_filter")
    section_start("Recurring subscriptions","Monthly recurring payments detected from your expenses.")
    subs=filter_by_month(display_df[display_df["subscription"]==1].copy(), month_filter) if not display_df.empty else pd.DataFrame()
    if subs.empty: empty_state("No subscriptions yet for this range.")
    else:
        st.markdown('<span class="badge badge-info">Recurring</span>', unsafe_allow_html=True)
        st.caption(f"Estimated subscriptions in range: {format_money(float(subs['display_amount'].sum()), display_currency)}")
        render_expense_cards(subs[["date_only","category","display_amount","subscription","note"]], display_currency, True)
    section_end()

elif page=="Savings":
    section_start("Savings goals","Create goals, add money, and keep track of progress.")
    c1,c2,c3=st.columns(3)
    with c1: goal_name=st.text_input("Goal name")
    with c2: goal_target=st.number_input("Target (€)", min_value=0.0, step=10.0)
    with c3: goal_saved=st.number_input("Already saved (€)", min_value=0.0, step=10.0)
    if st.button("Add goal", use_container_width=True):
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
    if savings_df.empty: empty_state("No savings goals yet.")
    else:
        for _,row in savings_df.iterrows():
            st.markdown('<div class="goal-card">', unsafe_allow_html=True)
            st.markdown(f"### {row['name']}")
            st.markdown(savings_status(float(row["saved"]), float(row["target"])), unsafe_allow_html=True)
            savings_bar(float(row["saved"]), float(row["target"]))
            st.caption(f"Saved: {format_money(row['saved'], 'EUR')} / Target: {format_money(row['target'], 'EUR')}")
            add_more=st.number_input(f"Add money to {row['name']}", min_value=0.0, step=10.0, key=f"add_goal_{row['id']}")
            x1,x2=st.columns(2)
            if x1.button(f"Update {row['name']}", key=f"update_goal_{row['id']}", use_container_width=True):
    new_saved = float(row["saved"]) + float(add_more)

    supabase.table("savings").update({
        "saved": new_saved
    }).eq("id", int(row["id"])).eq("user_id", user_id).execute()

    st.success("Savings updated.")
    rerun()
            if x2.button(f"Delete {row['name']}", key=f"delete_goal_{row['id']}", use_container_width=True):
    supabase.table("savings").delete().eq("id", int(row["id"])).eq("user_id", user_id).execute()

    st.success("Goal deleted.")
    rerun()

elif page=="Analytics":
    month_filter=st.selectbox("Month filter", month_options, index=0, key="analytics_month_filter")
    analytics_df=filter_by_month(display_df, month_filter)
    section_start("Analytics","KPI cards first, then charts, then comparisons and forecast.")
    if analytics_df.empty: empty_state("Add your first transaction to unlock analytics.")
    else:
        total=float(analytics_df["display_amount"].sum())
        avg=float(analytics_df["display_amount"].mean()) if len(analytics_df) else 0.0
        tx=int(len(analytics_df))
        today=pd.Timestamp.today()
        current_month_df=display_df[(display_df["date"].dt.year==today.year)&(display_df["date"].dt.month==today.month)].copy()
        current_month_total=float(current_month_df["display_amount"].sum()) if not current_month_df.empty else 0.0
        forecast=(current_month_total/max(today.day,1))*monthrange(today.year,today.month)[1]
        a1,a2,a3,a4=st.columns(4)
        with a1: metric_card("Total spending", format_money(total, display_currency), month_filter)
        with a2: metric_card("Average expense", format_money(avg, display_currency), "Per transaction")
        with a3: metric_card("Transactions", str(tx), "Recorded entries")
        with a4: metric_card("Forecast", format_money(forecast, display_currency), "Current month estimate")
        c1,c2=st.columns(2)
        with c1:
            section_start("Monthly trend"); st.line_chart(analytics_df.groupby("month", as_index=False)["display_amount"].sum().set_index("month")); section_end()
        with c2:
            section_start("Category distribution"); category_pie_chart(analytics_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False),"display_amount","category"); section_end()
        c3,c4=st.columns([1,1.1])
        with c3:
            section_start("Daily spending this month")
            if current_month_df.empty: empty_state("No expenses this month.")
            else:
                current_month_df["day"]=current_month_df["date"].dt.day
                st.bar_chart(current_month_df.groupby("day", as_index=False)["display_amount"].sum().set_index("day"))
            section_end()
        with c4:
            section_start("Month-over-month comparison")
            this_month_key=today.strftime("%Y-%m"); prev_month_key=(today.replace(day=1)-pd.Timedelta(days=1)).strftime("%Y-%m")
            grouped=display_df.groupby(["month","category"], as_index=False)["display_amount"].sum()
            this_df=grouped[grouped["month"]==this_month_key][["category","display_amount"]].rename(columns={"display_amount":"this_month"})
            prev_df=grouped[grouped["month"]==prev_month_key][["category","display_amount"]].rename(columns={"display_amount":"last_month"})
            comparison=pd.merge(this_df, prev_df, on="category", how="outer").fillna(0.0)
            comparison["diff"]=comparison["this_month"]-comparison["last_month"]
            comparison["pct_change"]=comparison.apply(lambda row: ((row["diff"]/row["last_month"])*100.0) if row["last_month"]>0 else (100.0 if row["this_month"]>0 else 0.0), axis=1)
            st.dataframe(comparison.sort_values("diff", ascending=False), use_container_width=True, hide_index=True)
            st.markdown(f'<div class="forecast-box"><div class="forecast-label">Forecast for this month</div><div class="forecast-value">{format_money(forecast, display_currency)}</div></div>', unsafe_allow_html=True)
            section_end()
    section_end()

elif page=="Export":
    month_filter=st.selectbox("Month filter", month_options, index=0, key="export_month_filter")
    export_df=filter_by_month(display_df, month_filter)
    section_start("Export your data","Download the current filtered view or the full dataset.")
    if df.empty and savings_df.empty: empty_state("Nothing to export yet.")
    else:
        filtered_expenses=export_df.copy()
        if not filtered_expenses.empty: filtered_expenses["date"]=pd.to_datetime(filtered_expenses["date"]).dt.strftime("%Y-%m-%d")
        full_expenses=df.copy()
        if not full_expenses.empty: full_expenses["date"]=pd.to_datetime(full_expenses["date"]).dt.strftime("%Y-%m-%d")
        c1,c2=st.columns(2)
        with c1:
            st.caption("Filtered export")
            st.download_button("Download filtered CSV", data=filtered_expenses.to_csv(index=False).encode("utf-8"), file_name="expenses_filtered.csv", mime="text/csv", use_container_width=True)
            filtered_excel=io.BytesIO()
            with pd.ExcelWriter(filtered_excel, engine="openpyxl") as writer:
                filtered_expenses.to_excel(writer, index=False, sheet_name="Expenses")
                savings_df.to_excel(writer, index=False, sheet_name="Savings")
            filtered_excel.seek(0)
            st.download_button("Download filtered Excel", data=filtered_excel.getvalue(), file_name="finance_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with c2:
            st.caption("Full export")
            st.download_button("Download full CSV", data=full_expenses.to_csv(index=False).encode("utf-8"), file_name="expenses_full.csv", mime="text/csv", use_container_width=True)
            full_excel=io.BytesIO()
            with pd.ExcelWriter(full_excel, engine="openpyxl") as writer:
                full_expenses.to_excel(writer, index=False, sheet_name="Expenses")
                savings_df.to_excel(writer, index=False, sheet_name="Savings")
            full_excel.seek(0)
            st.download_button("Download full Excel", data=full_excel.getvalue(), file_name="finance_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    section_end()

st.markdown("</div>", unsafe_allow_html=True)




