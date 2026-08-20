from __future__ import annotations

import streamlit as st

from common import end_section, l, lcat, rerun, section, show_empty
from config import (
    CATEGORY_COLOR_TEMPLATE_NAMES,
    CATEGORY_COLOR_TEMPLATES,
    CATEGORY_COLORS,
    DEFAULT_CATEGORIES,
    INCOME_CATEGORIES,
)
from db import (
    add_custom_category,
    apply_category_color_template,
    delete_custom_category,
    get_category_colors,
    get_category_options,
    get_custom_categories,
    reset_category_color,
    set_category_color,
)

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
    if st.button(l("Add category", "Додати категорію", "Kategorie hinzufügen"), key=f"add_cat_{tx_type}", use_container_width=True, type="primary"):
        ok, reason = add_custom_category(user_id, new_name, tx_type)
        if ok:
            st.success(l("Category added.", "Категорію додано.", "Kategorie hinzugefügt."))
            rerun()
        else:
            st.error(_ADD_ERROR_MESSAGES.get(reason, _ADD_ERROR_MESSAGES["error"])())


def _render_color_section(user_id: str, tx_type: str) -> None:
    """One row per category (built-in + custom) with a color picker and a
    "Reset" button that only shows once that category actually has a saved
    override — comparing against a fresh, un-merged fetch of the user's
    overrides (not the ctx-level merged map dashboard/pie charts use) is
    what lets us tell "override happens to equal the default" apart from
    "no override at all".
    """
    st.markdown(f"**{l('Category colors', 'Кольори категорій', 'Kategoriefarben')}**")
    st.caption(l(
        "Used in the pie chart and the category badges on recent transactions.",
        "Використовуються в круговій діаграмі та бейджах категорій в останніх транзакціях.",
        "Werden im Kreisdiagramm und bei den Kategorie-Badges der letzten Transaktionen verwendet.",
    ))
    all_categories = get_category_options(user_id, tx_type)
    overrides = get_category_colors(user_id)
    for name in all_categories:
        default_color = CATEGORY_COLORS.get(name, CATEGORY_COLORS["Other"])
        is_overridden = name in overrides
        current_color = overrides.get(name, default_color)
        row_label, row_picker, row_reset = st.columns([3, 2, 1.4])
        row_label.write(lcat(name))
        picked = row_picker.color_picker(
            l("Color", "Колір", "Farbe"), value=current_color,
            key=f"color_{tx_type}_{name}", label_visibility="collapsed",
        )
        if picked.lower() != current_color.lower():
            set_category_color(user_id, name, tx_type, picked)
            rerun()
        if is_overridden:
            if row_reset.button(l("Reset", "Скинути", "Zurücksetzen"), key=f"reset_color_{tx_type}_{name}", use_container_width=True):
                reset_category_color(user_id, name, tx_type)
                st.success(l("Color reset to default.", "Колір скинуто до типового.", "Farbe zurückgesetzt."))
                rerun()


def _render_color_templates_section(user_id: str) -> None:
    """A row per pre-built palette template: swatch preview + one-click apply.

    Templates are sourced from real, published palettes (Tableau 20 /
    Material Design tonal families — see config.CATEGORY_COLOR_TEMPLATES) so
    the colors are pre-validated to work well together, instead of asking
    people to hand-pick 19 individual hues and hope they harmonize.
    """
    st.markdown(f"**{l('Palette templates', 'Шаблони кольорів', 'Farbvorlagen')}**")
    st.caption(l(
        "Ready-made color sets, picked to work well together. Applying one overwrites all your category colors below.",
        "Готові набори кольорів, підібрані так, щоб гармонійно поєднуватись. Застосування шаблону перезапише всі кольори категорій нижче.",
        "Fertige Farbsets, die gut zusammenpassen. Das Anwenden überschreibt alle deine Kategoriefarben unten.",
    ))
    expense_categories = get_category_options(user_id, "expense")
    income_categories = get_category_options(user_id, "income")
    for key, template in CATEGORY_COLOR_TEMPLATES.items():
        row_label, row_swatches, row_apply = st.columns([1.4, 3.6, 1.4])
        row_label.write(f"**{CATEGORY_COLOR_TEMPLATE_NAMES[key][st.session_state.get('lang', 'en')]}**")
        swatches = "".join(
            f'<span style="display:inline-block;width:16px;height:16px;border-radius:4px;'
            f'background:{color};margin-right:4px;" title="{name}"></span>'
            for name, color in list(template.items())[:12]
        )
        row_swatches.markdown(f'<div style="line-height:16px;padding-top:8px;">{swatches}</div>', unsafe_allow_html=True)
        if row_apply.button(l("Apply", "Застосувати", "Anwenden"), key=f"apply_template_{key}", use_container_width=True):
            apply_category_color_template(user_id, template, expense_categories, income_categories)
            st.success(l("Palette applied.", "Шаблон застосовано.", "Vorlage angewendet."))
            rerun()


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
    st.divider()
    _render_color_templates_section(user_id)
    st.divider()
    _render_color_section(user_id, "expense")
    end_section()

    section(l("Income categories", "Категорії доходів", "Einnahmenkategorien"))
    _render_type_section(user_id, "income", INCOME_CATEGORIES)
    st.divider()
    _render_color_section(user_id, "income")
    end_section()
