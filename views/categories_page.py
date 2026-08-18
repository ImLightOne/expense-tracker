from __future__ import annotations

import streamlit as st

from common import end_section, l, lcat, rerun, section, show_empty
from config import DEFAULT_CATEGORIES, INCOME_CATEGORIES
from db import add_custom_category, delete_custom_category, get_custom_categories

_ADD_ERROR_MESSAGES = {
    "empty": lambda: l("Category name cannot be empty.", "Назва категорії не може бути порожньою.", "Der Kategoriename darf nicht leer sein."),
    "duplicate_default": lambda: l("This is already a built-in category.", "Така вбудована категорія вже існує.", "Diese Kategorie ist bereits eine eingebaute Kategorie."),
    "duplicate": lambda: l("You already have a category with this name.", "У тебе вже є категорія з такою назвою.", "Du hast bereits eine Kategorie mit diesem Namen."),
    "error": lambda: l("Could not add the category. Please try again.", "Не вдалося додати категорію. Спробуй ще раз.", "Kategorie konnte nicht hinzugefügt werden. Bitte versuche es erneut."),
}


def _render_type_section(user_id: str, tx_type: str, defaults: list) -> None:
    custom = get_custom_categories(user_id, tx_type)

    st.markdown(f"**{l('Built-in categories', 'Вбудовані категорії', 'Eingebaute Kategorien')}**")
    st.caption(", ".join(lcat(c) for c in defaults))

    st.markdown(f"**{l('Your categories', 'Твої категорії', 'Deine Kategorien')}**")
    if not custom:
        show_empty(l("No custom categories yet.", "Користувацьких категорій ще немає.", "Noch keine eigenen Kategorien."))
    else:
        for name in custom:
            row_left, row_right = st.columns([4, 1])
            row_left.write(name)
            if row_right.button(l("Delete", "Видалити", "Löschen"), key=f"del_{tx_type}_{name}", use_container_width=True):
                delete_custom_category(user_id, name, tx_type)
                st.success(l("Category deleted.", "Категорію видалено.", "Kategorie gelöscht."))
                rerun()

    new_name = st.text_input(l("New category name", "Назва нової категорії", "Neuer Kategoriename"), key=f"new_cat_{tx_type}")
    if st.button(l("Add category", "Додати категорію", "Kategorie hinzufügen"), key=f"add_cat_{tx_type}", use_container_width=True):
        ok, reason = add_custom_category(user_id, new_name, tx_type)
        if ok:
            st.success(l("Category added.", "Категорію додано.", "Kategorie hinzugefügt."))
            rerun()
        else:
            st.error(_ADD_ERROR_MESSAGES.get(reason, _ADD_ERROR_MESSAGES["error"])())


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]

    section(
        l("Expense categories", "Категорії витрат", "Ausgabenkategorien"),
        l(
            "Add your own categories on top of the built-in list. Deleting a custom category does not change transactions already recorded with it.",
            "Додавай власні категорії поверх вбудованого списку. Видалення категорії не змінює вже внесені транзакції з нею.",
            "Füge eigene Kategorien zur eingebauten Liste hinzu. Das Löschen einer Kategorie ändert bereits erfasste Transaktionen damit nicht.",
        ),
    )
    _render_type_section(user_id, "expense", DEFAULT_CATEGORIES)
    end_section()

    section(l("Income categories", "Категорії доходів", "Einnahmenkategorien"))
    _render_type_section(user_id, "income", INCOME_CATEGORIES)
    end_section()
