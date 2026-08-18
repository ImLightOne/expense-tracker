from __future__ import annotations

import streamlit as st

from common import end_section, l, lcat, ltx, rerun, section
from config import DEFAULT_CATEGORIES, INCOME_CATEGORIES
from db import add_transaction
from utils import format_money, parse_quick_add


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    expense_df = ctx["expense_df"]

    section(l("Quick Add", "Швидке додавання", "Schnell hinzufügen"), l("Paste a short sentence, preview the parsed entry, then save it.", "Встав коротке речення, переглянь розбір і збережи.", "Füge einen kurzen Satz ein, prüfe die Erkennung und speichere dann."))
    quick_text = st.text_input(
        l("Quick entry", "Швидкий запис", "Schnelleingabe"),
        value=st.session_state.smart_note,
        placeholder="Examples: 2026-03-17 8.5 EUR coffee at Starbucks | 17.03 24.90 groceries | 12 usd uber",
    )
    preview = parse_quick_add(quick_text, history_df=expense_df)
    st.session_state.smart_note = quick_text
    if quick_text and preview["ok"]:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(l("Amount", "Сума", "Betrag"), format_money(preview["amount"], preview["currency"]))
        with c2:
            st.metric(l("Date", "Дата", "Datum"), str(preview["date"]))
        with c3:
            st.metric(l("Category", "Категорія", "Kategorie"), lcat(str(preview["category"])))
        with c4:
            st.metric("Type", ltx(preview["tx_type"]))
        confidence_labels = {
            "high": l("High confidence", "Висока впевненість", "Hohe Sicherheit"),
            "medium": l("Medium confidence", "Середня впевненість", "Mittlere Sicherheit"),
            "low": l("Low confidence", "Низька впевненість", "Niedrige Sicherheit"),
        }
        st.caption(
            f"{l('Category source', 'Джерело категорії', 'Kategoriequelle')}: {preview.get('category_reason', 'fallback')} · "
            f"{confidence_labels.get(str(preview.get('confidence', 'low')), str(preview.get('confidence', 'low')).title())}"
            + (f" · {l('Merchant guess', 'Ймовірний продавець', 'Vermuteter Händler')}: {preview.get('merchant_guess')}" if preview.get('merchant_guess') else "")
        )
        category_options = INCOME_CATEGORIES if preview["tx_type"] == "income" else DEFAULT_CATEGORIES
        default_index = category_options.index(preview["category"]) if preview["category"] in category_options else len(category_options)-1
        manual_category = st.selectbox(l("Adjust category", "Змінити категорію", "Kategorie anpassen"), category_options, index=default_index, format_func=lcat)
        note = st.text_input(l("Note / merchant", "Нотатка / продавець", "Notiz / Händler"), value=str(preview["note"]))
        subscription = st.checkbox(l("Recurring monthly subscription", "Щомісячна повторювана підписка", "Monatlich wiederkehrendes Abo"), value=bool(preview["subscription"]), disabled=preview["tx_type"] == "income")
        if st.button(l("Save quick entry", "Зберегти швидкий запис", "Schnelleingabe speichern"), type="primary", use_container_width=True):
            add_transaction(
                user_id,
                preview["date"],
                preview["amount"],
                manual_category,
                preview["currency"],
                preview["tx_type"],
                note,
                1 if subscription else 0,
            )
            st.success(l("Quick entry saved.", "Швидкий запис збережено.", "Schnelleingabe gespeichert."))
            st.session_state.smart_note = ""
            rerun()
    elif quick_text:
        st.warning(preview["error"])
    end_section()

    section(l("Why this helps", "Чому це корисно", "Warum das hilft"), l("Useful for mobile, quick logging, and chat-style input.", "Зручно для телефону, швидкого внесення і вводу як у чаті.", "Nützlich für Handy, schnelle Erfassung und chatartigen Input."))
    st.write(l("The parser detects date, amount, currency, subscription hints, and suggests a category from the note.", "Парсер визначає дату, суму, валюту, ознаки підписки та пропонує категорію з нотатки.", "Der Parser erkennt Datum, Betrag, Währung, Abo-Hinweise und schlägt anhand der Notiz eine Kategorie vor."))
    end_section()
