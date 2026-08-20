from __future__ import annotations

import pandas as pd
import streamlit as st

from common import end_section, gradient_bar_chart, l, lrec, section, show_empty
from utils import format_money, monthly_equivalent, safe_float


def render(ctx: dict) -> None:
    display_currency = ctx["display_currency"]
    filtered_df = ctx["filtered_df"]

    section(l("Recurring subscriptions", "Повторювані підписки", "Wiederkehrende Abos"), l("Grouped view, annual cost estimate, and concentration risk.", "Групування, оцінка річної вартості та ризик концентрації.", "Gruppierte Ansicht, jährliche Kostenschätzung und Konzentrationsrisiko."))
    subs = filtered_df[filtered_df["subscription"] == 1].copy()
    if subs.empty:
        show_empty(l("No subscriptions in the selected range.", "У вибраному діапазоні немає підписок.", "Keine Abos im ausgewählten Bereich."))
        if "pages" in ctx:
            st.page_link(ctx["pages"]["add_expense"], label=l("Add a recurring expense", "Додати повторювану витрату", "Wiederkehrende Ausgabe hinzufügen"), icon=":material/add_circle:")
    else:
        subs["recurrence"] = subs["recurrence"].fillna("monthly")
        # Normalize every subscription to a monthly-equivalent amount before
        # aggregating, so totals stay meaningful now that a subscription can
        # be weekly, monthly, or yearly rather than always monthly.
        subs["monthly_equivalent"] = subs.apply(
            lambda r: monthly_equivalent(r["display_amount"], r["recurrence"]), axis=1
        )
        grouped = subs.groupby(["category", "merchant", "currency", "recurrence"], as_index=False).agg(
            amount_per_charge=("display_amount", "mean"),
            monthly_display=("monthly_equivalent", "mean"),
            transactions=("id", "count"),
            last_seen=("date", "max"),
        ).sort_values("monthly_display", ascending=False)
        total_monthly = safe_float(grouped["monthly_display"].sum())
        annualized = total_monthly * 12
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(l("Estimated monthly total", "Орієнтовна сума за місяць", "Geschätzte Monatssumme"), format_money(total_monthly, display_currency))
        with c2:
            st.metric(l("Estimated annual total", "Орієнтовна сума за рік", "Geschätzte Jahressumme"), format_money(annualized, display_currency))
        with c3:
            top_share = grouped.iloc[0]["monthly_display"] / total_monthly * 100 if total_monthly else 0
            st.metric(l("Largest subscription share", "Найбільша частка підписки", "Größter Abo-Anteil"), f"{top_share:.1f}%")
        grouped_view = grouped.copy()
        grouped_view["last_seen"] = pd.to_datetime(grouped_view["last_seen"]).dt.date
        grouped_view["recurrence"] = grouped_view["recurrence"].map(lrec)
        st.dataframe(grouped_view, use_container_width=True, hide_index=True)
        st.caption(l(
            "\"Monthly-equivalent\" normalizes weekly/yearly amounts to a monthly figure for comparison — it isn't a literal monthly charge.",
            "\"Місячний еквівалент\" перераховує тижневі/річні суми на місячну для порівняння — це не буквальне щомісячне списання.",
            "\"Monatsäquivalent\" rechnet wöchentliche/jährliche Beträge zu einem Monatswert um, um sie vergleichbar zu machen — es ist keine tatsächliche monatliche Abbuchung.",
        ))
        gradient_bar_chart(
            grouped, "merchant", "monthly_display",
            y_title=display_currency, sort=list(grouped["merchant"]),
        )
    end_section()
