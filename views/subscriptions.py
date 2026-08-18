from __future__ import annotations

import pandas as pd
import streamlit as st

from common import end_section, l, section, show_empty
from utils import format_money, safe_float


def render(ctx: dict) -> None:
    display_currency = ctx["display_currency"]
    filtered_df = ctx["filtered_df"]

    section(l("Recurring subscriptions", "Повторювані підписки", "Wiederkehrende Abos"), l("Grouped view, annual cost estimate, and concentration risk.", "Групування, оцінка річної вартості та ризик концентрації.", "Gruppierte Ansicht, jährliche Kostenschätzung und Konzentrationsrisiko."))
    subs = filtered_df[filtered_df["subscription"] == 1].copy()
    if subs.empty:
        show_empty(l("No subscriptions in the selected range.", "У вибраному діапазоні немає підписок.", "Keine Abos im ausgewählten Bereich."))
    else:
        grouped = subs.groupby(["category", "merchant", "currency"], as_index=False).agg(
            monthly_eur=("amount", "mean"),
            monthly_display=("display_amount", "mean"),
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
        grouped["last_seen"] = pd.to_datetime(grouped["last_seen"]).dt.date
        st.dataframe(grouped, use_container_width=True, hide_index=True)
        st.bar_chart(grouped.set_index("merchant")[["monthly_display"]])
    end_section()
