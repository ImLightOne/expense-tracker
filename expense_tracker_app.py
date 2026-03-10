import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import calendar
import requests

# ---------- CONFIG ----------
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="💰",
    layout="wide"
)

FILE = "expenses.csv"

# ---------- UI STYLE ----------
st.markdown("""
<style>

body {
background-color:#0e1117;
}

.metric-card{
background:#1e1e1e;
padding:20px;
border-radius:15px;
box-shadow:0px 4px 10px rgba(0,0,0,0.3);
}

</style>
""", unsafe_allow_html=True)

# ---------- LOGIN ----------
PASSWORD = "1234"

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:

    st.title("🔐 Login")

    password = st.text_input("PIN", type="password")

    if st.button("Login"):
        if password == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Wrong PIN")

    st.stop()

# ---------- LOAD DATA ----------
try:
    df = pd.read_csv(FILE)
except:
    df = pd.DataFrame(columns=["Date","Amount","Category","Note"])

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

df = df.dropna(subset=["Date"])

# ---------- LOAD SUBSCRIPTIONS ----------
try:
    subs = pd.read_csv("subscriptions.csv")
except:
    subs = pd.DataFrame(columns=["Name","Amount","Category"])

# ---------- APPLY SUBSCRIPTIONS ----------

today = datetime.today()

for i, sub in subs.iterrows():

    name = sub["Name"]
    amount = sub["Amount"]
    category = sub["Category"]

    exists = df[
        (df["Note"] == name) &
        (df["Date"].dt.month == today.month) &
        (df["Date"].dt.year == today.year)
    ]

    if exists.empty:

        new_row = pd.DataFrame({
            "Date":[pd.to_datetime(f"{today.year}-{today.month}-01")],
            "Amount":[amount],
            "Category":[category],
            "Note":[name]
        })

        df = pd.concat([df,new_row])
df.to_csv(FILE,index=False)

# ---------- SAVINGS ----------
try:
    savings = pd.read_csv("savings.csv")
except:
    savings = pd.DataFrame(columns=["Name","Target","Saved"])

# ---------- CURRENCY ----------
def get_rate(currency):

    if currency == "EUR":
        return 1

    url = f"https://api.exchangerate.host/latest?base={currency}&symbols=EUR"

    try:
        r = requests.get(url).json()
        return r["rates"]["EUR"]
    except:
        return 1


# ---------- SIDEBAR ----------
page = st.sidebar.radio(
"Navigation",
[
"Dashboard",
"Add Expense",
"Manage Expenses",
"Subscriptions",
"Savings",
"Analytics",
"Export"
]
)


currency = st.sidebar.selectbox(
"Currency",
["EUR","USD","UAH"]
)

rate = get_rate(currency)

# ---------- DASHBOARD ----------
if page == "Dashboard":

    st.title("📊 Financial Dashboard")

    col1,col2,col3,col4 = st.columns(4)

    total = df["Amount"].sum()

    this_month = df[df["Date"].dt.month == datetime.today().month]

    monthly = this_month["Amount"].sum()

    avg = df["Amount"].mean() if len(df)>0 else 0

    transactions = len(df)

    col1.metric("Total Spent", f"{total:.2f} €")
    col2.metric("This Month", f"{monthly:.2f} €")
    col3.metric("Average Expense", f"{avg:.2f} €")
    col4.metric("Transactions", transactions)

    st.subheader("Expenses by Category")

    cat = df.groupby("Category")["Amount"].sum()

    st.bar_chart(cat)

    st.subheader("Monthly Trend")

    trend = df.copy()

    trend["Month"] = trend["Date"].dt.to_period("M")

    trend = trend.groupby("Month")["Amount"].sum()

    st.line_chart(trend)

    # ---------- FORECAST ----------
    today = datetime.today()

    current_month = df[df["Date"].dt.month == today.month]

    E_current = current_month["Amount"].sum()

    D_passed = today.day

    D_total = calendar.monthrange(today.year,today.month)[1]

    forecast = (E_current/D_passed)*D_total if D_passed>0 else 0

    st.metric("Forecast end of month", f"{forecast:.2f} €")


# ---------- ADD EXPENSE ----------
if page == "Add Expense":

    st.title("➕ Add Expense")

    col1,col2 = st.columns(2)

    with col1:

        amount = st.number_input("Amount", min_value=0.01)

        category = st.selectbox(
        "Category",
        [
        "Food","Transport","Rent","Entertainment",
        "Shopping","Health","Sports","Bills","Cafe","Other"
        ])

    with col2:

        note = st.text_input("Note")

        date = st.date_input("Date")

    if st.button("Add Expense"):

        amount_eur = amount * rate

        new = pd.DataFrame({
        "Date":[pd.to_datetime(date)],
        "Amount":[amount_eur],
        "Category":[category],
        "Note":[note]
        })

        df = pd.concat([df,new])

        df.to_csv(FILE,index=False)

        st.success("Expense Added")

# ---------- SUBSCRIPTIONS ----------
if page == "Subscriptions":

    st.title("🔁 Subscriptions")

    # ---------- ADD BUTTON ----------
    if "add_sub" not in st.session_state:
        st.session_state.add_sub = False

    if st.button("➕ Add Subscription"):
        st.session_state.add_sub = True

    # ---------- ADD FORM ----------
    if st.session_state.add_sub:

        st.subheader("New Subscription")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name")
            amount = st.number_input("Monthly Amount", min_value=0.0)

        with col2:
            category = st.text_input("Category")

        col1, col2 = st.columns(2)

        if col1.button("Save Subscription"):

            new = pd.DataFrame({
                "Name":[name],
                "Amount":[amount],
                "Category":[category]
            })

            subs = pd.concat([subs,new])

            subs.to_csv("subscriptions.csv",index=False)

            st.success("Subscription Added")

            st.session_state.add_sub = False
            st.rerun()

        if col2.button("Cancel"):
            st.session_state.add_sub = False
            st.rerun()

    st.divider()

    # ---------- LIST ----------
    st.subheader("Your Subscriptions")

    if subs.empty:
        st.info("No subscriptions yet")
    else:

        for i,row in subs.iterrows():

            col1,col2,col3,col4 = st.columns([3,2,2,1])

            col1.write(f"**{row['Name']}**")
            col2.write(f"{row['Amount']} €")
            col3.write(row["Category"])

            if col4.button("Edit", key=f"edit{i}"):

                st.session_state.edit_sub = i

        # ---------- EDIT ----------
        if "edit_sub" in st.session_state:

            idx = st.session_state.edit_sub

            sub = subs.loc[idx]

            st.divider()
            st.subheader("Edit Subscription")

            col1,col2 = st.columns(2)

            with col1:
                new_name = st.text_input("Name", value=sub["Name"])
                new_amount = st.number_input("Amount", value=float(sub["Amount"]))

            with col2:
                new_category = st.text_input("Category", value=sub["Category"])

            col1,col2 = st.columns(2)

            if col1.button("💾 Save Changes"):

                subs.loc[idx,"Name"] = new_name
                subs.loc[idx,"Amount"] = new_amount
                subs.loc[idx,"Category"] = new_category

                subs.to_csv("subscriptions.csv",index=False)

                st.success("Subscription updated")

                del st.session_state.edit_sub
                st.rerun()

            if col2.button("🗑 Delete Subscription"):

                subs = subs.drop(idx)

                subs.to_csv("subscriptions.csv",index=False)

                st.success("Subscription deleted")

                del st.session_state.edit_sub
                st.rerun()


# ---------- SAVINGS ----------
if page == "Savings":

    st.title("🎯 Savings Goals")

    for i,row in savings.iterrows():

        progress = row["Saved"]/row["Target"]

        st.subheader(row["Name"])

        st.progress(progress)

        st.write(f"{row['Saved']} / {row['Target']} €")

    name = st.text_input("Goal")

    target = st.number_input("Target Amount")

    saved = st.number_input("Already Saved")

    if st.button("Add Goal"):

        new = pd.DataFrame({
        "Name":[name],
        "Target":[target],
        "Saved":[saved]
        })

        savings = pd.concat([savings,new])

        savings.to_csv("savings.csv",index=False)

        st.success("Goal Added")

# ---------- ANALYTICS ----------
if page == "Analytics":

    st.title("📈 Analytics")

    df["Month"] = df["Date"].dt.to_period("M")

    this_month = df[df["Month"] == df["Month"].max()]

    last_month = df[df["Month"] == (df["Month"].max()-1)]

    this_cat = this_month.groupby("Category")["Amount"].sum()

    last_cat = last_month.groupby("Category")["Amount"].sum()

    compare = pd.concat([this_cat,last_cat],axis=1)

    compare.columns=["This Month","Last Month"]

    compare["Change %"] = (
    (compare["This Month"] - compare["Last Month"])
    / compare["Last Month"]
    )*100

    st.subheader("Month Comparison")

    st.dataframe(compare)

    st.subheader("Fastest Growing Categories")

    growth = compare.sort_values("Change %", ascending=False)

    st.dataframe(growth.head(5))

# ---------- EXPORT ----------
if page == "Export":

    st.title("Export Data")

    st.download_button(
    "Download CSV",
    df.to_csv(index=False),
    "expenses.csv"
    )

    df.to_excel("expenses.xlsx")

    st.download_button(
    "Download Excel",
    open("expenses.xlsx","rb"),
    "expenses.xlsx"
    )
# ---------- MANAGE EXPENSES ----------
if page == "Manage Expenses":

    st.title("✏️ Manage Expenses")

    if df.empty:
        st.info("No expenses yet")
    else:

        df_display = df.copy()

        df_display["Label"] = (
            df_display["Date"].dt.strftime("%Y-%m-%d")
            + " | "
            + df_display["Category"]
            + " | "
            + df_display["Amount"].round(2).astype(str)
            + " €"
            + " | "
            + df_display["Note"].fillna("")
        )

        choice = st.selectbox(
            "Select expense",
            df_display["Label"]
        )

        idx = df_display[df_display["Label"] == choice].index[0]

        expense = df.loc[idx]

        st.subheader("Edit Expense")

        col1,col2 = st.columns(2)

        with col1:

            new_amount = st.number_input(
                "Amount",
                value=float(expense["Amount"])
            )

            new_category = st.text_input(
                "Category",
                value=expense["Category"]
            )

        with col2:

            new_note = st.text_input(
                "Note",
                value=str(expense["Note"])
            )

            new_date = st.date_input(
                "Date",
                value=expense["Date"]
            )

        col1,col2 = st.columns(2)

        if col1.button("💾 Save Changes"):

            df.loc[idx,"Amount"] = new_amount
            df.loc[idx,"Category"] = new_category
            df.loc[idx,"Note"] = new_note
            df.loc[idx,"Date"] = pd.to_datetime(new_date)

            df.to_csv(FILE,index=False)

            st.success("Expense updated")

        if col2.button("🗑 Delete Expense"):

            df = df.drop(idx)

            df.to_csv(FILE,index=False)

            st.success("Expense deleted")

