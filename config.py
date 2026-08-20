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
   "Confident & modern" theme — Wave 3, iteration 7.

   One deliberate brand color (a deep, saturated blue — #1d4ed8 light /
   #5b8cff dark) on a neutral background, crisp small-radius shapes, no
   gradients, no decorative blur/glow. This is a full swap of what used to
   be a "minimalist / monochrome" palette borrowed from Streamlit's own
   default colors (including its default red primaryColor) — that default
   look is also exactly what made the app read as an unstyled/default
   Streamlit app rather than its own product. --app-primary here is now
   the SAME hex as .streamlit/config.toml's [theme.light]/[theme.dark]
   primaryColor, so native widgets (st.button, st.checkbox, focus rings,
   links) and this stylesheet's own custom HTML (.metric-card accents,
   the brand mark) finally agree on one accent instead of two clashing
   ones (custom CSS's old accent vs. Streamlit's default red button).

   These are still OUR OWN custom properties (not Streamlit's var(--
   primary-color) etc, which don't exist in this Streamlit version's DOM —
   see git history for how that was confirmed), switched with a plain
   `@media (prefers-color-scheme: dark)` block that tracks the same OS/
   browser preference Streamlit's own "Use system setting" theme option
   defaults to.

   Category badges are the one deliberate exception to "one brand color":
   they keep their per-category colors (config.CATEGORY_COLORS) because
   that color-coding carries real information (which category is which at
   a glance), not just decoration — and are visually distinct from the
   brand color by context (small pills vs. buttons/accents/nav), not hue
   alone.
   --------------------------------------------------------------------- */

:root {
  --app-bg: #ffffff;
  --app-secondary-bg: #f4f5f9;
  --app-text: #1a1d29;
  --app-primary: #1d4ed8;
  --app-border: rgba(15,23,42,.12);
  --app-radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --app-bg: #0e1117;
    --app-secondary-bg: #262730;
    --app-text: #fafafa;
    --app-primary: #5b8cff;
    --app-border: rgba(255,255,255,.14);
  }
}

/* padding-top clears Streamlit's own fixed header bar (the top strip that
   holds the "⋮" menu / Deploy button): that header is ~60px tall and
   position:absolute, so it does not take up document flow space — any
   content sitting at the very top of .block-container physically renders
   underneath it unless padding pushes past it. The previous 1rem (16px)
   was never really enough (verified live: the app's own heading text was
   partially hidden behind the header, top of the letters clipped flat);
   it went unnoticed only because a plain st.title() call's default font
   size made the clipped sliver easy to miss. Caught while adding the
   larger brand mark + wordmark header, which made the clipping obvious. */
.block-container {max-width: 1400px; padding-top: 4rem; padding-bottom: 2rem;}

[data-testid='stSidebar'] {
  border-right: 1px solid var(--app-border);
}

/* Brand mark + wordmark, used in the sidebar header and the pre-login
   hero (see common.py's brand_header()). Replaces the old plain-emoji
   "💸 Expense Tracker Pro+" text — a hand-drawn geometric mark (rounded
   square, three ascending bars) reads as a designed identity instead of a
   generic Unicode emoji standing in for a logo. */
.brand-header {
  display:flex; align-items:center; gap:.55rem; margin-bottom:.15rem;
}
.brand-header svg {flex-shrink:0; display:block;}
.brand-wordmark {font-weight:800; font-size:1.15rem; letter-spacing:-.01em; color:var(--app-text);}
.brand-header.brand-hero .brand-wordmark {font-size:1.7rem;}

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
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius); padding: 1.1rem; margin-bottom: 1rem;
}

/* Stat tiles (metric_card() in common.py). Crisp, flat surfaces — a
   filled background and a hairline border carry the separation from the
   page; no drop shadow, which used to read as a slightly "soft/AI-
   dashboard" default rather than a deliberate, confident flat design (the
   Linear/Stripe/Vercel school, not the neumorphic-card school). The top
   accent bar is reserved for actual status (tone-good/warning/serious/
   critical) — untoned cards render with no bar at all rather than a
   neutral gray one, so a status bar always means something instead of
   every single tile having one "just in case". */
.metric-card {
  /* margin-bottom is the important part here: the two metric rows on the
     dashboard are two separate st.columns() calls stacked by Streamlit's
     own layout, and its default gap between them was thin enough that the
     cards' accent bar could read as touching/overlapping the row below.
     An explicit margin guarantees a real gap regardless of Streamlit's
     own spacing between blocks. */
  position: relative;
  overflow: hidden;
  background: var(--app-secondary-bg);
  color: var(--app-text);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  padding: 1.15rem 1.3rem 1.2rem;
  margin-bottom: 1.1rem;
  min-height: 130px;
}
.metric-card.tone-good::before,
.metric-card.tone-warning::before,
.metric-card.tone-serious::before,
.metric-card.tone-critical::before {
  content: "";
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.metric-card.tone-good::before     {background:#0ca30c;}
.metric-card.tone-warning::before  {background:#fab219;}
.metric-card.tone-serious::before  {background:#ec835a;}
.metric-card.tone-critical::before {background:#d03b3b;}

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
  padding:.75rem; border:1px solid var(--app-border); border-radius: var(--app-radius);
  margin-bottom:.5rem; background:var(--app-secondary-bg);
}

.soft-box {
  border:1px dashed var(--app-border); border-radius: var(--app-radius); padding:1rem;
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
