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
.savings-card {
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
    color:white;
    font-weight:500;
}

.s-red {
    background:#5c1a1a;
}

.s-orange {
    background:#5c3d1a;
}

.s-green {
    background:#1f4d2e;
}

.s-blue {
    background:#1a3b5c;
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

    # ---------- TOTAL METRICS ----------
    col1, col2, col3, col4 = st.columns(4)

    total_spent = df["Amount"].sum()
    this_month_df = df[df["Date"].dt.month == datetime.today().month]
    this_month_spent = this_month_df["Amount"].sum()
    avg_expense = df["Amount"].mean() if len(df) > 0 else 0
    transactions = len(df)

    col1.metric("Total Spent", f"{total_spent:.2f} €")
    col2.metric("This Month", f"{this_month_spent:.2f} €")
    col3.metric("Average Expense", f"{avg_expense:.2f} €")
    col4.metric("Transactions", transactions)

    st.divider()

    # ---------- EXPENSES BY CATEGORY ----------
    st.subheader("Expenses by Category")
    import plotly.express as px

    cat_df = df.groupby("Category")["Amount"].sum().reset_index()
    fig_cat = px.bar(cat_df, x="Category", y="Amount", color="Amount",
                     color_continuous_scale="Tealgrn", text="Amount")
    fig_cat.update_layout(yaxis_title="Amount (€)", xaxis_title="Category")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.divider()

    # ---------- TOP 3 EXPENSES ----------
    st.subheader("Top 3 Expense Categories This Month")
    top3 = this_month_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(3)
    st.table(top3.reset_index().rename(columns={"Amount":"This Month Spend (€)"}))

    st.divider()

    # ---------- HEATMAP OF DAILY SPENDING ----------
    st.subheader("Heatmap: Daily Spending")
    daily_df = this_month_df.groupby(this_month_df["Date"].dt.day)["Amount"].sum().reset_index()
    daily_df.rename(columns={"Date":"Day"}, inplace=True)

    fig_heat = px.density_heatmap(
        daily_df,
        x="Day",
        y="Amount",        # одне поле
        z="Amount",        # інтенсивність кольору
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(fig_heat, use_container_width=True)


    # ---------- MONTHLY COMPARISON ----------
    st.subheader("Monthly Comparison")
    df["Month"] = df["Date"].dt.to_period("M")
    month_cat = df.groupby(["Month","Category"])["Amount"].sum().reset_index()
    last_month_str = (datetime.today().replace(day=1) - pd.Timedelta(days=1)).strftime("%Y-%m")
    this_month_str = datetime.today().strftime("%Y-%m")

    last_df = month_cat[month_cat["Month"]==last_month_str]
    this_df = month_cat[month_cat["Month"]==this_month_str]

    comparison = pd.merge(this_df, last_df, on="Category", how="outer", suffixes=('_this','_last')).fillna(0)
    comparison["Diff"] = comparison["Amount_this"] - comparison["Amount_last"]
    comparison["% Change"] = comparison.apply(lambda x: (x["Diff"]/x["Amount_last"]*100) if x["Amount_last"]>0 else 100, axis=1)

    st.dataframe(comparison[["Category","Amount_this","Amount_last","Diff","% Change"]])

    st.divider()

    # ---------- BUDGET ALERT ----------
    st.subheader("Budget Alert / Forecast")
    days_passed = datetime.today().day
    days_total = (pd.Period(datetime.today(), freq='M').days_in_month)
    forecast_total = (this_month_spent / days_passed) * days_total if days_passed > 0 else this_month_spent
    st.metric("Forecast Total Spend", f"{forecast_total:.2f} €")

    if "monthly_limit" in st.session_state:
        limit = st.session_state.monthly_limit
        if forecast_total > limit:
            st.warning(f"You may exceed your monthly limit ({limit} €)")
        else:
            st.success(f"You’re on track to stay under your limit ({limit} €)")

    st.divider()

    # ---------- SAVINGS PROGRESS ----------
    st.subheader("💰 Savings Progress")
    if not savings.empty:
        total_saved = savings["Saved"].sum()
        total_target = savings["Target"].sum()
        progress = total_saved / total_target if total_target > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("Total Saved", f"{total_saved:.2f} €")
        col2.metric("Savings Target", f"{total_target:.2f} €")
        st.progress(progress)
    else:
        st.info("No savings goals yet")

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

    # Поділ на активні та завершені цілі
    if savings.empty:
        st.info("No savings goals yet")
    else:
        active_goals = savings[savings["Saved"] < savings["Target"]]
        completed_goals = savings[savings["Saved"] >= savings["Target"]]

        st.subheader("Active Goals")

        # ---------- ACTIVE GOALS ----------
        for i,row in active_goals.iterrows():

            progress = row["Saved"] / row["Target"] if row["Target"] > 0 else 0
            percent = int(progress*100)

            # ---------- GOAL ACHIEVED ----------
            if row["Saved"] >= row["Target"] and row["Target"] > 0:
                st.success(f"🎉 Goal '{row['Name']}' achieved!")
                if f"celebrated_{i}" not in st.session_state:
                    st.balloons()
                    st.session_state[f"celebrated_{i}"] = True

            # ---------- COLOR LOGIC ----------
            if progress < 0.3:
                color = "s-red"
            elif progress < 0.7:
                color = "s-orange"
            elif progress < 1:
                color = "s-green"
            else:
                color = "s-blue"

            st.markdown(
                f"""
                <div class="savings-card {color}">
                <h3>{row['Name']}</h3>
                <p>{row['Saved']} € / {row['Target']} €</p>
                <p><b>{percent}% completed</b></p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.progress(progress)

            # ---------- ADD / DELETE ----------
            col1,col2,col3 = st.columns(3)

            with col1:
                add_money = st.number_input(
                    "Add money",
                    min_value=0.0,
                    key=f"add{i}"
                )

            with col2:
                if st.button("➕ Add", key=f"addbtn{i}"):
                    savings.loc[i,"Saved"] += add_money
                    savings.to_csv("savings.csv",index=False)
                    st.rerun()

            with col3:
                if st.button("🗑 Delete", key=f"del{i}"):
                    savings = savings.drop(i)
                    savings.to_csv("savings.csv",index=False)
                    st.rerun()

            st.divider()

        # ---------- COMPLETED GOALS ----------
        st.divider()
        st.subheader("🏆 Completed Goals")

        if completed_goals.empty:
            st.write("No completed goals yet")

        for i,row in completed_goals.iterrows():

            st.markdown(
                f"""
                <div class="savings-card s-blue">
                <h3>🏆 {row['Name']}</h3>
                <p>{row['Saved']} € / {row['Target']} €</p>
                <p><b>Goal achieved!</b></p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.progress(1.0)

            col1,col2 = st.columns(2)

            with col1:
                if st.button("🎉 Celebrate", key=f"celebrate{i}"):
                    st.balloons()

            with col2:
                if st.button("🗑 Remove goal", key=f"remove{i}"):
                    savings = savings.drop(i)
                    savings.to_csv("savings.csv",index=False)
                    st.rerun()

    # ---------- CREATE NEW GOAL ----------
    st.divider()
    st.subheader("➕ Create New Goal")

    name = st.text_input("Goal Name")
    target = st.number_input("Target Amount")
    saved = st.number_input("Already Saved")

    if st.button("Create Goal"):
        new = pd.DataFrame({
            "Name":[name],
            "Target":[target],
            "Saved":[saved]
        })
        savings = pd.concat([savings,new])
        savings.to_csv("savings.csv",index=False)
        st.rerun()


# ---------- ANALYTICS ----------
if page == "Analytics":

    st.title("📊 Financial Analytics")

    # ---------- TOTAL METRICS ----------
    col1,col2,col3,col4 = st.columns(4)

    total_spent = df["Amount"].sum()
    monthly_df = df[df["Date"].dt.month == datetime.today().month]
    this_month = monthly_df["Amount"].sum()
    avg = df["Amount"].mean() if len(df) > 0 else 0
    transactions = len(df)

    col1.metric("Total Spent", f"{total_spent:.2f} €")
    col2.metric("This Month", f"{this_month:.2f} €")
    col3.metric("Average Expense", f"{avg:.2f} €")
    col4.metric("Transactions", transactions)

    st.divider()

    # ---------- SPENDING BY CATEGORY ----------
    st.subheader("Expenses by Category")

    import plotly.express as px

    cat_df = df.groupby("Category")["Amount"].sum().reset_index()
    fig_cat = px.bar(cat_df, x="Category", y="Amount", color="Amount",
                     color_continuous_scale="Tealgrn", text="Amount")
    fig_cat.update_layout(yaxis_title="Amount (€)", xaxis_title="Category")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.divider()

    # ---------- MONTHLY COMPARISON ----------
    st.subheader("Monthly Comparison")

    df["Month"] = df["Date"].dt.to_period("M")
    month_cat = df.groupby(["Month","Category"])["Amount"].sum().reset_index()
    last_month = (datetime.today().replace(day=1) - pd.Timedelta(days=1)).strftime("%Y-%m")
    this_month_str = datetime.today().strftime("%Y-%m")

    last_df = month_cat[month_cat["Month"]==last_month]
    this_df = month_cat[month_cat["Month"]==this_month_str]

    comparison = pd.merge(this_df, last_df, on="Category", how="outer", suffixes=('_this','_last')).fillna(0)
    comparison["Diff"] = comparison["Amount_this"] - comparison["Amount_last"]
    comparison["% Change"] = comparison.apply(lambda x: (x["Diff"]/x["Amount_last"]*100) if x["Amount_last"]>0 else 100, axis=1)

    st.dataframe(comparison[["Category","Amount_this","Amount_last","Diff","% Change"]])

    st.divider()

    # ---------- SPENDING GROWTH ALERT ----------
    st.subheader("📈 Categories with Highest Growth")

    growth = comparison.sort_values("Diff", ascending=False)
    st.write(growth[["Category","Diff","% Change"]].head(5))

    st.divider()

    # ---------- FORECAST ----------
    st.subheader("Forecast for This Month")

    days_passed = datetime.today().day
    days_total = (pd.Period(datetime.today(), freq='M').days_in_month)

    forecast_total = (this_month / days_passed) * days_total if days_passed>0 else this_month
    st.metric("Forecast Total Spend", f"{forecast_total:.2f} €")

    if "monthly_limit" in st.session_state:
        limit = st.session_state.monthly_limit
        if forecast_total > limit:
            st.warning(f"You may exceed your monthly limit of {limit} €!")
        else:
            st.success(f"You're on track to stay under your limit ({limit} €)")

    st.divider()

    # ---------- SAVINGS PROGRESS ----------
    st.subheader("💰 Savings Progress")

    if not savings.empty:
        total_saved = savings["Saved"].sum()
        total_target = savings["Target"].sum()
        progress = total_saved / total_target if total_target > 0 else 0

        col1,col2 = st.columns(2)
        col1.metric("Total Saved", f"{total_saved:.2f} €")
        col2.metric("Savings Target", f"{total_target:.2f} €")
        st.progress(progress)
    else:
        st.info("No savings goals yet")

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
