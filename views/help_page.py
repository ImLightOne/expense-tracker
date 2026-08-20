"""Help & Privacy page: a short FAQ plus a plain-language privacy summary.

This page is intentionally static (no ctx-driven data) — it exists so users
have one internal place to find answers and the privacy summary instead of
looking outside the app, and so other pages have somewhere to link to via
st.page_link (see the "Related" blocks added to a few pages in this wave).
"""
from __future__ import annotations

import streamlit as st

from common import end_section, l, privacy_policy_text, section


def _faq_item(question: str, answer: str) -> None:
    with st.expander(question):
        st.write(answer)


def render(ctx: dict) -> None:
    section(
        l("Help & FAQ", "Довідка та FAQ", "Hilfe & FAQ"),
        l(
            "Quick answers to common questions about how the app works.",
            "Короткі відповіді на поширені запитання про роботу застосунку.",
            "Kurze Antworten auf häufige Fragen zur Funktionsweise der App.",
        ),
    )

    pages = ctx.get("pages", {})
    if pages:
        st.caption(l("Jump to:", "Перейти до:", "Direkt zu:"))
        link_cols = st.columns(3)
        with link_cols[0]:
            st.page_link(pages["categories"], label=l("Categories", "Категорії", "Kategorien"), icon=":material/sell:")
        with link_cols[1]:
            st.page_link(pages["subscriptions"], label=l("Subscriptions", "Підписки", "Abos"), icon=":material/autorenew:")
        with link_cols[2]:
            st.page_link(pages["quick_add"], label=l("Quick Add", "Швидке додавання", "Schnell hinzufügen"), icon=":material/bolt:")

    _faq_item(
        l(
            "How does Quick Add understand what I typed?",
            "Як Quick Add розуміє те, що я написав(-ла)?",
            "Wie versteht Quick Add meine Eingabe?",
        ),
        l(
            "Quick Add looks for an amount and a currency in your text, then tries to match a merchant name or "
            "keyword (like \"netflix\" or \"uber\") against a built-in list to guess a category. You always see a "
            "preview before anything is saved, and you can correct the amount, category, or currency there — the "
            "guess is just a starting point.",
            "Quick Add шукає в тексті суму й валюту, а потім намагається зіставити назву мерчанта або ключове "
            "слово (наприклад, \"netflix\" чи \"uber\") із вбудованим списком, щоб вгадати категорію. Перед "
            "збереженням завжди показується попередній перегляд, де можна виправити суму, категорію чи валюту — "
            "здогадка це лише відправна точка.",
            "Quick Add sucht im Text nach einem Betrag und einer Währung und versucht dann, einen Händlernamen "
            "oder ein Schlüsselwort (z. B. \"netflix\" oder \"uber\") mit einer eingebauten Liste abzugleichen, "
            "um eine Kategorie zu erraten. Vor dem Speichern siehst du immer eine Vorschau, in der du Betrag, "
            "Kategorie oder Währung korrigieren kannst — die Vermutung ist nur ein Ausgangspunkt.",
        ),
    )

    _faq_item(
        l(
            "How do recurring transactions and periods work?",
            "Як працюють повторювані транзакції та періоди?",
            "Wie funktionieren wiederkehrende Transaktionen und Zeiträume?",
        ),
        l(
            "When you mark a transaction as recurring, you pick a period — weekly, monthly, or yearly. Each time "
            "you open the app after a period has fully elapsed since the last occurrence, a new transaction is "
            "created automatically for the period(s) that passed. The Subscriptions page normalizes every "
            "recurrence to a \"monthly-equivalent\" amount so weekly, monthly, and yearly items are comparable "
            "side by side — that figure is for comparison only, not a literal monthly charge.",
            "Позначивши транзакцію як повторювану, ти обираєш період — тижневий, місячний або річний. Щоразу, "
            "коли ти відкриваєш застосунок після того, як з моменту останнього разу минув повний період, "
            "автоматично створюється нова транзакція за період(и), що минули. Сторінка \"Підписки\" перераховує "
            "кожен період на \"місячний еквівалент\", щоб тижневі, місячні та річні пункти можна було порівнювати "
            "поруч — це число лише для порівняння, а не буквальне щомісячне списання.",
            "Wenn du eine Transaktion als wiederkehrend markierst, wählst du einen Zeitraum — wöchentlich, "
            "monatlich oder jährlich. Jedes Mal, wenn du die App öffnest, nachdem seit dem letzten Mal ein voller "
            "Zeitraum vergangen ist, wird automatisch eine neue Transaktion für die vergangenen Zeiträume "
            "erstellt. Die Abo-Seite rechnet jeden Zeitraum in einen \"Monatsäquivalent\"-Betrag um, damit "
            "wöchentliche, monatliche und jährliche Posten vergleichbar sind — diese Zahl dient nur dem "
            "Vergleich, nicht einer tatsächlichen monatlichen Abbuchung.",
        ),
    )

    _faq_item(
        l(
            "Can other people see my data?",
            "Чи можуть інші люди бачити мої дані?",
            "Können andere Personen meine Daten sehen?",
        ),
        l(
            "No. Every table (transactions, savings, custom categories) is protected by row-level security "
            "policies in the database that only allow a row to be read or changed by the account that owns it — "
            "the same rule the login system itself relies on. There's no admin view or shared dataset; your data "
            "is scoped to your account.",
            "Ні. Кожна таблиця (транзакції, накопичення, користувацькі категорії) захищена політиками row-level "
            "security в базі даних, які дозволяють читати чи змінювати рядок лише тому акаунту, якому він "
            "належить, — те саме правило, на яке спирається сама система входу. Немає адмін-перегляду чи "
            "спільного набору даних; твої дані прив'язані лише до твого акаунту.",
            "Nein. Jede Tabelle (Transaktionen, Ersparnisse, eigene Kategorien) ist durch Row-Level-Security-"
            "Richtlinien in der Datenbank geschützt, die das Lesen oder Ändern einer Zeile nur dem Konto "
            "erlauben, dem sie gehört — dieselbe Regel, auf die sich auch das Login-System stützt. Es gibt keine "
            "Admin-Ansicht oder gemeinsame Datenbasis; deine Daten sind an dein Konto gebunden.",
        ),
    )

    _faq_item(
        l(
            "Can I add my own categories?",
            "Чи можу я додати власні категорії?",
            "Kann ich eigene Kategorien hinzufügen?",
        ),
        l(
            "Yes — the Categories page lets you add your own expense and income categories on top of the "
            "built-in list, and delete ones you no longer need. Deleting a custom category doesn't change "
            "transactions already recorded with it; they simply keep that category name.",
            "Так — сторінка \"Категорії\" дозволяє додавати власні категорії витрат і доходів поверх вбудованого "
            "списку, а також видаляти ті, що більше не потрібні. Видалення користувацької категорії не змінює "
            "вже внесені з нею транзакції — вони просто зберігають цю назву категорії.",
            "Ja — auf der Seite \"Kategorien\" kannst du eigene Ausgaben- und Einnahmenkategorien zusätzlich zur "
            "eingebauten Liste hinzufügen und nicht mehr benötigte löschen. Das Löschen einer eigenen Kategorie "
            "ändert bereits damit erfasste Transaktionen nicht — sie behalten einfach diesen Kategorienamen.",
        ),
    )

    _faq_item(
        l(
            "Why don't I see my older transactions?",
            "Чому я не бачу старіші транзакції?",
            "Warum sehe ich meine älteren Transaktionen nicht?",
        ),
        l(
            "By default the app only loads the last ~2 years of history on each load, to keep things fast as "
            "your history grows. Turn on \"Load full history\" in the sidebar to load everything — exports "
            "(CSV) always include your complete history regardless of this setting.",
            "За замовчуванням застосунок завантажує лише приблизно останні 2 роки історії, щоб усе працювало "
            "швидко навіть зі зростанням даних. Увімкни \"Завантажити повну історію\" в бічній панелі, щоб "
            "завантажити все — експорт (CSV) завжди містить повну історію незалежно від цього налаштування.",
            "Standardmäßig lädt die App bei jedem Laden nur die letzten ca. 2 Jahre der Historie, damit alles "
            "schnell bleibt, auch wenn deine Daten wachsen. Aktiviere \"Vollständige Historie laden\" in der "
            "Seitenleiste, um alles zu laden — Exporte (CSV) enthalten unabhängig von dieser Einstellung immer "
            "die vollständige Historie.",
        ),
    )
    end_section()

    section(
        l("Privacy policy", "Політика конфіденційності", "Datenschutzerklärung"),
        l(
            "A plain-language summary — not formal legal advice.",
            "Опис простою мовою — це не є формальною юридичною консультацією.",
            "Eine allgemeinverständliche Zusammenfassung — keine formelle Rechtsberatung.",
        ),
    )

    st.markdown(privacy_policy_text())
    end_section()

    section(l("About", "Про проєкт", "Über uns"))
    st.markdown(
        l(
            "Ledgy is designed and built by **PMG (Pyatnychko Media Group)**, founded in 2026. The goal is a "
            "fast, no-nonsense way to track spending — without turning it into a second job.",
            "Ledgy розробляє та створює **PMG (Pyatnychko Media Group)**, заснована у 2026 році. Мета — швидкий "
            "і зрозумілий спосіб відстежувати витрати, без зайвої складності.",
            "Ledgy wird von **PMG (Pyatnychko Media Group)** entworfen und entwickelt, gegründet 2026. Ziel ist "
            "eine schnelle, unkomplizierte Art, Ausgaben im Blick zu behalten — ohne dass es zur zweiten Arbeit wird.",
        )
    )
    end_section()
