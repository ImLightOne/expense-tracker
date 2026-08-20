from __future__ import annotations

import streamlit as st

from config import RECURRENCE_OPTIONS
from common import end_section, l, lcat, lrec, ltx, rerun, section
from db import add_transaction
from utils import format_money, parse_quick_add


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    # Smart category matching needs a *stable* pool of past transactions to
    # learn from. ctx["expense_df"] looked like the obvious choice but is
    # actually the dashboard's currently-filtered view (bound by whatever
    # date range / category / search text the sidebar happens to have
    # selected right now, from apply_filters() in expense_tracker_app.py) —
    # so the exact same Quick Add text used to suggest a different category
    # depending on unrelated sidebar filter state, which is what read as
    # "random" behavior. ctx["base_display_df"] is the full (unfiltered by
    # sidebar) history within the loaded window, so suggestions here now
    # depend only on what was actually typed.
    history_df = ctx.get("base_display_df")
    expense_categories = ctx["expense_categories"]
    income_categories = ctx["income_categories"]

    # Clearing the field after a successful save (below) has to happen
    # *before* the keyed text_input widget is instantiated in a run, not
    # after — Streamlit raises StreamlitAPIException if session_state for a
    # widget's key is written to later in the same run it was instantiated
    # in, even right before a rerun(). Routing the clear through this flag,
    # checked here at the top before the widget exists yet, avoids that.
    if st.session_state.get("_clear_quick_add"):
        st.session_state["smart_note"] = ""
        st.session_state["_clear_quick_add"] = False

    section(l("Quick Add", "Швидке додавання", "Schnell hinzufügen"), l("Paste a short sentence, preview the parsed entry, then save it.", "Встав коротке речення, переглянь розбір і збережи.", "Füge einen kurzen Satz ein, prüfe die Erkennung und speichere dann."))
    quick_text = st.text_input(
        l("Quick entry", "Швидкий запис", "Schnelleingabe"),
        key="smart_note",
        placeholder="Examples: 2026-03-17 8.5 EUR coffee at Starbucks | 17.03 24.90 groceries | 12 usd uber",
    )
    preview = parse_quick_add(quick_text, history_df=history_df)
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
        category_options = income_categories if preview["tx_type"] == "income" else expense_categories
        default_index = category_options.index(preview["category"]) if preview["category"] in category_options else len(category_options)-1
        manual_category = st.selectbox(l("Adjust category", "Змінити категорію", "Kategorie anpassen"), category_options, index=default_index, format_func=lcat)
        note = st.text_input(l("Note / merchant", "Нотатка / продавець", "Notiz / Händler"), value=str(preview["note"]))
        subscription = st.checkbox(l("Recurring subscription", "Повторювана підписка", "Wiederkehrendes Abo"), value=bool(preview["subscription"]), disabled=preview["tx_type"] == "income")
        recurrence = "monthly"
        if subscription:
            recurrence = st.selectbox(l("Repeats", "Повторюється", "Wiederholung"), RECURRENCE_OPTIONS, index=RECURRENCE_OPTIONS.index("monthly"), format_func=lrec)
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
                recurrence,
            )
            st.success(l("Quick entry saved.", "Швидкий запис збережено.", "Schnelleingabe gespeichert."))
            st.session_state["_clear_quick_add"] = True
            rerun()
    elif quick_text:
        st.warning(preview["error"])
    end_section()

    section(l("Why this helps", "Чому це корисно", "Warum das hilft"), l("Useful for mobile, quick logging, and chat-style input.", "Зручно для телефону, швидкого внесення і вводу як у чаті.", "Nützlich für Handy, schnelle Erfassung und chatartigen Input."))
    st.write(l("The parser detects date, amount, currency, subscription hints, and suggests a category from the note.", "Парсер визначає дату, суму, валюту, ознаки підписки та пропонує категорію з нотатки.", "Der Parser erkennt Datum, Betrag, Währung, Abo-Hinweise und schlägt anhand der Notiz eine Kategorie vor."))
    end_section()
