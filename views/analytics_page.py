from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import category_summary, detect_anomalies, merchant_summary, monthly_series, weekday_summary
from common import end_section, l, lcat, section, show_empty


def render(ctx: dict) -> None:
    expense_df = ctx["expense_df"]

    section(l("Advanced analytics", "Розширена аналітика", "Erweiterte Analysen"), l("Monthly trend, merchants, weekday patterns, anomalies, and Pareto view.", "Місячний тренд, продавці, патерни по днях, аномалії та Pareto-аналіз.", "Monatstrend, Händler, Wochentagsmuster, Anomalien und Pareto-Ansicht."))
    analytics_df = expense_df.copy()
    if analytics_df.empty:
        show_empty(l("No data for analytics in the current range.", "Немає даних для аналітики в цьому діапазоні.", "Keine Daten für Analysen im aktuellen Bereich."))
        end_section()
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**{l('Monthly trend', 'Місячний тренд', 'Monatstrend')}**")
            monthly = monthly_series(analytics_df, "display_abs_amount")
            if monthly.empty:
                show_empty(l("Not enough monthly data.", "Недостатньо місячних даних.", "Nicht genug Monatsdaten."))
            else:
                st.line_chart(monthly.set_index("month"))
        with c2:
            st.write(f"**{l('Weekday pattern', 'Патерн по днях тижня', 'Wochentagsmuster')}**")
            weekdays = weekday_summary(analytics_df, "display_abs_amount")
            st.bar_chart(weekdays.set_index("weekday"))
        end_section()

        left, right = st.columns(2)
        with left:
            section(l("Top merchants", "Топ продавців", "Top-Händler"), l("Based on the first meaningful words in the note.", "На основі перших змістовних слів у нотатці.", "Basierend auf den ersten sinnvollen Wörtern in der Notiz."))
            merchants = merchant_summary(analytics_df, "display_abs_amount")
            if merchants.empty:
                show_empty(l("No merchant-like notes found.", "Схожих на продавця нотаток не знайдено.", "Keine händlerähnlichen Notizen gefunden."))
            else:
                merchants_view = merchants.head(15).copy()
                merchants_view["category"] = merchants_view["category"].map(lcat) if "category" in merchants_view.columns else merchants_view.get("category")
                st.dataframe(merchants_view, use_container_width=True, hide_index=True)
            end_section()
        with right:
            section(l("Anomaly detector", "Пошук аномалій", "Anomalie-Erkennung"), l("Flags unusually high transactions within each category.", "Позначає незвично великі транзакції в межах кожної категорії.", "Markiert ungewöhnlich hohe Transaktionen innerhalb jeder Kategorie."))
            anomalies = detect_anomalies(analytics_df.assign(display_amount=analytics_df["display_abs_amount"]))
            if anomalies.empty:
                show_empty(l("No strong anomalies detected.", "Сильних аномалій не виявлено.", "Keine starken Anomalien erkannt."))
            else:
                anomalies_view = anomalies[["date_only", "category", "note", "display_amount", "currency"]].sort_values("display_amount", ascending=False).copy()
                anomalies_view["category"] = anomalies_view["category"].map(lcat)
                st.dataframe(
                    anomalies_view,
                    use_container_width=True,
                    hide_index=True,
                )
            end_section()

        section(l("Pareto view", "Pareto-аналіз", "Pareto-Ansicht"), l("Shows how much your top categories explain total spending.", "Показує, яку частку загальних витрат пояснюють топ-категорії.", "Zeigt, wie stark die Top-Kategorien die Gesamtausgaben erklären."))
        cat = category_summary(analytics_df, "display_abs_amount")
        if cat.empty:
            show_empty(l("No data.", "Немає даних.", "Keine Daten."))
        else:
            pareto = cat.copy()
            pareto["category"] = pareto["category"].map(lcat)
            pareto["cum_pct"] = (pareto["display_abs_amount"].cumsum() / pareto["display_abs_amount"].sum() * 100).round(1)
            st.dataframe(pareto, use_container_width=True, hide_index=True)
            hits_80 = pareto[pareto["cum_pct"] <= 80.0]
            st.caption(f"{len(hits_80) if not hits_80.empty else 1} " + l("category(ies) explain roughly 80% of the selected spending.", "категорій пояснюють приблизно 80% вибраних витрат.", "Kategorie(n) erklären ungefähr 80% der ausgewählten Ausgaben."))
        end_section()

        section(l("Spending calendar", "Календар витрат", "Ausgabenkalender"), l("Daily total view for the selected period.", "Щоденний підсумок за вибраний період.", "Tagesgesamtansicht für den ausgewählten Zeitraum."))
        cal = analytics_df.groupby("date_only", as_index=False)["display_abs_amount"].sum().sort_values("date_only")
        cal = cal.rename(columns={"display_abs_amount": "display_amount"})
        cal["weekday"] = pd.to_datetime(cal["date_only"]).dt.day_name()
        st.dataframe(cal, use_container_width=True, hide_index=True)
        end_section()
