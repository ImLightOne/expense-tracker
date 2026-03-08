import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

FILE = "expenses.csv"

# --- Load or create CSV ---
try:
    df = pd.read_csv(FILE)
except FileNotFoundError:
    df = pd.DataFrame(columns=["Date","Amount","Category","Note"])
    df.to_csv(FILE,index=False)

# --- Convert Date ---
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).reset_index(drop=True)

st.set_page_config(page_title="Expense Tracker Ultimate", layout="wide")
st.title("💸 Expense Tracker Ultimate")

# --- Budget setup ---
st.sidebar.header("Налаштування бюджету")
monthly_budget = st.sidebar.number_input("Бюджет на місяць (€)", min_value=0.0, step=10.0)

# --- Add Expense ---
st.header("Додати витрату")
with st.form("add_expense"):
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Сума (€)", min_value=0.01, step=0.5)
        category = st.selectbox("Категорія", [
            "Food", "Transport", "Rent", "Entertainment", "Health",
            "Shopping", "Education", "Travel", "Bills", "Phone",
            "Sports", "Gifts", "Other"
        ])
    with col2:
        date = st.date_input("Дата", value=datetime.today())
        note = st.text_input("Примітка")
    
    submitted = st.form_submit_button("Додати")
    if submitted:
        new_row = pd.DataFrame({
            "Date":[pd.to_datetime(date)],
            "Amount":[amount],
            "Category":[category],
            "Note":[note]
        })
        df = pd.concat([df,new_row], ignore_index=True)
        df.to_csv(FILE,index=False)
        st.success("✅ Витрату додано!")

# --- Delete Expense ---
st.header("Видалити витрату")
if not df.empty:
    df_display = df.copy()
    df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d")
    df_display["Info"] = df_display["Category"] + " - " + df_display["Amount"].astype(str) + "€ - " + df_display["Note"].fillna("")
    delete_choice = st.selectbox("Оберіть витрату для видалення", df_display["Info"])
    if st.button("Видалити"):
        idx = df_display[df_display["Info"]==delete_choice].index[0]
        df = df.drop(df.index[idx]).reset_index(drop=True)
        df.to_csv(FILE,index=False)
        st.success(f"✅ Витрату видалено!")
else:
    st.info("Немає витрат для видалення")

# --- Filters and Reports ---
st.header("Звіт")
col1, col2 = st.columns(2)
with col1:
    month_input = st.text_input("Місяць (yyyy-mm, залишити пустим для всіх витрат)")
with col2:
    sort_option = st.selectbox("Сортувати за", ["Date", "Amount", "Category"])

# Filter by month
if month_input:
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    report_df = df[df["Month"]==month_input]
else:
    report_df = df.copy()

if not report_df.empty:
    if sort_option == "Date":
        report_df = report_df.sort_values("Date", ascending=False)
    elif sort_option == "Amount":
        report_df = report_df.sort_values("Amount", ascending=False)
    else:
        report_df = report_df.sort_values("Category", ascending=True)

    total = report_df['Amount'].sum()
    st.subheader(f"Загальні витрати: {total:.2f} €")

    # Budget alert
    if monthly_budget > 0 and month_input:
        if total > monthly_budget:
            st.warning(f"⚠️ Перевищено бюджет на {total-monthly_budget:.2f} €!")
        else:
            st.success(f"Бюджет у межах: залишок {monthly_budget-total:.2f} €")

    st.subheader("Витрати по категоріях")
    cat_report = report_df.groupby("Category")["Amount"].sum().reset_index()
    st.table(cat_report)

    # Pie chart
    st.subheader("Кругова діаграма")
    colors = plt.cm.tab20.colors
    fig1, ax1 = plt.subplots()
    ax1.pie(cat_report["Amount"], labels=cat_report["Category"], autopct="%1.1f%%", startangle=90, colors=colors[:len(cat_report)])
    ax1.axis("equal")
    st.pyplot(fig1)

    # Bar chart
    st.subheader("Бар-діаграма")
    fig2, ax2 = plt.subplots(figsize=(6,4))
    ax2.barh(cat_report["Category"], cat_report["Amount"], color='skyblue')
    ax2.set_xlabel("Сума (€)")
    st.pyplot(fig2)

    # Line chart (trend by month)
    st.subheader("Тренд витрат по місяцях")
    trend = df.copy()
    trend["Month"] = trend["Date"].dt.to_period("M")
    trend_summary = trend.groupby("Month")["Amount"].sum()
    st.line_chart(trend_summary)

    # Max expense
    max_expense = report_df.loc[report_df['Amount'].idxmax()]
    st.subheader("Найбільша витрата")
    st.write(f"{max_expense['Category']} - {max_expense['Amount']}€ на {max_expense['Date'].strftime('%Y-%m-%d')} ({max_expense['Note']})")

    # Recent 10 expenses
    st.subheader("Останні 10 витрат")
    recent = report_df.sort_values("Date", ascending=False).head(10)
    recent["Date"] = recent["Date"].dt.strftime("%Y-%m-%d")
    st.table(recent[["Date","Category","Amount","Note"]])
else:
    st.info("Немає витрат для цього періоду")
