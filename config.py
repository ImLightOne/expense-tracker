DEFAULT_CATEGORIES = [
    "Food", "Transport", "Rent", "Entertainment", "Shopping", "Health",
    "Sports", "Bills", "Cafe", "Education", "Travel", "Other"
]

SUPPORTED_CURRENCIES = ["EUR", "USD", "UAH"]

INCOME_CATEGORIES = ["Salary", "Bonus", "Freelance", "Investments", "Gift", "Refund", "Other Income"]

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
.block-container {max-width: 1400px; padding-top: 1rem; padding-bottom: 2rem;}
[data-testid='stSidebar'] {background: linear-gradient(180deg,#111827 0%,#0f172a 100%) !important;}
[data-testid='stSidebar'], [data-testid='stSidebar'] * {color: white !important;}
.section-card {
  background: var(--secondary-background-color);
  border: 1px solid rgba(128,128,128,.18);
  border-radius: 18px; padding: 1rem; margin-bottom: 1rem;
  box-shadow: 0 8px 24px rgba(15,23,42,.06);
}
.metric-card {
  background: linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  color: white; border-radius: 18px; padding: 1rem; min-height: 125px;
  box-shadow: 0 10px 28px rgba(15,23,42,.18);
}
.metric-label {font-size:.95rem; opacity:.8; margin-bottom:.35rem;}
.metric-value {font-size:1.7rem; font-weight:800; line-height:1.08;}
.metric-foot {font-size:.88rem; opacity:.75; margin-top:.4rem;}
.small-muted {opacity:.72; font-size:.92rem;}
.badge {
  display:inline-block; padding:.2rem .55rem; border-radius:999px;
  font-size:.76rem; font-weight:700; color:white;
}
.feed-row {
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  padding:.75rem; border:1px solid rgba(128,128,128,.18); border-radius:14px;
  margin-bottom:.55rem; background:var(--secondary-background-color);
}
.soft-box {
  border:1px dashed rgba(128,128,128,.28); border-radius:16px; padding:1rem;
  background:var(--secondary-background-color);
}
</style>
"""
