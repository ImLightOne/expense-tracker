from __future__ import annotations

import streamlit as st

from analytics import detect_duplicates
from common import end_section, l, lcat, lrec, ltx, rerun, section, show_empty
from config import RECURRENCE_OPTIONS, SUPPORTED_CURRENCIES
from db import delete_expense, update_transaction


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    filtered_df = ctx["filtered_df"]
    expense_categories = ctx["expense_categories"]
    income_categories = ctx["income_categories"]

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
            category_options = expense_categories if edit_type == "expense" else income_categories
            current_category = row["category"] if row["category"] in category_options else category_options[-1]
            edit_category = st.selectbox(l("Category", "Категорія", "Kategorie"), category_options, index=category_options.index(current_category), format_func=lcat)
            edit_note = st.text_input(l("Note / description", "Нотатка / опис", "Notiz / Beschreibung"), value=str(row["note"] or ""))
            edit_subscription = st.checkbox(l("Recurring subscription", "Повторювана підписка", "Wiederkehrendes Abo"), value=bool(row["subscription"]), disabled=edit_type == "income")
            edit_recurrence = "monthly"
            if edit_subscription:
                current_recurrence = str(row.get("recurrence") or "monthly")
                recurrence_index = RECURRENCE_OPTIONS.index(current_recurrence) if current_recurrence in RECURRENCE_OPTIONS else RECURRENCE_OPTIONS.index("monthly")
                edit_recurrence = st.selectbox(l("Repeats", "Повторюється", "Wiederholung"), RECURRENCE_OPTIONS, index=recurrence_index, format_func=lrec)

        b1, b2 = st.columns(2)
        if b1.button("Save changes", use_container_width=True):
            update_transaction(user_id, int(row["id"]), edit_date, edit_original_amount, edit_currency, edit_category, edit_note, edit_subscription, edit_type, edit_recurrence)
            st.success(l("Expense updated.", "Транзакцію оновлено.", "Transaktion aktualisiert."))
            rerun()
        if b2.button("Delete expense", use_container_width=True):
            delete_expense(user_id, int(row["id"]))
            st.success(l("Expense deleted.", "Транзакцію видалено.", "Transaktion gelöscht."))
            rerun()

        st.divider()
        st.write(f"**{l('Filtered table', 'Відфільтрована таблиця', 'Gefilterte Tabelle')}**")
        table = managed[["date_only", "type", "category", "merchant", "note", "original_amount", "currency", "display_amount", "subscription", "recurrence"]].copy()
        table["type"] = table["type"].map(ltx)
        table["category"] = table["category"].map(lcat)
        table["recurrence"] = table.apply(lambda r: lrec(r["recurrence"]) if r["subscription"] else "", axis=1)
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
