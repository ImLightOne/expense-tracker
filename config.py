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
   Minimalist / monochrome theme. Everything here reads its colors from
   Streamlit's own CSS variables (--background-color, --text-color, etc.)
   instead of hardcoded hex values, so the whole UI — including the
   sidebar and custom cards — follows whichever theme the visitor picks
   from Streamlit's native "Choose app theme" menu (top-right ⋮ menu),
   light or dark, without needing a separate in-app toggle. Category
   badges are the one deliberate exception: they keep their per-category
   colors (config.CATEGORY_COLORS) because that color-coding carries real
   information (which category is which at a glance), not just decoration.
   --------------------------------------------------------------------- */

.block-container {max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem;}

[data-testid='stSidebar'] {
  border-right: 1px solid rgba(128,128,128,.18);
}

.section-card {
  background: var(--secondary-background-color);
  border: 1px solid rgba(128,128,128,.15);
  border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem;
}

.metric-card {
  background: var(--secondary-background-color);
  color: var(--text-color);
  border: 1px solid rgba(128,128,128,.15);
  border-left: 3px solid var(--primary-color);
  border-radius: 14px; padding: 1rem; min-height: 118px;
}
.metric-label {font-size:.9rem; opacity:.7; margin-bottom:.35rem;}
.metric-value {font-size:1.6rem; font-weight:700; line-height:1.1;}
.metric-foot {font-size:.85rem; opacity:.65; margin-top:.4rem;}
.small-muted {opacity:.68; font-size:.9rem;}

.badge {
  display:inline-block; padding:.2rem .55rem; border-radius:999px;
  font-size:.76rem; font-weight:700; color:white;
}

.feed-row {
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  flex-wrap: wrap;
  padding:.75rem; border:1px solid rgba(128,128,128,.15); border-radius:12px;
  margin-bottom:.5rem; background:var(--secondary-background-color);
}

.soft-box {
  border:1px dashed rgba(128,128,128,.28); border-radius:14px; padding:1rem;
  background:var(--secondary-background-color);
}

/* ---------------------------------------------------------------------
   Mobile: tighten spacing and type scale below ~640px (typical phone
   width) so cards and metrics don't feel oversized or cramped once
   Streamlit's columns stack vertically.
   --------------------------------------------------------------------- */
@media (max-width: 640px) {
  .block-container {padding-left: .75rem; padding-right: .75rem;}
  .section-card {padding: .85rem; border-radius: 12px;}
  .metric-card {padding: .85rem; min-height: unset;}
  .metric-value {font-size:1.35rem;}
  .metric-label {font-size:.82rem;}
  .metric-foot {font-size:.78rem;}
  .feed-row {padding:.6rem; flex-direction: column; align-items: flex-start;}
  .badge {font-size:.72rem;}
}
</style>
"""
