DEFAULT_CATEGORIES = [
    "Food", "Transport", "Rent", "Entertainment", "Shopping", "Health",
    "Sports", "Bills", "Cafe", "Education", "Travel", "Other"
]

SUPPORTED_CURRENCIES = ["EUR", "USD", "UAH"]

INCOME_CATEGORIES = ["Salary", "Bonus", "Freelance", "Investments", "Gift", "Refund", "Other Income"]

# Recurrence periods available for recurring (subscription) transactions.
# "monthly" is the historical default — every row created before this option
# existed is backfilled to "monthly" at the database level, so this order
# also doubles as the fallback/display order in the UI.
RECURRENCE_OPTIONS = ["weekly", "monthly", "yearly"]

CATEGORY_COLORS = {
    "Food": "#f97316",
    "Transport": "#3b82f6",
    "Rent": "#8b5cf6",
    "Entertainment": "#ec4899",
    "Shopping": "#14b8a6",
    "Health": "#ef4444",
    "Sports": "#22c55e",
    "Bills": "#f59e0b",
    "Cafe": "#d97706",
    "Education": "#6366f1",
    "Travel": "#06b6d4",
    "Other": "#64748b",
    "Salary": "#10b981",
    "Bonus": "#34d399",
    "Freelance": "#22c55e",
    "Investments": "#059669",
    "Gift": "#6ee7b7",
    "Refund": "#2dd4bf",
    "Other Income": "#0f766e",
}

CATEGORY_TRANSLATIONS = {
    "Food": {"uk": "Їжа", "de": "Essen"},
    "Transport": {"uk": "Транспорт", "de": "Transport"},
    "Rent": {"uk": "Оренда", "de": "Miete"},
    "Entertainment": {"uk": "Розваги", "de": "Unterhaltung"},
    "Shopping": {"uk": "Покупки", "de": "Shopping"},
    "Health": {"uk": "Здоров'я", "de": "Gesundheit"},
    "Sports": {"uk": "Спорт", "de": "Sport"},
    "Bills": {"uk": "Рахунки", "de": "Rechnungen"},
    "Cafe": {"uk": "Кафе", "de": "Café"},
    "Education": {"uk": "Освіта", "de": "Bildung"},
    "Travel": {"uk": "Подорожі", "de": "Reisen"},
    "Other": {"uk": "Інше", "de": "Sonstiges"},
    "Salary": {"uk": "Зарплата", "de": "Gehalt"},
    "Bonus": {"uk": "Бонус", "de": "Bonus"},
    "Freelance": {"uk": "Фриланс", "de": "Freelance"},
    "Investments": {"uk": "Інвестиції", "de": "Investitionen"},
    "Gift": {"uk": "Подарунок", "de": "Geschenk"},
    "Refund": {"uk": "Повернення", "de": "Rückerstattung"},
    "Other Income": {"uk": "Інший дохід", "de": "Sonstige Einnahmen"},
}

CATEGORY_KEYWORDS = {
    "Food": ["grocery", "groceries", "supermarket", "spar", "billa", "lidl", "hofer", "food", "market"],
    "Transport": ["uber", "taxi", "bolt", "train", "bus", "tram", "metro", "fuel", "gas", "parking"],
    "Rent": ["rent", "miete", "housing", "dorm", "wohnung"],
    "Entertainment": ["movie", "cinema", "netflix", "spotify", "game", "steam", "concert", "party"],
    "Shopping": ["amazon", "shopping", "clothes", "zara", "hm", "h&m", "ikea"],
    "Health": ["pharmacy", "doctor", "medicine", "dentist", "medical"],
    "Sports": ["gym", "sport", "supplement", "protein", "run", "bike", "fitness"],
    "Bills": ["electricity", "internet", "phone", "bill", "utility", "versicherung", "insurance"],
    "Cafe": ["coffee", "cafe", "restaurant", "bar", "mcd", "mcdonald", "burger", "pizza"],
    "Education": ["course", "book", "udemy", "education", "study", "uni", "wu", "exam"],
    "Travel": ["flight", "hotel", "booking", "airbnb", "trip", "travel"],
}

MERCHANT_CATEGORY_MAP_EXPENSE = {
    "billa": "Food", "spar": "Food", "lidl": "Food", "hofer": "Food", "penny": "Food", "dm": "Shopping",
    "ikea": "Shopping", "amazon": "Shopping", "zalando": "Shopping", "hm": "Shopping", "h&m": "Shopping", "zara": "Shopping",
    "uber": "Transport", "bolt": "Transport", "oebb": "Transport", "wiener linien": "Transport", "westbahn": "Transport",
    "shell": "Transport", "omv": "Transport", "esso": "Transport",
    "netflix": "Entertainment", "spotify": "Entertainment", "steam": "Entertainment", "kino": "Entertainment",
    "mcdonald": "Cafe", "mcd": "Cafe", "starbucks": "Cafe", "burger king": "Cafe", "subway": "Cafe",
    "pizza": "Cafe", "restaurant": "Cafe", "cafe": "Cafe",
    "fitinn": "Sports", "mcfit": "Sports", "gym": "Sports",
    "bipa": "Health", "pharmacy": "Health", "apotheke": "Health",
    "wu": "Education", "udemy": "Education", "coursera": "Education",
    "airbnb": "Travel", "booking": "Travel", "ryanair": "Travel", "wizz": "Travel",
}

MERCHANT_CATEGORY_MAP_INCOME = {
    "salary": "Salary", "payroll": "Salary", "bonus": "Bonus", "freelance": "Freelance",
    "upwork": "Freelance", "fiverr": "Freelance", "dividend": "Investments", "interest": "Investments",
    "refund": "Refund", "cashback": "Refund", "gift": "Gift",
}

INCOME_KEYWORDS = {
    "Salary": ["salary", "paycheck", "wage", "payroll"],
    "Bonus": ["bonus"],
    "Freelance": ["freelance", "client", "invoice", "project payment", "upwork", "fiverr"],
    "Investments": ["dividend", "interest", "investment", "stock", "etf"],
    "Gift": ["gift", "present"],
    "Refund": ["refund", "cashback", "reimbursement", "returned"],
}

STOPWORDS = {
    "the", "a", "an", "at", "for", "to", "from", "on", "and", "mit", "bei", "im", "in", "am", "vom", "fur", "für",
    "за", "в", "на", "до", "від", "та", "і", "or", "of", "my", "your", "monthly", "payment", "received", "paid"
}

STYLE = """
<style>
/* ---------------------------------------------------------------------
   Minimalist / monochrome theme.

   Earlier versions of this stylesheet read colors from var(--background-
   -color), var(--secondary-background-color), var(--text-color), var(
   --primary-color) — Streamlit used to expose those as CSS custom
   properties. As of the Streamlit version this app runs on, it doesn't:
   those names resolve to nothing anywhere in the page (verified by
   inspecting the live DOM — no stylesheet or inline style defines them),
   so every rule that used them silently rendered as if unset: transparent
   card backgrounds, an invisible accent bar. That's the actual root cause
   of "important numbers look like plain text" — the cards were there,
   just paint-free.

   Fix: --app-bg / --app-secondary-bg / --app-text / --app-primary below
   are our OWN custom properties, hardcoded to Streamlit's actual default
   theme colors (verified against the live DOM: .stApp's computed
   background/text and a primary button's background, in both modes), and
   switched with a plain `@media (prefers-color-scheme: dark)` block. This
   tracks the visitor's OS/browser preference, which is also what
   Streamlit's own default "System" theme choice follows — so for anyone
   who hasn't overridden it, this matches exactly. The one gap: if someone
   manually forces "Light" or "Dark" from Streamlit's menu against their
   OS setting, this stylesheet can't see that override (nothing in the
   page exposes it) and follows the OS instead. Given there's no supported
   hook to read Streamlit's actual theme choice from custom CSS in this
   version, this is the closest reliable match available.

   Category badges are the one deliberate exception to "monochrome": they
   keep their per-category colors (config.CATEGORY_COLORS) because that
   color-coding carries real information (which category is which at a
   glance), not just decoration.
   --------------------------------------------------------------------- */

:root {
  --app-bg: #ffffff;
  --app-secondary-bg: #f0f2f6;
  --app-text: #31333f;
  --app-primary: #ff4b4b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --app-bg: #0e1117;
    --app-secondary-bg: #262730;
    --app-text: #fafafa;
    --app-primary: #ff4b4b;
  }
}

.block-container {max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem;}

[data-testid='stSidebar'] {
  border-right: 1px solid rgba(128,128,128,.18);
}

/* Section "cards" (common.py's section()/end_section()). Targets the real
   st.container(key="section_...") wrapper element by its Streamlit-assigned
   "st-key-section_*" class (attribute-contains selector, since the exact
   key differs per section) rather than a hand-rolled .section-card class on
   a raw <div>: an earlier version opened and closed that div across two
   separate st.markdown() calls, which never actually nests real content
   inside it (each Streamlit call renders into its own isolated DOM node) —
   it only ever produced an empty decorative box floating above the section,
   with the real content sitting outside any card. st.container(key=...) is
   Streamlit's own grouping primitive, so this is the first version that
   genuinely wraps the section on screen. */
[class*="st-key-section_"] {
  background: var(--app-secondary-bg);
  border: 1px solid rgba(128,128,128,.15);
  border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem;
}

/* Stat tiles (metric_card() in common.py). These carry the app's headline
   numbers, so they get real elevation instead of blending into the page:
   a filled surface, a visible border, a soft shadow, and a colored top
   accent bar. The bar is var(--app-primary) by default, or a fixed status
   hex (never themed) when the caller passes a tone — status color lives
   in the accent bar + chip only, never the value text itself, so
   contrast never depends on which theme is active. */
.metric-card {
  /* margin-bottom is the important part here: the two metric rows on the
     dashboard are two separate st.columns() calls stacked by Streamlit's
     own layout, and its default gap between them was thin enough that the
     cards' box-shadow (which paints outside the card's own border box —
     overflow:hidden on this element does not clip its own shadow) read as
     touching/overlapping the row below. An explicit margin guarantees a
     real gap regardless of Streamlit's own spacing between blocks. */
  position: relative;
  overflow: hidden;
  background: var(--app-secondary-bg);
  color: var(--app-text);
  border: 1px solid rgba(128,128,128,.28);
  border-radius: 16px;
  padding: 1.15rem 1.3rem 1.2rem;
  margin-bottom: 1.1rem;
  min-height: 130px;
  box-shadow: 0 1px 4px rgba(0,0,0,.12);
}
.metric-card::before {
  /* Neutral default is gray, not var(--app-primary) — Streamlit's default
     primary color happens to be a red, which next to the tone-critical
     bar (also red) made every untoned tile read as if it were also
     flagged. Color on this bar is reserved for actual tone status. */
  content: "";
  position: absolute; top: 0; left: 0; right: 0; height: 4px;
  background: rgba(128,128,128,.55);
}
.metric-card.tone-good::before     {background:#0ca30c; opacity:1;}
.metric-card.tone-warning::before  {background:#fab219; opacity:1;}
.metric-card.tone-serious::before  {background:#ec835a; opacity:1;}
.metric-card.tone-critical::before {background:#d03b3b; opacity:1;}

.metric-label {
  font-size:.74rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
  opacity:.62; margin-bottom:.45rem;
}
.metric-value {font-size:1.9rem; font-weight:700; line-height:1.1; letter-spacing:-.01em;}
.metric-foot {font-size:.85rem; opacity:.65; margin-top:.5rem;}
.small-muted {opacity:.68; font-size:.9rem;}

.tone-chip {
  display:inline-block; margin-top:.55rem; padding:.24rem .68rem; border-radius:999px;
  font-size:.76rem; font-weight:700;
}

.badge {
  display:inline-block; padding:.2rem .55rem; border-radius:999px;
  font-size:.76rem; font-weight:700; color:white;
}

.feed-row {
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  flex-wrap: wrap;
  padding:.75rem; border:1px solid rgba(128,128,128,.15); border-radius:12px;
  margin-bottom:.5rem; background:var(--app-secondary-bg);
}

.soft-box {
  border:1px dashed rgba(128,128,128,.28); border-radius:14px; padding:1rem;
  background:var(--app-secondary-bg);
}

/* ---------------------------------------------------------------------
   Mobile: tighten spacing and type scale below ~640px (typical phone
   width) so cards and metrics don't feel oversized or cramped once
   Streamlit's columns stack vertically.
   --------------------------------------------------------------------- */
@media (max-width: 640px) {
  .block-container {padding-left: .75rem; padding-right: .75rem;}
  [class*="st-key-section_"] {padding: .85rem; border-radius: 12px;}
  .metric-card {padding: .9rem 1rem 1rem; min-height: unset;}
  .metric-value {font-size:1.5rem;}
  .metric-label {font-size:.7rem;}
  .metric-foot {font-size:.78rem;}
  .tone-chip {font-size:.7rem; padding:.2rem .55rem;}
  .feed-row {padding:.6rem; flex-direction: column; align-items: flex-start;}
  .badge {font-size:.72rem;}
}
</style>
"""
