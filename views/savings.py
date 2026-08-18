from __future__ import annotations

import streamlit as st

from analytics import savings_progress
from common import end_section, l, rerun, section, show_empty
from db import add_savings_goal, delete_savings_goal, update_savings_progress
from utils import format_money, safe_float


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    savings_df = ctx["savings_df"]

    section(l("Savings goals", "Цілі заощаджень", "Sparziele"), l("Create goals, add progress, and keep track of totals.", "Створюй цілі, додавай прогрес і відстежуй підсумки.", "Erstelle Ziele, füge Fortschritt hinzu und behalte Summen im Blick."))
    c1, c2, c3 = st.columns(3)
    with c1:
        goal_name = st.text_input(l("Goal name", "Назва цілі", "Zielname"))
    with c2:
        goal_target = st.number_input(l("Target (€)", "Ціль (€)", "Ziel (€)"), min_value=0.0, step=10.0)
    with c3:
        goal_saved = st.number_input(l("Already saved (€)", "Вже відкладено (€)", "Bereits gespart (€)"), min_value=0.0, step=10.0)

    if st.button(l("Add goal", "Додати ціль", "Ziel hinzufügen"), use_container_width=True):
        if not goal_name.strip():
            st.error(l("Goal name cannot be empty.", "Назва цілі не може бути порожньою.", "Der Zielname darf nicht leer sein."))
        else:
            add_savings_goal(user_id, goal_name.strip(), goal_target, goal_saved)
            st.success(l("Savings goal added.", "Ціль заощаджень додано.", "Sparziel hinzugefügt."))
            rerun()

    if savings_df.empty:
        show_empty(l("No savings goals yet.", "Цілей заощаджень ще немає.", "Noch keine Sparziele vorhanden."))
    else:
        total_target = safe_float(savings_df["target"].sum())
        total_saved = safe_float(savings_df["saved"].sum())
        st.caption(f"{l('Combined progress', 'Загальний прогрес', 'Gesamtfortschritt')}: {format_money(total_saved, 'EUR')} / {format_money(total_target, 'EUR')}")
        for _, row in savings_df.iterrows():
            st.write(f"### {row['name']}")
            progress = savings_progress(row["saved"], row["target"])
            st.progress(progress)
            st.caption(f"{l('Saved', 'Відкладено', 'Gespart')}: {format_money(row['saved'], 'EUR')} / {l('Target', 'Ціль', 'Ziel')}: {format_money(row['target'], 'EUR')}")
            add_more = st.number_input(f"{l('Add money to', 'Додати гроші до', 'Geld hinzufügen zu')} {row['name']}", min_value=0.0, step=10.0, key=f"save_{row['id']}")
            x1, x2 = st.columns(2)
            if x1.button(f"{l('Update', 'Оновити', 'Aktualisieren')} {row['name']}", key=f"upd_{row['id']}", use_container_width=True):
                update_savings_progress(user_id, int(row["id"]), float(row["saved"]) + float(add_more))
                st.success(l("Savings updated.", "Заощадження оновлено.", "Sparziel aktualisiert."))
                rerun()
            if x2.button(f"{l('Delete', 'Видалити', 'Löschen')} {row['name']}", key=f"del_{row['id']}", use_container_width=True):
                delete_savings_goal(user_id, int(row["id"]))
                st.success(l("Goal deleted.", "Ціль видалено.", "Ziel gelöscht."))
                rerun()
            st.divider()
    end_section()
