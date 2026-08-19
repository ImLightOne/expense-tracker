from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from analytics import calculate_financial_health, category_summary, check_category_budgets, month_forecast, savings_progress, streak_metrics
from common import end_section, generate_smart_insights, get_rates_map, l, lcat, metric_card, plot_pie, rerun, section, show_empty, t
from config import CATEGORY_COLORS
from db import convert_from_eur, convert_to_eur, get_category_budgets, get_monthly_limit, set_category_budget, set_monthly_limit
from utils import format_money, month_key, safe_float


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    display_currency = ctx["display_currency"]
    base_display_df = ctx["base_display_df"]
    filtered_df = ctx["filtered_df"]
    expense_df = ctx["expense_df"]
    income_df = ctx["income_df"]
    savings_df = ctx["savings_df"]
    expense_categories = ctx["expense_categories"]

    total_spent = safe_float(expense_df["display_abs_amount"].sum())
    total_income = safe_float(income_df["display_abs_amount"].sum())
    net_balance = total_income - total_spent
    avg_tx = safe_float(expense_df["display_abs_amount"].mean())
    tx_count = int(len(filtered_df))
    active_days = int(filtered_df["date_only"].nunique()) if not filtered_df.empty else 0
    avg_day = total_spent / active_days if active_days else 0.0
    current_month_limit_eur = get_monthly_limit(user_id)
    current_month_key = month_key(date.today())
    current_month_df = base_display_df[(base_display_df["month"] == current_month_key) & (base_display_df["type"] == "expense")].copy()
    this_month_spent = safe_float(current_month_df["display_abs_amount"].sum())
    current_month_limit_display = convert_from_eur(current_month_limit_eur, display_currency) if current_month_limit_eur is not None else None
    budget_left = max(safe_float(current_month_limit_display) - this_month_spent, 0.0) if current_month_limit_display is not None else None
    forecast_value = month_forecast(base_display_df)
    no_spend_streak, best_no_spend_streak = streak_metrics(base_display_df)
    health_score, health_label, health_breakdown = calculate_financial_health(expense_df, savings_df, current_month_limit_display)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(l("Total spent", "Усього витрачено", "Gesamtausgaben"), format_money(total_spent, display_currency), f"{tx_count} transactions")
    with c2:
        metric_card(l("Total income", "Усього доходів", "Gesamteinnahmen"), format_money(total_income, display_currency), f"{l('Net', 'Баланс', 'Netto')}: {format_money(net_balance, display_currency)}")
    with c3:
        metric_card(l("Average expense", "Середня витрата", "Durchschnittliche Ausgabe"), format_money(avg_tx, display_currency), f"{l('Month forecast', 'Прогноз на місяць', 'Monatsprognose')}: {format_money(forecast_value, display_currency)}")
    with c4:
        if current_month_limit_display is not None:
            metric_card(l("Budget left", "Залишок бюджету", "Verbleibendes Budget"), format_money(budget_left, display_currency), f"Budget: {format_money(current_month_limit_display, display_currency)}")
        else:
            metric_card(l("Budget left", "Залишок бюджету", "Verbleibendes Budget"), l("Not set", "Не задано", "Nicht festgelegt"), l("Set a monthly budget below", "Задай місячний бюджет нижче", "Lege unten ein Monatsbudget fest"))

    m1, m2, m3, m4 = st.columns(4)
    top_cat = category_summary(expense_df, "display_abs_amount")
    top_cat_name = lcat(top_cat.iloc[0]["category"]) if not top_cat.empty else "—"
    biggest_tx = safe_float(expense_df["display_abs_amount"].max())
    savings_total = safe_float(savings_df["saved"].sum())
    savings_rate = (savings_total / (savings_total + total_spent) * 100) if (savings_total + total_spent) > 0 else 0.0
    with m1:
        st.metric(t("top_category"), top_cat_name)
    with m2:
        st.metric(t("largest_expense"), format_money(biggest_tx, display_currency))
    with m3:
        st.metric(t("savings_rate"), f"{savings_rate:.1f}%")
    with m4:
        hb = health_breakdown if isinstance(health_breakdown, dict) else {}
        st.metric(t("health_score"), f"{health_score}/100", help=f"{health_label} · {t('budget')} {hb.get('budget', '—')}, {t('saving')} {hb.get('saving', '—')}, {t('consistency')} {hb.get('consistency', '—')}")

    left, right = st.columns([1.4, 1])
    with left:
        section(l("Category overview", "Огляд категорій", "Kategorieübersicht"), l("Biggest spending buckets for the current filter set.", "Найбільші категорії витрат для поточного фільтра.", "Größte Ausgabenkategorien für den aktuellen Filter."))
        cat_df = category_summary(expense_df, "display_abs_amount")
        if cat_df.empty:
            show_empty(l("Add a few transactions to unlock the dashboard.", "Додай кілька транзакцій, щоб активувати дашборд.", "Füge ein paar Transaktionen hinzu, um das Dashboard zu aktivieren."))
            if "pages" in ctx:
                st.page_link(ctx["pages"]["quick_add"], label=t("quick_add"), icon="⚡")
        else:
            cat_df_view = cat_df.copy()
            cat_df_view["category"] = cat_df_view["category"].map(lcat)
            st.bar_chart(cat_df_view.set_index("category"))
            share_df = cat_df.copy()
            share_df["share"] = (share_df["display_abs_amount"] / share_df["display_abs_amount"].sum() * 100).round(1)
            st.dataframe(share_df, use_container_width=True, hide_index=True)
        end_section()
    with right:
        section(l("Category split", "Розподіл категорій", "Kategorieverteilung"), l("Pie view for the same filtered range.", "Кругова діаграма для того ж фільтра.", "Kreisdiagramm für denselben Filter."))
        pie_df = category_summary(expense_df, "display_abs_amount").copy()
        pie_df["category"] = pie_df["category"].map(lcat)
        plot_pie(pie_df, "display_abs_amount")
        end_section()

    left2, right2 = st.columns([1.1, 1])
    with left2:
        section(l("Budget pacing", "Темп витрат бюджету", "Budgetverlauf"), l("Compares this month’s spending with month progress.", "Порівнює витрати цього місяця з прогресом місяця.", "Vergleicht die Ausgaben dieses Monats mit dem Monatsfortschritt."))
        limit_input = st.number_input(
            f"{l('Monthly budget', 'Місячний бюджет', 'Monatsbudget')} ({display_currency})",
            min_value=0.0,
            value=safe_float(current_month_limit_display),
            step=10.0,
        )
        if st.button(l("Save monthly budget", "Зберегти місячний бюджет", "Monatsbudget speichern"), use_container_width=True):
            set_monthly_limit(user_id, convert_to_eur(limit_input, display_currency))
            st.success(l("Budget saved.", "Бюджет збережено.", "Budget gespeichert."))
            rerun()

        st.markdown("---")
        st.subheader(l("Category budgets", "Бюджети по категоріях", "Kategorie-Budgets"))
        category_budgets = get_category_budgets(user_id)
        selected_budget_categories = st.multiselect(
            l("Choose categories for monthly limits", "Оберіть категорії для місячних лімітів", "Kategorien für Monatslimits auswählen"),
            options=expense_categories,
            default=[c for c in expense_categories if c in category_budgets],
            key="selected_budget_categories",
            format_func=lcat,
        )
        category_budget_inputs = {}
        for cat in selected_budget_categories:
            current_limit_display = get_rates_map("EUR").get(display_currency, 1.0)
            current_limit_display = category_budgets.get(cat, 0.0) * current_limit_display
            category_budget_inputs[cat] = st.number_input(
                f"{l('Monthly limit for', 'Місячний ліміт для', 'Monatslimit für')} {lcat(cat)} ({display_currency})",
                min_value=0.0,
                value=float(current_limit_display),
                step=10.0,
                key=f"cat_budget_{cat}",
            )
        if st.button(l("Save category budgets", "Зберегти бюджети категорій", "Kategorie-Budgets speichern"), use_container_width=True):
            for cat in selected_budget_categories:
                amount_display = category_budget_inputs[cat]
                amount_eur = convert_to_eur(amount_display, display_currency)
                set_category_budget(user_id, cat, amount_eur)
            st.success(l("Category budgets saved.", "Бюджети категорій збережено.", "Kategorie-Budgets gespeichert."))
            rerun()
        budget_status = check_category_budgets(expense_df, get_category_budgets(user_id), display_currency)
        if budget_status:
            st.markdown(f"**{l('Category budget usage', 'Використання бюджетів категорій', 'Nutzung der Kategorie-Budgets')}**")
            for row in budget_status:
                st.write(
                    f"**{lcat(row['category'])}** — {row['spent']:.2f} / {row['limit']:.2f} {display_currency} ({row['pct']:.1f}%)"
                )
                st.progress(min(row["pct"] / 100, 1.0))
                if row["over"]:
                    st.warning(l("This category is over budget.", "Ця категорія перевищила бюджет.", "Diese Kategorie liegt über dem Budget."))
        if current_month_limit_display:
            elapsed_pct = date.today().day / pd.Timestamp.today().days_in_month
            spent_pct = this_month_spent / current_month_limit_display if current_month_limit_display > 0 else 0
            pace_delta = spent_pct - elapsed_pct
            st.progress(min(max(spent_pct, 0.0), 1.0))
            st.write(f"{l('Spent', 'Витрачено', 'Ausgegeben')}: **{format_money(this_month_spent, display_currency)}**")
            st.write(f"{l('Month progress', 'Прогрес місяця', 'Monatsfortschritt')}: **{elapsed_pct * 100:.1f}%**")
            st.write(f"{l('Budget used', 'Використано бюджету', 'Budget genutzt')}: **{spent_pct * 100:.1f}%**")
            if pace_delta > 0.08:
                st.warning(l("You are spending faster than the month is passing.", "Ти витрачаєш швидше, ніж минає місяць.", "Du gibst schneller aus, als der Monat vergeht."))
            elif pace_delta < -0.08:
                st.success(l("You are ahead of budget pace.", "Ти випереджаєш план бюджету.", "Du liegst besser als dein Budgetplan."))
            else:
                st.info(l("You are roughly on pace.", "Ти приблизно в межах плану.", "Du liegst ungefähr im Plan."))
            days_left = pd.Timestamp.today().days_in_month - date.today().day
            suggested_daily = budget_left / max(days_left, 1)
            st.caption(f"{l('Suggested daily cap for the rest of the month', 'Рекомендований денний ліміт до кінця місяця', 'Empfohlenes Tageslimit für den Rest des Monats')}: {format_money(suggested_daily, display_currency)}")
        else:
            show_empty(l("Set a monthly budget to unlock budget pacing.", "Задай місячний бюджет, щоб активувати темп бюджету.", "Lege ein Monatsbudget fest, um den Budgetverlauf zu sehen."))
        end_section()
    with right2:
        section(l("Live FX widget", "Віджет курсу валют", "Live-Wechselkurse"), l("Reference rates used for display conversion.", "Довідкові курси для конвертації відображення.", "Referenzkurse für die Anzeigekonvertierung."))
        eur_rates = get_rates_map("EUR")
        usd_rates = get_rates_map("USD")
        fx_df = pd.DataFrame([
            {"Pair": "EUR / USD", "Rate": round(eur_rates.get("USD", 0.0), 4)},
            {"Pair": "EUR / UAH", "Rate": round(eur_rates.get("UAH", 0.0), 4)},
            {"Pair": "USD / UAH", "Rate": round(usd_rates.get("UAH", 0.0), 4)},
        ])
        st.dataframe(fx_df, use_container_width=True, hide_index=True)
        end_section()

    insight_box = generate_smart_insights(expense_df, income_df, savings_df, current_month_limit_display, display_currency)
    with st.expander(l("Smart insights", "Розумні інсайти", "Smarte Insights"), expanded=True):
        for item in insight_box:
            st.write(f"- {item}")

    low, high = st.columns(2)
    with low:
        section(l("Recent expenses", "Останні витрати", "Letzte Ausgaben"), l("Last 12 items in the filtered range.", "Останні 12 записів у вибраному фільтрі.", "Letzte 12 Einträge im aktuellen Filter."))
        recent = filtered_df.sort_values("date", ascending=False).head(12)
        if recent.empty:
            show_empty(l("No expenses in the selected range.", "У вибраному діапазоні немає витрат.", "Keine Ausgaben im ausgewählten Bereich."))
        else:
            for _, row in recent.iterrows():
                badge = f'<span class="badge" style="background:{CATEGORY_COLORS.get(row["category"], CATEGORY_COLORS["Other"])}">{lcat(row["category"])}</span>'
                sub_badge = f'<span class="badge" style="background:#3b82f6">{l("Subscription", "Підписка", "Abo")}</span>' if int(row["subscription"]) == 1 else ""
                st.markdown(
                    f'<div class="feed-row"><div>{badge} {sub_badge}<br><span class="small-muted">{row["date_only"]} · {row["note"] or row["merchant"]}</span></div>'
                    f'<div><strong>{format_money(row["display_amount"], display_currency)}</strong></div></div>',
                    unsafe_allow_html=True,
                )
        end_section()
    with high:
        section(l("Savings goals", "Цілі заощаджень", "Sparziele"), l("Quick progress summary.", "Короткий підсумок прогресу.", "Kurze Fortschrittsübersicht."))
        if savings_df.empty:
            show_empty(l("No savings goals yet.", "Цілей заощаджень ще немає.", "Noch keine Sparziele vorhanden."))
            if "pages" in ctx:
                st.page_link(ctx["pages"]["savings"], label=t("savings"), icon="💰")
        else:
            for _, row in savings_df.iterrows():
                progress = savings_progress(row["saved"], row["target"])
                st.write(f"**{row['name']}** — {format_money(row['saved'], 'EUR')} / {format_money(row['target'], 'EUR')}")
                st.progress(progress)
        end_section()
