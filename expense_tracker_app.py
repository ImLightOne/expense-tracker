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

# --- Convert Date to datetime ---
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).reset_index(drop=True)

st.title("💸 Мобільний трекер витрат")

# --- Add Expense ---
st.header("Додати витрату")
with st.form("add_expense"):
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Сума (€)", min_value=0.01, step=0.5)
        category = st.selectbox("Категорія", [
            "Food", "Transport", "Rent", "Entertainment", "Health",
            "Shopping", "Education", "Travel", "Bills", "Other"
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

# --- Monthly Report ---
st.header("Звіт за місяць")
month_input = st.text_input("Місяць (yyyy-mm або залишити пустим для всіх витрат)")

if month_input:
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    report_df = df[df["Month"]==month_input]
else:
    report_df = df.copy()

if not report_df.empty:
    st.subheader(f"Загальні витрати: {report_df['Amount'].sum():.2f} €")
    st.subheader("Витрати по категоріях")
    cat_report = report_df.groupby("Category")["Amount"].sum().reset_index()
    st.table(cat_report)

    # --- Pie chart ---
    st.subheader("Кругова діаграма")
    fig1, ax1 = plt.subplots()
    ax1.pie(cat_report["Amount"], labels=cat_report["Category"], autopct="%1.1f%%", startangle=90)
    ax1.axis("equal")
    st.pyplot(fig1)

    # --- Bar chart ---
    st.subheader("Бар-діаграма")
    fig2, ax2 = plt.subplots()
    ax2.barh(cat_report["Category"], cat_report["Amount"], color='skyblue')
    ax2.set_xlabel("Сума (€)")
    st.pyplot(fig2)

    # --- Max expense ---
    max_expense = report_df.loc[report_df['Amount'].idxmax()]
    st.subheader("Найбільша витрата")
    st.write(f"{max_expense['Category']} - {max_expense['Amount']}€ на {max_expense['Date'].strftime('%Y-%m-%d')} ({max_expense['Note']})")
else:
    st.info("Немає витрат для цього періоду")
