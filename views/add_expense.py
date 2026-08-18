from __future__ import annotations

from datetime import date

import streamlit as st

from common import end_section, l, lcat, ltx, rerun, section
from config import DEFAULT_CATEGORIES, INCOME_CATEGORIES, SUPPORTED_CURRENCIES
from db import add_transaction
from utils import infer_category


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]

    section(l("Add transaction", "Додати транзакцію", "Transaktion hinzufügen"), l("Manual form for both expenses and income.", "Ручна форма для витрат і доходів.", "Manuelles Formular für Ausgaben und Einnahmen."))
    col1, col2 = st.columns(2)
    with col1:
        tx_type = st.selectbox(l("Transaction type", "Тип транзакції", "Transaktionstyp"), ["expense", "income"], format_func=lambda x: ltx(x))
        amount = st.number_input(l("Amount", "Сума", "Betrag"), min_value=0.01, step=0.5)
        currency = st.selectbox(l("Currency", "Валюта", "Währung"), SUPPORTED_CURRENCIES)
        note = st.text_input(l("Note / description", "Нотатка / опис", "Notiz / Beschreibung"))
        suggested_category = infer_category(note, fallback="Other Income" if tx_type == "income" else "Other")["category"] if note else ("Other Income" if tx_type == "income" else "Other")
    with col2:
        expense_date = st.date_input(l("Date", "Дата", "Datum"), value=date.today())
        category_options = INCOME_CATEGORIES if tx_type == "income" else DEFAULT_CATEGORIES
        category = st.selectbox(l("Category", "Категорія", "Kategorie"), category_options, index=category_options.index(suggested_category) if suggested_category in category_options else len(category_options)-1, format_func=lcat)
        is_subscription = st.checkbox(l("Recurring monthly subscription", "Щомісячна повторювана підписка", "Monatlich wiederkehrendes Abo"), disabled=tx_type == "income")

    if note:
        st.caption(l("Suggested category from note: {suggested_category}", "Запропонована категорія з нотатки: {suggested_category}", "Vorgeschlagene Kategorie aus der Notiz: {suggested_category}").format(suggested_category=suggested_category))
    if st.button(l("Save transaction", "Зберегти транзакцію", "Transaktion speichern"), use_container_width=True):
        add_transaction(user_id, expense_date, amount, category, currency, tx_type, note, 1 if is_subscription else 0)
        st.success(l("Transaction added.", "Транзакцію додано.", "Transaktion hinzugefügt."))
        rerun()
    end_section()
