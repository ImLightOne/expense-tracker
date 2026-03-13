
import io
from datetime import date
from calendar import monthrange
from supabase import create_client, Client
import bcrypt
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

from pathlib import Path
import shutil
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def init_db():
    # Supabase uses pre-created tables, so nothing to initialize here.
    return
DEFAULT_CATEGORIES = ["Food","Transport","Rent","Entertainment","Shopping","Health","Sports","Bills","Cafe","Education","Travel","Other"]
SUPPORTED_CURRENCIES = ["EUR","USD","UAH"]
CATEGORY_COLORS = {
    "Food":"#f97316","Transport":"#3b82f6","Rent":"#8b5cf6","Entertainment":"#ec4899",
    "Shopping":"#14b8a6","Health":"#ef4444","Sports":"#22c55e","Bills":"#f59e0b",
    "Cafe":"#d97706","Education":"#6366f1","Travel":"#06b6d4","Other":"#64748b",
}


LANGUAGE_OPTIONS = {"en": "English", "uk": "Українська", "de": "Deutsch"}
PAGE_KEYS = ["Dashboard", "Add Expense", "Manage Expenses", "Subscriptions", "Savings", "Analytics", "Export"]

TRANSLATIONS = {
    "en": {
        "language": "Language",
        "welcome": "Welcome",
        "choose_mode": "Choose mode",
        "login": "Login",
        "login_username": "Username",
        "login_password": "Password",
        "register": "Register",
        "create_account": "Create account",
        "invalid_username_password": "Invalid username or password.",
        "account_created_successfully": "Account created successfully.",
        "logged_in_as": "Logged in as {username}",
        "log_out": "Log out",
        "please_log_in_first": "Please log in first.",
        "professional_dashboard": "Professional personal finance dashboard",
        "app_title": "Expense Tracker Pro",
        "hero_subtitle": "Track spending, subscriptions, savings, and analytics in one place.",
        "expenses": "Expenses",
        "smart": "Smart",
        "track_daily_spending": "Track daily spending with categories",
        "savings": "Savings",
        "visible": "Visible",
        "watch_progress": "Watch progress toward your goals",
        "analytics": "Analytics",
        "clear": "Clear",
        "see_trends": "See trends, monthly totals, and export",
        "display_currency": "Display currency",
        "live_fx": "Live FX rates via ECB + NBU",
        "navigation": "Navigation",
        "welcome_back": "Welcome back, <b>{username}</b>. Metrics first, then trends, then details.",
        "added_recurring": "Added {count} recurring subscription(s) for this month.",
        "month_filter": "Month filter",
        "all_months": "All months",
        "selected_range": "Selected range",
        "total_spent": "Total spent",
        "this_month": "This month",
        "vs_last_month": "vs last month: {amount}",
        "average_expense": "Average expense",
        "transactions_count": "{count} transactions",
        "budget_left": "Budget left",
        "not_set": "Not set",
        "left_amount": "{amount} left",
        "no_budget_set": "No budget set",
        "transactions": "Transactions",
        "top_category": "Top category",
        "largest_expense": "Largest expense",
        "savings_rate": "Savings rate",
        "expenses_by_category": "Expenses by category",
        "biggest_spending_buckets": "Biggest spending buckets for the selected range.",
        "add_first_transaction_category_analytics": "Add your first transaction to see category analytics.",
        "amount_header": "Amount ({currency})",
        "category_split": "Category split",
        "pie_chart_consistent_colors": "Pie chart with consistent category colors.",
        "no_category_split": "No category split yet.",
        "monthly_budget": "Monthly budget",
        "use_current_month_budget": "Use the current month to track whether spending is on target.",
        "monthly_limit": "Monthly limit ({currency})",
        "save_monthly_limit": "Save monthly limit",
        "monthly_limit_saved": "Monthly limit saved.",
        "used_budget_pct": "Used {pct:.1f}% of monthly budget",
        "over_budget": "Over budget",
        "close_to_limit": "Close to limit",
        "on_track": "On track",
        "set_monthly_limit_unlock": "Set a monthly limit to unlock budget tracking.",
        "live_fx_widget": "Live FX widget",
        "reference_rates": "Reference rates for the selected display currency.",
        "savings_goals": "Savings goals",
        "progress_cards": "Progress cards with statuses and percentages.",
        "no_savings_goals": "No savings goals yet.",
        "recent_subscriptions": "Recent subscriptions",
        "recurring_payments_detected": "Recurring payments detected in your tracker.",
        "no_subscriptions_range": "No subscriptions in this range.",
        "recent_expenses": "Recent expenses",
        "styled_transaction_feed": "Styled transaction feed with category colors, notes, and badges.",
        "no_expenses_selected_range": "No expenses to show for the selected range.",
        "detailed_expense_form": "Detailed expense form",
        "record_transaction": "Record a transaction with category, currency, note, and optional recurring status.",
        "amount": "Amount",
        "currency": "Currency",
        "category": "Category",
        "date": "Date",
        "note_description": "Note / description",
        "recurring_monthly_subscription": "Recurring monthly subscription",
        "add_expense": "Add expense",
        "expense_added": "Expense added.",
        "manage_expenses": "Manage expenses",
        "filter_edit_delete": "Filter, edit, or delete your existing transactions.",
        "no_expenses_yet": "No expenses yet.",
        "filter_by_category": "Filter by category",
        "all": "All",
        "only_subscriptions": "Only subscriptions",
        "no_matching_expenses": "No matching expenses.",
        "select_expense": "Select expense",
        "amount_in_eur": "Amount in EUR",
        "recurring_subscription": "Recurring subscription",
        "original_currency_label": "Original currency label",
        "save_changes": "Save changes",
        "delete_expense": "Delete expense",
        "expense_updated": "Expense updated.",
        "expense_deleted": "Expense deleted.",
        "recurring_subscriptions": "Recurring subscriptions",
        "monthly_recurring_payments_detected": "Monthly recurring payments detected from your expenses.",
        "no_subscriptions_yet_range": "No subscriptions yet for this range.",
        "recurring": "Recurring",
        "estimated_subscriptions_range": "Estimated subscriptions in range: {amount}",
        "create_goals_track_progress": "Create goals, add money, and keep track of progress.",
        "goal_name": "Goal name",
        "target_eur": "Target (€)",
        "already_saved_eur": "Already saved (€)",
        "add_goal": "Add goal",
        "goal_name_empty": "Goal name cannot be empty.",
        "savings_goal_added": "Savings goal added.",
        "saved_target": "Saved: {saved} / Target: {target}",
        "add_money_to": "Add money to {name}",
        "update_name": "Update {name}",
        "delete_name": "Delete {name}",
        "savings_updated": "Savings updated.",
        "goal_deleted": "Goal deleted.",
        "analytics_subtitle": "KPI cards first, then charts, then comparisons and forecast.",
        "add_first_transaction_analytics": "Add your first transaction to unlock analytics.",
        "total_spending": "Total spending",
        "per_transaction": "Per transaction",
        "recorded_entries": "Recorded entries",
        "forecast": "Forecast",
        "current_month_estimate": "Current month estimate",
        "monthly_trend": "Monthly trend",
        "category_distribution": "Category distribution",
        "daily_spending_this_month": "Daily spending this month",
        "no_expenses_this_month": "No expenses this month.",
        "month_over_month_comparison": "Month-over-month comparison",
        "forecast_for_this_month": "Forecast for this month",
        "export_your_data": "Export your data",
        "download_filtered_or_full": "Download the current filtered view or the full dataset.",
        "nothing_to_export": "Nothing to export yet.",
        "filtered_export": "Filtered export",
        "download_filtered_csv": "Download filtered CSV",
        "download_filtered_excel": "Download filtered Excel",
        "full_export": "Full export",
        "download_full_csv": "Download full CSV",
        "download_full_excel": "Download full Excel",
        "completed": "Completed",
        "almost_there": "Almost there",
        "in_progress": "In progress",
        "started": "Started",
        "no_target": "No target",
        "progress": "Progress",
        "subscription": "Subscription",
        "no_items_to_show": "No items to show.",
        "not_enough_data_for_pie": "Not enough data for pie chart."
    },
    "uk": {
        "language": "Мова",
        "welcome": "Вітаю",
        "choose_mode": "Оберіть режим",
        "login": "Увійти",
        "login_username": "Ім’я користувача",
        "login_password": "Пароль",
        "register": "Реєстрація",
        "create_account": "Створити акаунт",
        "invalid_username_password": "Неправильне ім’я користувача або пароль.",
        "account_created_successfully": "Акаунт успішно створено.",
        "logged_in_as": "Увійшли як {username}",
        "log_out": "Вийти",
        "please_log_in_first": "Спочатку увійдіть у систему.",
        "professional_dashboard": "Професійна панель фінансів",
        "app_title": "Трекер витрат Pro",
        "hero_subtitle": "Відстежуй витрати, підписки, заощадження та аналітику в одному місці.",
        "expenses": "Витрати",
        "smart": "Розумно",
        "track_daily_spending": "Відстежуй щоденні витрати за категоріями",
        "savings": "Заощадження",
        "visible": "Наочно",
        "watch_progress": "Слідкуй за прогресом своїх цілей",
        "analytics": "Аналітика",
        "clear": "Чітко",
        "see_trends": "Дивись тренди, місячні підсумки й експорт",
        "display_currency": "Валюта відображення",
        "live_fx": "Живі курси ECB + НБУ",
        "navigation": "Навігація",
        "welcome_back": "З поверненням, <b>{username}</b>. Спочатку метрики, потім тренди і деталі.",
        "added_recurring": "Додано {count} регулярних підписок за цей місяць.",
        "month_filter": "Фільтр місяця",
        "all_months": "Усі місяці",
        "selected_range": "Обраний період",
        "total_spent": "Усього витрачено",
        "this_month": "Цього місяця",
        "vs_last_month": "до минулого місяця: {amount}",
        "average_expense": "Середня витрата",
        "transactions_count": "{count} транзакцій",
        "budget_left": "Залишок бюджету",
        "not_set": "Не задано",
        "left_amount": "залишилось {amount}",
        "no_budget_set": "Бюджет не задано",
        "transactions": "Транзакції",
        "top_category": "Топ категорія",
        "largest_expense": "Найбільша витрата",
        "savings_rate": "Рівень заощаджень",
        "expenses_by_category": "Витрати за категоріями",
        "biggest_spending_buckets": "Найбільші витратні категорії за вибраний період.",
        "add_first_transaction_category_analytics": "Додай першу транзакцію, щоб побачити аналітику категорій.",
        "amount_header": "Сума ({currency})",
        "category_split": "Розподіл категорій",
        "pie_chart_consistent_colors": "Кругова діаграма з однаковими кольорами категорій.",
        "no_category_split": "Ще немає розподілу по категоріях.",
        "monthly_budget": "Місячний бюджет",
        "use_current_month_budget": "Використовуй поточний місяць, щоб бачити, чи вкладаєшся в бюджет.",
        "monthly_limit": "Місячний ліміт ({currency})",
        "save_monthly_limit": "Зберегти місячний ліміт",
        "monthly_limit_saved": "Місячний ліміт збережено.",
        "used_budget_pct": "Використано {pct:.1f}% місячного бюджету",
        "over_budget": "Понад бюджет",
        "close_to_limit": "Близько до ліміту",
        "on_track": "У нормі",
        "set_monthly_limit_unlock": "Задай місячний ліміт, щоб увімкнути контроль бюджету.",
        "live_fx_widget": "Віджет курсів валют",
        "reference_rates": "Довідкові курси для вибраної валюти відображення.",
        "savings_goals": "Цілі заощаджень",
        "progress_cards": "Картки прогресу зі статусами і відсотками.",
        "no_savings_goals": "Цілей заощаджень ще немає.",
        "recent_subscriptions": "Останні підписки",
        "recurring_payments_detected": "Регулярні платежі, знайдені у твоєму трекері.",
        "no_subscriptions_range": "У цьому періоді немає підписок.",
        "recent_expenses": "Останні витрати",
        "styled_transaction_feed": "Стрічка транзакцій з кольорами категорій, нотатками та бейджами.",
        "no_expenses_selected_range": "Немає витрат для вибраного періоду.",
        "detailed_expense_form": "Детальна форма витрати",
        "record_transaction": "Запиши транзакцію з категорією, валютою, нотаткою та опціонально регулярністю.",
        "amount": "Сума",
        "currency": "Валюта",
        "category": "Категорія",
        "date": "Дата",
        "note_description": "Нотатка / опис",
        "recurring_monthly_subscription": "Щомісячна регулярна підписка",
        "add_expense": "Додати витрату",
        "expense_added": "Витрату додано.",
        "manage_expenses": "Керування витратами",
        "filter_edit_delete": "Фільтруй, редагуй або видаляй свої транзакції.",
        "no_expenses_yet": "Витрат ще немає.",
        "filter_by_category": "Фільтр за категорією",
        "all": "Усі",
        "only_subscriptions": "Лише підписки",
        "no_matching_expenses": "Немає відповідних витрат.",
        "select_expense": "Оберіть витрату",
        "amount_in_eur": "Сума в EUR",
        "recurring_subscription": "Регулярна підписка",
        "original_currency_label": "Початкова валюта",
        "save_changes": "Зберегти зміни",
        "delete_expense": "Видалити витрату",
        "expense_updated": "Витрату оновлено.",
        "expense_deleted": "Витрату видалено.",
        "recurring_subscriptions": "Регулярні підписки",
        "monthly_recurring_payments_detected": "Щомісячні регулярні платежі, знайдені у твоїх витратах.",
        "no_subscriptions_yet_range": "Для цього періоду ще немає підписок.",
        "recurring": "Регулярно",
        "estimated_subscriptions_range": "Оцінка підписок за період: {amount}",
        "create_goals_track_progress": "Створюй цілі, додавай гроші та відстежуй прогрес.",
        "goal_name": "Назва цілі",
        "target_eur": "Ціль (€)",
        "already_saved_eur": "Вже відкладено (€)",
        "add_goal": "Додати ціль",
        "goal_name_empty": "Назва цілі не може бути порожньою.",
        "savings_goal_added": "Ціль заощаджень додано.",
        "saved_target": "Накопичено: {saved} / Ціль: {target}",
        "add_money_to": "Додати гроші до {name}",
        "update_name": "Оновити {name}",
        "delete_name": "Видалити {name}",
        "savings_updated": "Заощадження оновлено.",
        "goal_deleted": "Ціль видалено.",
        "analytics_subtitle": "Спочатку KPI-картки, потім графіки, порівняння й прогноз.",
        "add_first_transaction_analytics": "Додай першу транзакцію, щоб увімкнути аналітику.",
        "total_spending": "Усього витрачено",
        "per_transaction": "На одну транзакцію",
        "recorded_entries": "Записаних позицій",
        "forecast": "Прогноз",
        "current_month_estimate": "Оцінка поточного місяця",
        "monthly_trend": "Місячний тренд",
        "category_distribution": "Розподіл категорій",
        "daily_spending_this_month": "Щоденні витрати цього місяця",
        "no_expenses_this_month": "Цього місяця витрат немає.",
        "month_over_month_comparison": "Порівняння місяць до місяця",
        "forecast_for_this_month": "Прогноз на цей місяць",
        "export_your_data": "Експорт даних",
        "download_filtered_or_full": "Завантаж поточний відфільтрований вигляд або повний набір даних.",
        "nothing_to_export": "Поки немає чого експортувати.",
        "filtered_export": "Експорт фільтра",
        "download_filtered_csv": "Завантажити filtered CSV",
        "download_filtered_excel": "Завантажити filtered Excel",
        "full_export": "Повний експорт",
        "download_full_csv": "Завантажити full CSV",
        "download_full_excel": "Завантажити full Excel",
        "completed": "Завершено",
        "almost_there": "Майже готово",
        "in_progress": "У процесі",
        "started": "Розпочато",
        "no_target": "Без цілі",
        "progress": "Прогрес",
        "subscription": "Підписка",
        "no_items_to_show": "Немає елементів для показу.",
        "not_enough_data_for_pie": "Недостатньо даних для кругової діаграми."
    },
    "de": {
        "language": "Sprache",
        "welcome": "Willkommen",
        "choose_mode": "Modus wählen",
        "login": "Anmelden",
        "login_username": "Benutzername",
        "login_password": "Passwort",
        "register": "Registrieren",
        "create_account": "Konto erstellen",
        "invalid_username_password": "Benutzername oder Passwort ist falsch.",
        "account_created_successfully": "Konto erfolgreich erstellt.",
        "logged_in_as": "Angemeldet als {username}",
        "log_out": "Abmelden",
        "please_log_in_first": "Bitte melde dich zuerst an.",
        "professional_dashboard": "Professionelles Finanz-Dashboard",
        "app_title": "Ausgaben-Tracker Pro",
        "hero_subtitle": "Behalte Ausgaben, Abos, Sparziele und Analysen an einem Ort im Blick.",
        "expenses": "Ausgaben",
        "smart": "Smart",
        "track_daily_spending": "Verfolge tägliche Ausgaben nach Kategorien",
        "savings": "Sparen",
        "visible": "Sichtbar",
        "watch_progress": "Beobachte den Fortschritt deiner Ziele",
        "analytics": "Analysen",
        "clear": "Klar",
        "see_trends": "Sieh Trends, Monatssummen und Export",
        "display_currency": "Anzeigewährung",
        "live_fx": "Live-Wechselkurse via EZB + NBU",
        "navigation": "Navigation",
        "welcome_back": "Willkommen zurück, <b>{username}</b>. Zuerst Kennzahlen, dann Trends und Details.",
        "added_recurring": "{count} wiederkehrende Abos für diesen Monat hinzugefügt.",
        "month_filter": "Monatsfilter",
        "all_months": "Alle Monate",
        "selected_range": "Ausgewählter Zeitraum",
        "total_spent": "Gesamtausgaben",
        "this_month": "Diesen Monat",
        "vs_last_month": "zum Vormonat: {amount}",
        "average_expense": "Durchschnittsausgabe",
        "transactions_count": "{count} Transaktionen",
        "budget_left": "Restbudget",
        "not_set": "Nicht gesetzt",
        "left_amount": "{amount} übrig",
        "no_budget_set": "Kein Budget gesetzt",
        "transactions": "Transaktionen",
        "top_category": "Top-Kategorie",
        "largest_expense": "Größte Ausgabe",
        "savings_rate": "Sparquote",
        "expenses_by_category": "Ausgaben nach Kategorien",
        "biggest_spending_buckets": "Größte Ausgabenkategorien im ausgewählten Zeitraum.",
        "add_first_transaction_category_analytics": "Füge deine erste Transaktion hinzu, um Kategorien-Analysen zu sehen.",
        "amount_header": "Betrag ({currency})",
        "category_split": "Kategorienverteilung",
        "pie_chart_consistent_colors": "Kreisdiagramm mit konsistenten Kategoriefarben.",
        "no_category_split": "Noch keine Kategorienverteilung vorhanden.",
        "monthly_budget": "Monatsbudget",
        "use_current_month_budget": "Nutze den aktuellen Monat, um zu sehen, ob du im Budget bleibst.",
        "monthly_limit": "Monatslimit ({currency})",
        "save_monthly_limit": "Monatslimit speichern",
        "monthly_limit_saved": "Monatslimit gespeichert.",
        "used_budget_pct": "{pct:.1f}% des Monatsbudgets verwendet",
        "over_budget": "Über Budget",
        "close_to_limit": "Nahe am Limit",
        "on_track": "Im Plan",
        "set_monthly_limit_unlock": "Setze ein Monatslimit, um Budget-Tracking zu aktivieren.",
        "live_fx_widget": "Live-FX-Widget",
        "reference_rates": "Referenzkurse für die ausgewählte Anzeigewährung.",
        "savings_goals": "Sparziele",
        "progress_cards": "Fortschrittskarten mit Status und Prozenten.",
        "no_savings_goals": "Noch keine Sparziele.",
        "recent_subscriptions": "Letzte Abos",
        "recurring_payments_detected": "Wiederkehrende Zahlungen aus deinem Tracker.",
        "no_subscriptions_range": "Keine Abos in diesem Zeitraum.",
        "recent_expenses": "Letzte Ausgaben",
        "styled_transaction_feed": "Transaktions-Feed mit Kategorienfarben, Notizen und Badges.",
        "no_expenses_selected_range": "Keine Ausgaben für den ausgewählten Zeitraum.",
        "detailed_expense_form": "Detailliertes Ausgabenformular",
        "record_transaction": "Erfasse eine Transaktion mit Kategorie, Währung, Notiz und optional wiederkehrendem Status.",
        "amount": "Betrag",
        "currency": "Währung",
        "category": "Kategorie",
        "date": "Datum",
        "note_description": "Notiz / Beschreibung",
        "recurring_monthly_subscription": "Monatlich wiederkehrendes Abo",
        "add_expense": "Ausgabe hinzufügen",
        "expense_added": "Ausgabe hinzugefügt.",
        "manage_expenses": "Ausgaben verwalten",
        "filter_edit_delete": "Filtern, bearbeiten oder lösche deine vorhandenen Transaktionen.",
        "no_expenses_yet": "Noch keine Ausgaben.",
        "filter_by_category": "Nach Kategorie filtern",
        "all": "Alle",
        "only_subscriptions": "Nur Abos",
        "no_matching_expenses": "Keine passenden Ausgaben.",
        "select_expense": "Ausgabe auswählen",
        "amount_in_eur": "Betrag in EUR",
        "recurring_subscription": "Wiederkehrendes Abo",
        "original_currency_label": "Ursprüngliche Währung",
        "save_changes": "Änderungen speichern",
        "delete_expense": "Ausgabe löschen",
        "expense_updated": "Ausgabe aktualisiert.",
        "expense_deleted": "Ausgabe gelöscht.",
        "recurring_subscriptions": "Wiederkehrende Abos",
        "monthly_recurring_payments_detected": "Monatlich wiederkehrende Zahlungen aus deinen Ausgaben.",
        "no_subscriptions_yet_range": "In diesem Zeitraum gibt es noch keine Abos.",
        "recurring": "Wiederkehrend",
        "estimated_subscriptions_range": "Geschätzte Abos im Zeitraum: {amount}",
        "create_goals_track_progress": "Erstelle Ziele, füge Geld hinzu und verfolge deinen Fortschritt.",
        "goal_name": "Zielname",
        "target_eur": "Ziel (€)",
        "already_saved_eur": "Bereits gespart (€)",
        "add_goal": "Ziel hinzufügen",
        "goal_name_empty": "Der Zielname darf nicht leer sein.",
        "savings_goal_added": "Sparziel hinzugefügt.",
        "saved_target": "Gespart: {saved} / Ziel: {target}",
        "add_money_to": "Geld zu {name} hinzufügen",
        "update_name": "{name} aktualisieren",
        "delete_name": "{name} löschen",
        "savings_updated": "Sparziel aktualisiert.",
        "goal_deleted": "Ziel gelöscht.",
        "analytics_subtitle": "Zuerst KPI-Karten, dann Diagramme, Vergleiche und Prognose.",
        "add_first_transaction_analytics": "Füge deine erste Transaktion hinzu, um Analysen freizuschalten.",
        "total_spending": "Gesamtausgaben",
        "per_transaction": "Pro Transaktion",
        "recorded_entries": "Erfasste Einträge",
        "forecast": "Prognose",
        "current_month_estimate": "Schätzung für den aktuellen Monat",
        "monthly_trend": "Monatstrend",
        "category_distribution": "Kategorienverteilung",
        "daily_spending_this_month": "Tägliche Ausgaben diesen Monat",
        "no_expenses_this_month": "Diesen Monat keine Ausgaben.",
        "month_over_month_comparison": "Monat-zu-Monat-Vergleich",
        "forecast_for_this_month": "Prognose für diesen Monat",
        "export_your_data": "Daten exportieren",
        "download_filtered_or_full": "Lade die gefilterte Ansicht oder den vollständigen Datensatz herunter.",
        "nothing_to_export": "Noch nichts zu exportieren.",
        "filtered_export": "Gefilterter Export",
        "download_filtered_csv": "Gefiltertes CSV herunterladen",
        "download_filtered_excel": "Gefiltertes Excel herunterladen",
        "full_export": "Vollständiger Export",
        "download_full_csv": "Vollständiges CSV herunterladen",
        "download_full_excel": "Vollständiges Excel herunterladen",
        "completed": "Abgeschlossen",
        "almost_there": "Fast geschafft",
        "in_progress": "In Arbeit",
        "started": "Gestartet",
        "no_target": "Kein Ziel",
        "progress": "Fortschritt",
        "subscription": "Abo",
        "no_items_to_show": "Keine Elemente zum Anzeigen.",
        "not_enough_data_for_pie": "Nicht genügend Daten für das Kreisdiagramm."
    }
}

CATEGORY_TRANSLATIONS = {
    "en": {c: c for c in DEFAULT_CATEGORIES},
    "uk": {
        "Food": "Їжа", "Transport": "Транспорт", "Rent": "Оренда", "Entertainment": "Розваги",
        "Shopping": "Покупки", "Health": "Здоров’я", "Sports": "Спорт", "Bills": "Рахунки",
        "Cafe": "Кафе", "Education": "Освіта", "Travel": "Подорожі", "Other": "Інше"
    },
    "de": {
        "Food": "Essen", "Transport": "Transport", "Rent": "Miete", "Entertainment": "Unterhaltung",
        "Shopping": "Shopping", "Health": "Gesundheit", "Sports": "Sport", "Bills": "Rechnungen",
        "Cafe": "Café", "Education": "Bildung", "Travel": "Reisen", "Other": "Sonstiges"
    },
}

PAGE_TRANSLATIONS = {
    "en": {p: p for p in PAGE_KEYS},
    "uk": {
        "Dashboard": "Дашборд",
        "Add Expense": "Додати витрату",
        "Manage Expenses": "Керування витратами",
        "Subscriptions": "Підписки",
        "Savings": "Заощадження",
        "Analytics": "Аналітика",
        "Export": "Експорт",
    },
    "de": {
        "Dashboard": "Dashboard",
        "Add Expense": "Ausgabe hinzufügen",
        "Manage Expenses": "Ausgaben verwalten",
        "Subscriptions": "Abos",
        "Savings": "Sparen",
        "Analytics": "Analysen",
        "Export": "Export",
    },
}

def t(key: str, **kwargs):
    lang = st.session_state.get("lang", "en")
    template = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return template.format(**kwargs)

def tr_category(cat: str) -> str:
    lang = st.session_state.get("lang", "en")
    return CATEGORY_TRANSLATIONS.get(lang, CATEGORY_TRANSLATIONS["en"]).get(cat, cat)

def tr_page(page_key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return PAGE_TRANSLATIONS.get(lang, PAGE_TRANSLATIONS["en"]).get(page_key, page_key)

def month_label(value: str) -> str:
    return t("all_months") if value == "All months" else value

st.set_page_config(page_title="Expense Tracker Pro", page_icon="💸", layout="wide")

st.markdown("""
<style>
/* ---------- LOGIN / REGISTER INPUT FIX ---------- */

section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background: #ffffff !important;
}

section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder {
    color: #666666 !important;
    -webkit-text-fill-color: #666666 !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="input"] > div {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
}

section[data-testid="stSidebar"] div[data-baseweb="input"] > div * {
    color: #111111 !important;
}

/* ---------- STREAMLIT THEME VARIABLES ----------
   var(--background-color)
   var(--secondary-background-color)
   var(--text-color)
   var(--primary-color)
------------------------------------------------- */

.block-container{
    padding-top:1rem;
    padding-bottom:2rem;
    max-width:1300px;
}

/* ---------- SIDEBAR ---------- */

[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#111827 0%,#0f172a 100%) !important;
}

[data-testid="stSidebar"],
[data-testid="stSidebar"] *{
    color:#ffffff !important;
}

/* ---------- MAIN TYPOGRAPHY ---------- */

.main-title{
    font-size:clamp(1.6rem,2vw,2.15rem);
    font-weight:800;
    margin-bottom:.2rem;
    line-height:1.15;
    color:var(--text-color) !important;
}

.main-subtitle{
    color:var(--text-color) !important;
    opacity:.8;
    margin-bottom:1rem;
    line-height:1.45;
}

/* ---------- PAGE SHELL ---------- */

.page-shell{
    background:var(--background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:24px;
    padding:1rem 1rem .4rem 1rem;
    box-shadow:0 10px 30px rgba(15,23,42,.08);
    color:var(--text-color) !important;
}

/* ---------- SECTION CARDS ---------- */

.section-card{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:18px;
    padding:1rem 1rem .9rem 1rem;
    margin-bottom:1rem;
    box-shadow:0 8px 24px rgba(15,23,42,.08);
    color:var(--text-color) !important;
}

.section-card *{
    color:var(--text-color);
}

.section-title{
    font-size:1.12rem;
    font-weight:700;
    margin-bottom:.1rem;
    color:var(--text-color) !important;
}

.section-subtitle{
    font-size:.93rem;
    margin-bottom:.9rem;
    color:var(--text-color) !important;
    opacity:.75;
}

/* ---------- KPI CARDS (INTENTIONALLY DARK) ---------- */

.metric-card{
    background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%) !important;
    border-radius:18px;
    padding:1rem;
    min-height:126px;
    box-shadow:0 10px 28px rgba(15,23,42,.18);
    color:#ffffff !important;
}

.metric-card *{
    color:#ffffff !important;
}

.metric-label{
    font-size:.95rem;
    margin-bottom:.35rem;
    color:rgba(255,255,255,.78) !important;
}

.metric-value{
    font-size:1.75rem;
    font-weight:800;
    line-height:1.08;
    color:#ffffff !important;
}

.metric-foot{
    margin-top:.45rem;
    font-size:.9rem;
    color:rgba(255,255,255,.78) !important;
}

/* ---------- NATIVE ST.METRIC ---------- */

div[data-testid="stMetric"]{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:12px 14px;
    box-shadow:0 8px 22px rgba(15,23,42,.05);
}

div[data-testid="stMetric"],
div[data-testid="stMetric"] *{
    color:var(--text-color) !important;
}

/* ---------- SAVINGS ---------- */

.goal-card{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:.9rem;
    margin-bottom:.8rem;
    color:var(--text-color) !important;
}

.goal-card *{
    color:var(--text-color);
}

.goal-wrap{
    margin-bottom:.9rem;
}

.goal-head{
    display:flex;
    justify-content:space-between;
    gap:12px;
    align-items:center;
    margin-bottom:.35rem;
    flex-wrap:wrap;
}

.goal-name{
    font-weight:700;
    color:var(--text-color) !important;
}

.goal-nums{
    color:var(--text-color) !important;
    opacity:.8;
}

.goal-bar{
    width:100%;
    height:12px;
    background:rgba(148,163,184,.25) !important;
    border-radius:999px;
    overflow:hidden;
}

.goal-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#22c55e 0%,#06b6d4 100%) !important;
}

/* ---------- BADGES ---------- */

.badge{
    display:inline-block;
    padding:.25rem .6rem;
    border-radius:999px;
    font-size:.78rem;
    font-weight:700;
}

.badge-good{background:#22c55e !important;color:#ffffff !important;}
.badge-warn{background:#f59e0b !important;color:#ffffff !important;}
.badge-info{background:#3b82f6 !important;color:#ffffff !important;}
.badge-neutral{background:#64748b !important;color:#ffffff !important;}

/* ---------- CATEGORY BADGES ---------- */

.cat-badge{
    display:inline-block;
    padding:.24rem .62rem;
    border-radius:999px;
    font-size:.76rem;
    font-weight:700;
    color:#ffffff !important;
}

/* ---------- EXPENSE FEED ---------- */

.expense-row{
    display:flex;
    justify-content:space-between;
    gap:12px;
    align-items:center;
    padding:.72rem .78rem;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:14px;
    margin-bottom:.55rem;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
}

.expense-left,.expense-right{
    display:flex;
    align-items:center;
    gap:8px;
    flex-wrap:wrap;
}

.expense-row,
.expense-row *{
    color:var(--text-color);
}

.expense-note{
    font-size:.87rem;
    color:var(--text-color) !important;
    opacity:.75;
}

.expense-row .badge,
.expense-row .cat-badge{
    color:#ffffff !important;
}

/* ---------- FX WIDGET ---------- */

.fx-row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:.55rem .7rem;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:12px;
    margin-bottom:.5rem;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
}

.fx-row,
.fx-row *{
    color:var(--text-color) !important;
}

/* ---------- EMPTY STATES ---------- */

.empty-box{
    background:var(--secondary-background-color) !important;
    border:1px dashed rgba(128,128,128,.28) !important;
    border-radius:16px;
    padding:1rem;
    color:var(--text-color) !important;
}

.empty-box *{
    color:var(--text-color) !important;
}

/* ---------- FORECAST ---------- */

.forecast-box{
    background:var(--secondary-background-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
    border-radius:16px;
    padding:.95rem 1rem;
    margin-top:1rem;
    color:var(--text-color) !important;
}

.forecast-box *{
    color:var(--text-color) !important;
}

.forecast-label{
    font-size:.92rem;
    color:var(--text-color) !important;
    opacity:.8;
}

.forecast-value{
    font-size:1.7rem;
    font-weight:800;
    color:var(--text-color) !important;
}

.kpi-inline{
    color:var(--text-color) !important;
    opacity:.8;
}

/* ---------- TABLES / DATAFRAMES ---------- */

[data-testid="stDataFrame"]{
    background:var(--secondary-background-color) !important;
    border-radius:14px;
}

[data-testid="stDataFrame"] *{
    color:var(--text-color) !important;
}

/* ---------- INPUTS ---------- */

div.stButton > button{
    border-radius:12px;
    border:0;
    min-height:2.8rem;
    font-weight:700;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
.stDateInput > div > div{
    border-radius:12px;
    background:var(--secondary-background-color) !important;
    color:var(--text-color) !important;
    border:1px solid rgba(128,128,128,.18) !important;
}

input, textarea{
    color:var(--text-color) !important;
    -webkit-text-fill-color:var(--text-color) !important;
}

/* ---------- ALERTS ---------- */

div[data-testid="stAlertContent"],
div[data-testid="stAlertContent"] *{
    color:var(--text-color) !important;
}

</style>
""", unsafe_allow_html=True)

# Supabase uses pre-created tables. No local SQLite init needed.
init_db()


def hash_password(password): return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
def get_user(username: str):
    res = (
        supabase.table("users")
        .select("*")
        .eq("username", username.strip())
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None
def register_user(username: str, password: str):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must have at least 3 characters."
    if len(password) < 6:
        return False, "Password must have at least 6 characters."

    existing = (
        supabase.table("users")
        .select("id")
        .eq("username", username)
        .limit(1)
        .execute()
    )

    if existing.data:
        return False, "This username already exists."

    supabase.table("users").insert({
        "username": username,
        "password_hash": hash_password(password).decode("utf-8")
    }).execute()

    return True, t("account_created_successfully")
def require_login():
    user_id=st.session_state.get("user_id")
    if not user_id:
        st.info(t("please_log_in_first"))
        st.stop()
    return int(user_id)
def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
@st.cache_data(ttl=1800)
def get_rates_map(base="EUR"):
    base=base.upper()
    if base=="EUR": fallback={"EUR":1.0,"USD":1.08,"UAH":50.0}
    elif base=="USD": fallback={"USD":1.0,"EUR":0.93,"UAH":43.0}
    elif base=="UAH": fallback={"UAH":1.0,"EUR":0.02,"USD":0.023}
    else: fallback={base:1.0,"EUR":1.0,"USD":1.0,"UAH":1.0}
    result={base:1.0}
    try:
        resp=requests.get(f"https://api.frankfurter.app/latest?from={base}&to=EUR,USD",timeout=10)
        rates=resp.json().get("rates",{})
        if isinstance(rates,dict):
            if base=="EUR": result.update({"USD":float(rates.get("USD",fallback["USD"])),"EUR":1.0})
            elif base=="USD": result.update({"EUR":float(rates.get("EUR",fallback["EUR"])),"USD":1.0})
            else: result.update({"EUR":float(rates.get("EUR",fallback["EUR"])),"USD":float(rates.get("USD",fallback["USD"]))})
    except Exception:
        result.update({k:v for k,v in fallback.items() if k in ["EUR","USD"]})
    try:
        data=requests.get("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json",timeout=10).json()
        eur_uah=usd_uah=None
        for row in data:
            if row.get("cc")=="EUR": eur_uah=float(row["rate"])
            if row.get("cc")=="USD": usd_uah=float(row["rate"])
        if eur_uah and usd_uah:
            if base=="EUR": result["UAH"]=eur_uah
            elif base=="USD": result["UAH"]=usd_uah
            elif base=="UAH": result.update({"EUR":1/eur_uah,"USD":1/usd_uah,"UAH":1.0})
    except Exception:
        result["UAH"]=fallback["UAH"]
    for k,v in fallback.items(): result.setdefault(k,v)
    return result

def convert_to_eur(amount,currency):
    if currency=="EUR": return round(float(amount),2)
    return round(float(amount)*float(get_rates_map(currency).get("EUR",1.0)),2)

def convert_from_eur(amount_eur,out_currency):
    if out_currency=="EUR": return round(float(amount_eur),2)
    return round(float(amount_eur)*float(get_rates_map("EUR").get(out_currency,1.0)),2)

def format_money(value,currency="EUR"): return f"{value:,.2f} {currency}".replace(",", " ")

def load_expenses(user_id: int) -> pd.DataFrame:
    res = (
        supabase.table("expenses")
        .select("*")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .execute()
    )

    df = pd.DataFrame(res.data)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["subscription"] = pd.to_numeric(df["subscription"], errors="coerce").fillna(0).astype(int)
    df["note"] = df["note"].fillna("")
    df["currency"] = df["currency"].fillna("EUR")
    return df.sort_values(["date", "id"], ascending=[False, False])
def load_savings(user_id: int) -> pd.DataFrame:
    res = (
        supabase.table("savings")
        .select("*")
        .eq("user_id", user_id)
        .order("id", desc=True)
        .execute()
    )

    df = pd.DataFrame(res.data)

    if df.empty:
        return df

    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved"] = pd.to_numeric(df["saved"], errors="coerce").fillna(0.0)
    return df
def make_display_df(df, output_currency):
    if df.empty: return df
    out=df.copy()
    out["display_amount"]=out["amount"].apply(lambda x: convert_from_eur(x, output_currency))
    out["date_only"]=out["date"].dt.date
    out["month"]=out["date"].dt.to_period("M").astype(str)
    return out

def add_expense(user_id: int, expense_date: date, amount: float, category: str, currency: str, note: str = "", subscription: int = 0):
    amount_eur = convert_to_eur(amount, currency)

    supabase.table("expenses").insert({
        "user_id": user_id,
        "date": expense_date.isoformat(),
        "amount": amount_eur,
        "category": category,
        "currency": currency,
        "subscription": int(subscription),
        "note": note.strip(),
    }).execute()
def get_monthly_limit(user_id: int):
    res = (
        supabase.table("budgets")
        .select("monthly_limit")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return float(res.data[0]["monthly_limit"]) if res.data else None
def set_monthly_limit(user_id: int, amount_eur: float):
    existing = (
        supabase.table("budgets")
        .select("user_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    payload = {"user_id": user_id, "monthly_limit": float(amount_eur)}

    if existing.data:
        supabase.table("budgets").update(payload).eq("user_id", user_id).execute()
    else:
        supabase.table("budgets").insert(payload).execute()
def upsert_monthly_subscriptions(user_id: int) -> int:
    df = load_expenses(user_id)
    if df.empty:
        return 0

    today = date.today()
    month_start = date(today.year, today.month, 1).isoformat()
    current_month_key = today.strftime("%Y-%m")

    subs = df[df["subscription"] == 1].copy()
    if subs.empty:
        return 0

    created = 0

    for _, row in subs.iterrows():
        row_month_key = pd.to_datetime(row["date"]).strftime("%Y-%m")
        if row_month_key == current_month_key:
            continue

        existing = (
            supabase.table("expenses")
            .select("id")
            .eq("user_id", user_id)
            .eq("subscription", 1)
            .eq("category", str(row["category"]))
            .eq("note", str(row["note"]))
            .eq("amount", float(row["amount"]))
            .gte("date", f"{current_month_key}-01")
            .lt("date", f"{current_month_key}-32")
            .limit(1)
            .execute()
        )

        if not existing.data:
            supabase.table("expenses").insert({
                "user_id": user_id,
                "date": month_start,
                "amount": float(row["amount"]),
                "category": str(row["category"]),
                "currency": str(row["currency"] or "EUR"),
                "subscription": 1,
                "note": str(row["note"]),
            }).execute()
            created += 1

    return created
def section_start(title, subtitle=None):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle: st.markdown(f'<div class="section-subtitle">{subtitle}</div>', unsafe_allow_html=True)
def section_end(): st.markdown("</div>", unsafe_allow_html=True)
def metric_card(label, value, foot=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-foot">{foot}</div></div>', unsafe_allow_html=True)
def empty_state(text): st.markdown(f'<div class="empty-box">{text}</div>', unsafe_allow_html=True)
def category_badge(category): return f'<span class="cat-badge" style="background:{CATEGORY_COLORS.get(category,CATEGORY_COLORS["Other"])};">{tr_category(category)}</span>'
def savings_bar(saved,target):
    progress=0.0 if target<=0 else max(0.0,min(saved/target,1.0))
    pct=round(progress*100,1); width=max(progress*100,4 if progress>0 else 0)
    st.markdown(f'<div class="goal-wrap"><div class="goal-head"><div class="goal-name">{t("progress")}</div><div class="goal-nums">{pct}%</div></div><div class="goal-bar"><div class="goal-fill" style="width:{width}%;"></div></div></div>', unsafe_allow_html=True)
def savings_status(saved,target):
    if target<=0: return f'<span class="badge badge-neutral">{t("no_target")}</span>'
    ratio=saved/target
    if ratio>=1: return f'<span class="badge badge-good">{t("completed")}</span>'
    if ratio>=0.8: return f'<span class="badge badge-info">{t("almost_there")}</span>'
    if ratio>0: return f'<span class="badge badge-neutral">{t("in_progress")}</span>'
    return f'<span class="badge badge-warn">{t("started")}</span>'
def category_pie_chart(cat_df,value_col,label_col):
    if cat_df.empty: return empty_state(t("not_enough_data_for_pie"))
    colors=[CATEGORY_COLORS.get(cat,CATEGORY_COLORS["Other"]) for cat in cat_df[label_col]]
    fig,ax=plt.subplots(figsize=(6,6))
    ax.pie(cat_df[value_col],labels=[tr_category(v) for v in cat_df[label_col]],autopct="%1.1f%%",startangle=90,colors=colors,wedgeprops={"linewidth":1,"edgecolor":"white"},textprops={"fontsize":9})
    ax.axis("equal"); st.pyplot(fig); plt.close(fig)
def render_expense_cards(cards_df, display_currency, show_subscription=True):
    if cards_df.empty: return empty_state(t("no_items_to_show"))
    for _,row in cards_df.iterrows():
        parts=[category_badge(str(row["category"])),f'<span>{row["date_only"]}</span>']
        if show_subscription and int(row.get("subscription",0))==1: parts.append('<span class="badge badge-info">Subscription</span>')
        note=str(row.get("note","") or "")
        if note: parts.append(f'<span class="expense-note">{note}</span>')
        st.markdown(f'<div class="expense-row"><div class="expense-left">{"".join(parts)}</div><div class="expense-right"><strong>{format_money(float(row["display_amount"]), display_currency)}</strong></div></div>', unsafe_allow_html=True)
def recent_month_options(display_df):
    if display_df.empty or "month" not in display_df.columns: return ["All months"]
    return ["All months"] + sorted(display_df["month"].dropna().unique().tolist(), reverse=True)
def filter_by_month(df, month_value):
    if df.empty or month_value=="All months": return df.copy()
    return df[df["month"]==month_value].copy()

if "user_id" not in st.session_state: st.session_state.user_id=None
if "username" not in st.session_state: st.session_state.username=None
if "lang" not in st.session_state: st.session_state.lang="en"

st.sidebar.selectbox(t("language"), list(LANGUAGE_OPTIONS.keys()), format_func=lambda k: LANGUAGE_OPTIONS[k], key="lang")
st.sidebar.markdown(f"## 💸 {t('app_title')}")
st.sidebar.caption(t("professional_dashboard"))
if st.session_state.user_id:
    st.sidebar.success(t("logged_in_as", username=st.session_state.username))
    if st.sidebar.button(t("log_out"), use_container_width=True):
        st.session_state.user_id=None; st.session_state.username=None; rerun()
else:
    st.sidebar.markdown(f"### {t('welcome')}")
    mode=st.sidebar.radio(t("choose_mode"), [t("login"), t("register")])
    username=st.sidebar.text_input(t("login_username"))
    password=st.sidebar.text_input(t("login_password"), type="password")
    if mode==t("login"):
        if st.sidebar.button(t("login"), use_container_width=True):
            user=get_user(username)
            if user and check_password(password,user["password_hash"]):
                st.session_state.user_id=int(user["id"]); st.session_state.username=user["username"]; rerun()
            else: st.sidebar.error(t("invalid_username_password"))
    else:
        if st.sidebar.button(t("create_account"), use_container_width=True):
            ok,message=register_user(username,password)
            if ok: st.sidebar.success(message)
            else: st.sidebar.error(message)

if not st.session_state.user_id:
    st.markdown('<div class="page-shell">', unsafe_allow_html=True)
    st.markdown(f'<div class="main-title">💸 {t("app_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="main-subtitle">{t("hero_subtitle")}</div>', unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a: metric_card(t("expenses"),t("smart"),t("track_daily_spending"))
    with b: metric_card(t("savings"),t("visible"),t("watch_progress"))
    with c: metric_card(t("analytics"),t("clear"),t("see_trends"))
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

user_id=require_login()
created_subs=upsert_monthly_subscriptions(user_id)
if created_subs: st.toast(t("added_recurring", count=created_subs))

st.sidebar.divider()
display_currency=st.sidebar.selectbox(t("display_currency"), SUPPORTED_CURRENCIES, index=0)
st.sidebar.caption(t("live_fx"))
page=st.sidebar.radio(t("navigation"), PAGE_KEYS, format_func=tr_page)

st.markdown('<div class="page-shell">', unsafe_allow_html=True)
st.markdown(f'<div class="main-title">💸 {t("app_title")}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="main-subtitle">{t("welcome_back", username=st.session_state.username)}</div>', unsafe_allow_html=True)

df=load_expenses(user_id)
display_df=make_display_df(df, display_currency)
savings_df=load_savings(user_id)
month_options=recent_month_options(display_df)

if page=="Dashboard":
    dashboard_filter=st.selectbox(t("month_filter"), month_options, index=0, format_func=month_label)
    filtered_df=filter_by_month(display_df, dashboard_filter)
    today=pd.Timestamp.today(); this_month_key=today.strftime("%Y-%m")
    this_month_df=filter_by_month(display_df, this_month_key)
    total_spent=float(filtered_df["display_amount"].sum()) if not filtered_df.empty else 0.0
    month_spent=float(this_month_df["display_amount"].sum()) if not this_month_df.empty else 0.0
    avg_spent=float(filtered_df["display_amount"].mean()) if not filtered_df.empty else 0.0
    tx_count=int(len(filtered_df))
    current_limit_eur=get_monthly_limit(user_id)
    current_limit_display=convert_from_eur(current_limit_eur, display_currency) if current_limit_eur is not None else 0.0
    left_budget=max(current_limit_display-month_spent,0.0) if current_limit_eur is not None else 0.0
    prev_month_key=(today.replace(day=1)-pd.Timedelta(days=1)).strftime("%Y-%m")
    prev_month_df=filter_by_month(display_df, prev_month_key)
    prev_month_total=float(prev_month_df["display_amount"].sum()) if not prev_month_df.empty else 0.0
    delta_vs_last=month_spent-prev_month_total
    c1,c2,c3,c4=st.columns(4)
    with c1: metric_card(t("total_spent"), format_money(total_spent, display_currency), month_label(dashboard_filter) if dashboard_filter!="All months" else t("selected_range"))
    with c2: metric_card(t("this_month"), format_money(month_spent, display_currency), t("vs_last_month", amount=format_money(delta_vs_last, display_currency)))
    with c3: metric_card(t("average_expense"), format_money(avg_spent, display_currency), t("transactions_count", count=tx_count))
    with c4: metric_card(t("budget_left"), format_money(current_limit_display, display_currency) if current_limit_eur is not None else t("not_set"), t("left_amount", amount=format_money(left_budget, display_currency)) if current_limit_eur is not None else t("no_budget_set"))
    o1,o2,o3,o4=st.columns(4)
    highest_cat="—"
    if not filtered_df.empty:
        topcat=filtered_df.groupby("category")["display_amount"].sum().sort_values(ascending=False)
        if not topcat.empty: highest_cat=topcat.index[0]
    biggest_tx=float(filtered_df["display_amount"].max()) if not filtered_df.empty else 0.0
    savings_rate=(float(savings_df["saved"].sum())/(float(savings_df["saved"].sum())+total_spent))*100 if total_spent>0 and not savings_df.empty else 0.0
    with o1: st.metric(t("transactions"), tx_count)
    with o2: st.metric(t("top_category"), tr_category(highest_cat) if highest_cat!="—" else highest_cat)
    with o3: st.metric(t("largest_expense"), format_money(biggest_tx, display_currency))
    with o4: st.metric(t("savings_rate"), f"{savings_rate:.1f}%")
    left,right=st.columns([1.35,1])
    with left:
        section_start(t("expenses_by_category"), t("biggest_spending_buckets"))
        if filtered_df.empty: empty_state(t("add_first_transaction_category_analytics"))
        else:
            cat_df=filtered_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False)
            st.bar_chart(cat_df.set_index("category"))
            cat_show = cat_df.copy(); cat_show["category"] = cat_show["category"].map(tr_category); st.dataframe(cat_show.rename(columns={"category": t("category"), "display_amount": t("amount_header", currency=display_currency)}), use_container_width=True, hide_index=True)
        section_end()
    with right:
        section_start(t("category_split"), t("pie_chart_consistent_colors"))
        if filtered_df.empty: empty_state(t("no_category_split"))
        else:
            category_pie_chart(filtered_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False), "display_amount", "category")
        section_end()
    l2,r2=st.columns([1.05,1])
    with l2:
        section_start(t("monthly_budget"), t("use_current_month_budget"))
        new_limit_display=st.number_input(t("monthly_limit", currency=display_currency), min_value=0.0, value=float(current_limit_display), step=10.0)
        if st.button(t("save_monthly_limit"), use_container_width=True):
            set_monthly_limit(user_id, convert_to_eur(new_limit_display, display_currency))
            st.success(t("monthly_limit_saved"))
            rerun()
        if current_limit_eur is not None:
            limit_display=convert_from_eur(current_limit_eur, display_currency)
            progress=min(month_spent/limit_display,1.0) if limit_display>0 else 0.0
            st.progress(progress)
            pct=(month_spent/limit_display*100) if limit_display>0 else 0
            st.markdown(f'<div class="kpi-inline">{t("used_budget_pct", pct=pct)}</div>', unsafe_allow_html=True)
            if month_spent>limit_display: st.markdown(f'<span class="badge badge-warn">{t("over_budget")}</span>', unsafe_allow_html=True)
            elif pct>=85: st.markdown(f'<span class="badge badge-info">{t("close_to_limit")}</span>', unsafe_allow_html=True)
            else: st.markdown(f'<span class="badge badge-good">{t("on_track")}</span>', unsafe_allow_html=True)
        else: empty_state(t("set_monthly_limit_unlock"))
        section_end()
    with r2:
        section_start(t("live_fx_widget"), t("reference_rates"))
        eur_rates=get_rates_map("EUR"); usd_rates=get_rates_map("USD")
        for label,val in [("EUR / USD",eur_rates.get("USD",0)),("EUR / UAH",eur_rates.get("UAH",0)),("USD / UAH",usd_rates.get("UAH",0))]:
            st.markdown(f'<div class="fx-row"><span>{label}</span><strong>{val:.4f}</strong></div>', unsafe_allow_html=True)
        section_end()
    c5,c6=st.columns(2)
    with c5:
        section_start(t("savings_goals"), t("progress_cards"))
        if savings_df.empty: empty_state(t("no_savings_goals"))
        else:
            for _,row in savings_df.iterrows():
                st.markdown('<div class="goal-card">', unsafe_allow_html=True)
                st.markdown(f"**{row['name']}**")
                st.markdown(savings_status(float(row["saved"]), float(row["target"])), unsafe_allow_html=True)
                savings_bar(float(row["saved"]), float(row["target"]))
                st.caption(t("saved_target", saved=format_money(row["saved"], "EUR"), target=format_money(row["target"], "EUR")))
                st.markdown('</div>', unsafe_allow_html=True)
        section_end()
    with c6:
        section_start(t("recent_subscriptions"), t("recurring_payments_detected"))
        subs=filtered_df[filtered_df["subscription"]==1].copy() if not filtered_df.empty else pd.DataFrame()
        if subs.empty: empty_state(t("no_subscriptions_range"))
        else: render_expense_cards(subs[["date_only","category","display_amount","subscription","note"]].head(6), display_currency, True)
        section_end()
    section_start(t("recent_expenses"), t("styled_transaction_feed"))
    if filtered_df.empty: empty_state(t("no_expenses_selected_range"))
    else: render_expense_cards(filtered_df[["date_only","category","display_amount","subscription","note"]].head(12), display_currency, True)
    section_end()

elif page=="Add Expense":
    section_start(t("detailed_expense_form"), t("record_transaction"))
    c1,c2=st.columns(2)
    with c1:
        amount=st.number_input(t("amount"), min_value=0.01, step=0.5)
        currency=st.selectbox(t("currency"), SUPPORTED_CURRENCIES)
        category=st.selectbox(t("category"), DEFAULT_CATEGORIES, format_func=tr_category)
    with c2:
        expense_date=st.date_input(t("date"), value=date.today())
        note=st.text_input(t("note_description"))
        is_subscription=st.checkbox(t("recurring_monthly_subscription"))
    if st.button(t("add_expense"), use_container_width=True):
        add_expense(user_id, expense_date, amount, category, currency, note, 1 if is_subscription else 0)
        st.success(t("expense_added")); rerun()
    section_end()

elif page=="Manage Expenses":
    month_filter=st.selectbox(t("month_filter"), month_options, index=0, key="manage_month_filter", format_func=month_label)
    section_start(t("manage_expenses"), t("filter_edit_delete"))
    if df.empty: empty_state(t("no_expenses_yet"))
    else:
        c1,c2=st.columns(2)
        with c1:
            base_filtered=filter_by_month(make_display_df(df,"EUR"), month_filter)
            categories=sorted(base_filtered["category"].dropna().unique().tolist()) if not base_filtered.empty else []
            filter_category=st.selectbox(t("filter_by_category"), ["All"]+categories, format_func=lambda x: t("all") if x=="All" else tr_category(x))
        with c2: show_subs_only=st.checkbox(t("only_subscriptions"))
        filtered=filter_by_month(df.copy().assign(month=df["date"].dt.to_period("M").astype(str)), month_filter)
        if filter_category!="All": filtered=filtered[filtered["category"]==filter_category]
        if show_subs_only: filtered=filtered[filtered["subscription"]==1]
        if filtered.empty: empty_state(t("no_matching_expenses"))
        else:
            filtered=filtered.copy()
            filtered["label"]=filtered["date"].dt.strftime("%Y-%m-%d")+" | "+filtered["category"].astype(str)+" | "+filtered["amount"].round(2).astype(str)+" EUR | "+filtered["note"].fillna("")
            expense=filtered.loc[filtered["label"]==st.selectbox(t("select_expense"), filtered["label"].tolist())].iloc[0]
            c3,c4=st.columns(2)
            with c3:
                edit_amount_eur=st.number_input(t("amount_in_eur"), min_value=0.0, value=float(expense["amount"]), step=0.5)
                current_category=expense["category"] if expense["category"] in DEFAULT_CATEGORIES else "Other"
                edit_category=st.selectbox(t("category"), DEFAULT_CATEGORIES, index=DEFAULT_CATEGORIES.index(current_category), format_func=tr_category)
                edit_subscription=st.checkbox(t("recurring_subscription"), value=bool(expense["subscription"]))
            with c4:
                edit_date=st.date_input(t("date"), value=pd.to_datetime(expense["date"]).date())
                edit_note=st.text_input(t("note_description"), value=str(expense["note"] or ""))
                current_currency=expense["currency"] if expense["currency"] in SUPPORTED_CURRENCIES else "EUR"
                edit_currency=st.selectbox(t("original_currency_label"), SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(current_currency))
            b1,b2=st.columns(2)
            if b1.button(t("save_changes"), use_container_width=True):
                supabase.table("expenses").update({
                    "amount": float(edit_amount_eur),
                    "category": edit_category,
                    "date": edit_date.isoformat(),
                    "note": edit_note.strip(),
                    "currency": edit_currency,
                    "subscription": 1 if edit_subscription else 0,
                }).eq("id", int(expense["id"])).eq("user_id", user_id).execute()
            
                st.success(t("expense_updated"))
                rerun()
            if b2.button(t("delete_expense"), use_container_width=True):
                supabase.table("expenses").delete().eq("id", int(expense["id"])).eq("user_id", user_id).execute()
            
                st.success(t("expense_deleted"))
                rerun()
    section_end()

elif page=="Subscriptions":
    month_filter=st.selectbox(t("month_filter"), month_options, index=0, key="subs_month_filter", format_func=month_label)
    section_start(t("recurring_subscriptions"), t("monthly_recurring_payments_detected"))
    subs=filter_by_month(display_df[display_df["subscription"]==1].copy(), month_filter) if not display_df.empty else pd.DataFrame()
    if subs.empty: empty_state(t("no_subscriptions_yet_range"))
    else:
        st.markdown(f'<span class="badge badge-info">{t("recurring")}</span>', unsafe_allow_html=True)
        st.caption(t("estimated_subscriptions_range", amount=format_money(float(subs["display_amount"].sum()), display_currency)))
        render_expense_cards(subs[["date_only","category","display_amount","subscription","note"]], display_currency, True)
    section_end()

elif page=="Savings":
    section_start(t("savings_goals"), t("create_goals_track_progress"))
    c1,c2,c3=st.columns(3)
    with c1: goal_name=st.text_input(t("goal_name"))
    with c2: goal_target=st.number_input(t("target_eur"), min_value=0.0, step=10.0)
    with c3: goal_saved=st.number_input(t("already_saved_eur"), min_value=0.0, step=10.0)
    if st.button(t("add_goal"), use_container_width=True):
        if not goal_name.strip():
            st.error(t("goal_name_empty"))
        else:
            supabase.table("savings").insert({
                "user_id": user_id,
                "name": goal_name.strip(),
                "target": float(goal_target),
                "saved": float(goal_saved),
            }).execute()

            st.success(t("savings_goal_added"))
            rerun()
    if savings_df.empty: empty_state(t("no_savings_goals"))
    else:
        for _,row in savings_df.iterrows():
            st.markdown('<div class="goal-card">', unsafe_allow_html=True)
            st.markdown(f"### {row['name']}")
            st.markdown(savings_status(float(row["saved"]), float(row["target"])), unsafe_allow_html=True)
            savings_bar(float(row["saved"]), float(row["target"]))
            st.caption(t("saved_target", saved=format_money(row["saved"], "EUR"), target=format_money(row["target"], "EUR")))
            add_more=st.number_input(t("add_money_to", name=row["name"]), min_value=0.0, step=10.0, key=f"add_goal_{row['id']}")
            x1,x2=st.columns(2)
            if x1.button(t("update_name", name=row["name"]), key=f"update_goal_{row['id']}", use_container_width=True):
                new_saved = float(row["saved"]) + float(add_more)
            
                supabase.table("savings").update({
                    "saved": new_saved
                }).eq("id", int(row["id"])).eq("user_id", user_id).execute()
            
                st.success(t("savings_updated"))
                rerun()
            if x2.button(t("delete_name", name=row["name"]), key=f"delete_goal_{row['id']}", use_container_width=True):
                supabase.table("savings").delete().eq("id", int(row["id"])).eq("user_id", user_id).execute()
            
                st.success(t("goal_deleted"))
                rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    section_end()

elif page=="Analytics":
    month_filter=st.selectbox(t("month_filter"), month_options, index=0, key="analytics_month_filter", format_func=month_label)
    analytics_df=filter_by_month(display_df, month_filter)
    section_start(t("analytics"), t("analytics_subtitle"))
    if analytics_df.empty: empty_state(t("add_first_transaction_analytics"))
    else:
        total=float(analytics_df["display_amount"].sum())
        avg=float(analytics_df["display_amount"].mean()) if len(analytics_df) else 0.0
        tx=int(len(analytics_df))
        today=pd.Timestamp.today()
        current_month_df=display_df[(display_df["date"].dt.year==today.year)&(display_df["date"].dt.month==today.month)].copy()
        current_month_total=float(current_month_df["display_amount"].sum()) if not current_month_df.empty else 0.0
        forecast=(current_month_total/max(today.day,1))*monthrange(today.year,today.month)[1]
        a1,a2,a3,a4=st.columns(4)
        with a1: metric_card(t("total_spending"), format_money(total, display_currency), month_label(month_filter))
        with a2: metric_card(t("average_expense"), format_money(avg, display_currency), t("per_transaction"))
        with a3: metric_card(t("transactions"), str(tx), t("recorded_entries"))
        with a4: metric_card(t("forecast"), format_money(forecast, display_currency), t("current_month_estimate"))
        c1,c2=st.columns(2)
        with c1:
            section_start(t("monthly_trend")); st.line_chart(analytics_df.groupby("month", as_index=False)["display_amount"].sum().set_index("month")); section_end()
        with c2:
            section_start(t("category_distribution")); category_pie_chart(analytics_df.groupby("category", as_index=False)["display_amount"].sum().sort_values("display_amount", ascending=False),"display_amount","category"); section_end()
        c3,c4=st.columns([1,1.1])
        with c3:
            section_start(t("daily_spending_this_month"))
            if current_month_df.empty: empty_state(t("no_expenses_this_month"))
            else:
                current_month_df["day"]=current_month_df["date"].dt.day
                st.bar_chart(current_month_df.groupby("day", as_index=False)["display_amount"].sum().set_index("day"))
            section_end()
        with c4:
            section_start(t("month_over_month_comparison"))
            this_month_key=today.strftime("%Y-%m"); prev_month_key=(today.replace(day=1)-pd.Timedelta(days=1)).strftime("%Y-%m")
            grouped=display_df.groupby(["month","category"], as_index=False)["display_amount"].sum()
            this_df=grouped[grouped["month"]==this_month_key][["category","display_amount"]].rename(columns={"display_amount":"this_month"})
            prev_df=grouped[grouped["month"]==prev_month_key][["category","display_amount"]].rename(columns={"display_amount":"last_month"})
            comparison=pd.merge(this_df, prev_df, on="category", how="outer").fillna(0.0)
            comparison["diff"]=comparison["this_month"]-comparison["last_month"]
            comparison["pct_change"]=comparison.apply(lambda row: ((row["diff"]/row["last_month"])*100.0) if row["last_month"]>0 else (100.0 if row["this_month"]>0 else 0.0), axis=1)
            st.dataframe(comparison.sort_values("diff", ascending=False), use_container_width=True, hide_index=True)
            st.markdown(f'<div class="forecast-box"><div class="forecast-label">{t("forecast_for_this_month")}</div><div class="forecast-value">{format_money(forecast, display_currency)}</div></div>', unsafe_allow_html=True)
            section_end()
    section_end()

elif page=="Export":
    month_filter=st.selectbox(t("month_filter"), month_options, index=0, key="export_month_filter", format_func=month_label)
    export_df=filter_by_month(display_df, month_filter)
    section_start(t("export_your_data"), t("download_filtered_or_full"))
    if df.empty and savings_df.empty: empty_state(t("nothing_to_export"))
    else:
        filtered_expenses=export_df.copy()
        if not filtered_expenses.empty: filtered_expenses["date"]=pd.to_datetime(filtered_expenses["date"]).dt.strftime("%Y-%m-%d")
        full_expenses=df.copy()
        if not full_expenses.empty: full_expenses["date"]=pd.to_datetime(full_expenses["date"]).dt.strftime("%Y-%m-%d")
        c1,c2=st.columns(2)
        with c1:
            st.caption(t("filtered_export"))
            st.download_button(t("download_filtered_csv"), data=filtered_expenses.to_csv(index=False).encode("utf-8"), file_name="expenses_filtered.csv", mime="text/csv", use_container_width=True)
            filtered_excel=io.BytesIO()
            with pd.ExcelWriter(filtered_excel, engine="openpyxl") as writer:
                filtered_expenses.to_excel(writer, index=False, sheet_name="Expenses")
                savings_df.to_excel(writer, index=False, sheet_name="Savings")
            filtered_excel.seek(0)
            st.download_button(t("download_filtered_excel"), data=filtered_excel.getvalue(), file_name="finance_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with c2:
            st.caption(t("full_export"))
            st.download_button(t("download_full_csv"), data=full_expenses.to_csv(index=False).encode("utf-8"), file_name="expenses_full.csv", mime="text/csv", use_container_width=True)
            full_excel=io.BytesIO()
            with pd.ExcelWriter(full_excel, engine="openpyxl") as writer:
                full_expenses.to_excel(writer, index=False, sheet_name="Expenses")
                savings_df.to_excel(writer, index=False, sheet_name="Savings")
            full_excel.seek(0)
            st.download_button(t("download_full_excel"), data=full_excel.getvalue(), file_name="finance_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    section_end()

st.markdown("</div>", unsafe_allow_html=True)








