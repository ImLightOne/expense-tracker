from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from analytics import csv_template, enrich_expenses
from common import end_section, l, rerun, section, show_empty
from config import RECURRENCE_OPTIONS
from db import add_transaction, load_expenses
from utils import infer_category, safe_float


def render(ctx: dict) -> None:
    user_id = ctx["user_id"]
    display_currency = ctx["display_currency"]
    filtered_df = ctx["filtered_df"]
    base_display_df = ctx["base_display_df"]
    expense_categories = ctx["expense_categories"]
    income_categories = ctx["income_categories"]

    section(l("Export data", "Експорт даних", "Datenexport"), l("Filtered or full downloads for backup and analysis.", "Завантаження відфільтрованих або повних даних для резерву та аналізу.", "Gefilterte oder vollständige Downloads für Backup und Analyse."))
    export_df = filtered_df.copy()
    # "Full" export must never silently truncate, even though the app's main
    # dataframe is bounded to a recent window by default for performance
    # (see the "Load full history" sidebar toggle). Re-fetch unbounded here
    # unless that toggle is already on, in which case base_display_df is
    # already the complete history and re-fetching would be wasted work.
    if ctx.get("history_is_complete"):
        full_df = base_display_df.copy()
    else:
        full_df = enrich_expenses(load_expenses(user_id), display_currency)

    if export_df.empty and full_df.empty:
        show_empty(l("Nothing to export yet.", "Поки нічого експортувати.", "Noch nichts zu exportieren."))
    else:
        def to_excel_bytes(df: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Expenses")
            return output.getvalue()

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(l("Download filtered CSV", "Завантажити відфільтрований CSV", "Gefiltertes CSV herunterladen"), export_df.to_csv(index=False).encode("utf-8"), "expenses_filtered.csv", "text/csv", use_container_width=True)
            st.download_button(l("Download filtered Excel", "Завантажити відфільтрований Excel", "Gefiltertes Excel herunterladen"), to_excel_bytes(export_df), "expenses_filtered.xlsx", use_container_width=True)
        with c2:
            st.download_button(l("Download full CSV", "Завантажити повний CSV", "Vollständiges CSV herunterladen"), full_df.to_csv(index=False).encode("utf-8"), "expenses_full.csv", "text/csv", use_container_width=True)
            st.download_button(l("Download full Excel", "Завантажити повний Excel", "Vollständiges Excel herunterladen"), to_excel_bytes(full_df), "expenses_full.xlsx", use_container_width=True)
    end_section()

    section(l("CSV template", "CSV-шаблон", "CSV-Vorlage"), l("Use this format for bulk import. You can include type=income or expense.", "Використовуй цей формат для масового імпорту. Можна вказати type=income або expense.", "Nutze dieses Format für den Massenimport. Du kannst type=income oder expense angeben."))
    st.download_button(l("Download CSV template", "Завантажити CSV-шаблон", "CSV-Vorlage herunterladen"), csv_template(), "expense_import_template.csv", "text/csv", use_container_width=True)
    end_section()

    section(l("Bulk import", "Масовий імпорт", "Massenimport"), l("Expected columns: date, amount, currency, category, note, subscription, recurrence, type.", "Очікувані колонки: date, amount, currency, category, note, subscription, recurrence, type.", "Erwartete Spalten: date, amount, currency, category, note, subscription, recurrence, type."))
    uploaded = st.file_uploader(l("Upload CSV", "Завантажити CSV", "CSV hochladen"), type=["csv"])
    if uploaded is not None:
        try:
            incoming = pd.read_csv(uploaded)
            st.write(f"**{l('Preview', 'Попередній перегляд', 'Vorschau')}**")
            st.dataframe(incoming.head(10), use_container_width=True, hide_index=True)
            required = {"date", "amount"}
            if not required.issubset(set(incoming.columns.str.lower())):
                st.error(l("CSV must contain at least: date, amount", "CSV має містити щонайменше: date, amount", "CSV muss mindestens enthalten: date, amount"))
            else:
                incoming.columns = [c.lower().strip() for c in incoming.columns]
                incoming["currency"] = incoming.get("currency", "EUR").fillna("EUR")
                incoming["category"] = incoming.get("category", "Other").fillna("Other")
                incoming["note"] = incoming.get("note", "").fillna("")
                incoming["subscription"] = pd.to_numeric(incoming.get("subscription", 0), errors="coerce").fillna(0).astype(int)
                incoming["recurrence"] = incoming.get("recurrence", "monthly").fillna("monthly").astype(str).str.lower()
                incoming["type"] = incoming.get("type", "expense").fillna("expense").astype(str).str.lower()
                valid_rows = []
                for _, row in incoming.iterrows():
                    try:
                        d = pd.to_datetime(row["date"]).date()
                        amt = safe_float(row["amount"])
                        cur = str(row.get("currency", "EUR")).upper()
                        cat = str(row.get("category", "Other"))
                        note = str(row.get("note", ""))
                        sub = int(row.get("subscription", 0))
                        rec = str(row.get("recurrence", "monthly"))
                        rec = rec if rec in RECURRENCE_OPTIONS else "monthly"
                        tx_type = "income" if str(row.get("type", "expense")).lower() == "income" else "expense"
                        valid_categories = income_categories if tx_type == "income" else expense_categories
                        if cat not in valid_categories:
                            cat = infer_category(note, fallback="Other Income" if tx_type == "income" else "Other")["category"]
                        valid_rows.append((d, amt, cur, cat, note, sub, rec, tx_type))
                    except Exception as e:
                        st.warning(f"Skipped: {e}")
                        continue
                st.caption(f"{l('Valid rows ready to import', 'Валідних рядків готово до імпорту', 'Gültige Zeilen bereit für den Import')}: {len(valid_rows)}")
                if valid_rows and st.button(l("Import rows", "Імпортувати рядки", "Zeilen importieren"), use_container_width=True, type="primary"):
                    for d, amt, cur, cat, note, sub, rec, tx_type in valid_rows:
                        add_transaction(user_id, d, amt, cat, cur, tx_type, note, sub, rec)
                    st.success(f"{l('Imported', 'Імпортовано', 'Importiert')} {len(valid_rows)} {l('row(s).', 'рядків.', 'Zeile(n).')}")
                    rerun()
        except Exception as exc:
            st.error(f"{l('Failed to read CSV', 'Не вдалося прочитати CSV', 'CSV konnte nicht gelesen werden')}: {exc}")
    end_section()
