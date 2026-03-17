import re
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd

from config import (
    CATEGORY_KEYWORDS,
    INCOME_KEYWORDS,
    MERCHANT_CATEGORY_MAP_EXPENSE,
    MERCHANT_CATEGORY_MAP_INCOME,
    STOPWORDS,
)


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def format_money(value: float, currency: str = "EUR") -> str:
    return f"{value:,.2f} {currency}".replace(",", " ")


def month_key(dt: pd.Timestamp | date | datetime) -> str:
    return pd.Timestamp(dt).strftime("%Y-%m")


def normalize_quick_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    text = re.sub(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", " ", text)
    text = re.sub(r"\b(?:eur|usd|uah|€|\$|₴)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\d)\d+[\.,]?\d{0,2}(?!\d)", " ", text)
    text = re.sub(r"[^\w\s&+-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_quick_text(text: str) -> List[str]:
    normalized = normalize_quick_text(text)
    return [tok for tok in normalized.split() if tok and tok not in STOPWORDS]


def detect_merchant_candidate(text: str, tx_type: str = "expense") -> str:
    normalized = normalize_quick_text(text)
    merchant_map = MERCHANT_CATEGORY_MAP_INCOME if tx_type == "income" else MERCHANT_CATEGORY_MAP_EXPENSE
    matches = [merchant for merchant in merchant_map if merchant in normalized]
    if matches:
        return max(matches, key=len)
    tokens = tokenize_quick_text(text)
    return " ".join(tokens[:2]).strip()


def infer_category(note: str, fallback: str = "Other", history_df: Optional[pd.DataFrame] = None, tx_type: str = "expense") -> Dict[str, object]:
    text = (note or "").strip()
    if not text:
        return {"category": fallback, "confidence": "low", "reason": "empty", "scores": {}, "merchant": ""}

    normalized = normalize_quick_text(text)
    tokens = tokenize_quick_text(text)
    merchant = detect_merchant_candidate(text, tx_type=tx_type)
    scores: Dict[str, float] = {}
    merchant_map = MERCHANT_CATEGORY_MAP_INCOME if tx_type == "income" else MERCHANT_CATEGORY_MAP_EXPENSE
    keyword_map = INCOME_KEYWORDS if tx_type == "income" else CATEGORY_KEYWORDS

    def add_score(category: str, points: float):
        if category:
            scores[category] = scores.get(category, 0.0) + float(points)

    matched_merchant = ""
    for merchant_key, category in merchant_map.items():
        if merchant_key and merchant_key in normalized:
            add_score(category, 6)
            matched_merchant = merchant_key

    history_reason = None
    if history_df is not None and not getattr(history_df, 'empty', True):
        hist = history_df.copy()
        if "type" in hist.columns:
            hist = hist[hist["type"].fillna("expense").astype(str).str.lower() == tx_type]
        if not hist.empty and "note" in hist.columns and "category" in hist.columns:
            notes = hist["note"].fillna("").astype(str)
            note_norm = notes.apply(normalize_quick_text)
            masks = []
            if matched_merchant:
                masks.append(note_norm.str.contains(re.escape(matched_merchant), regex=True, na=False))
            elif merchant:
                masks.append(note_norm.str.contains(re.escape(merchant), regex=True, na=False))
            if tokens:
                token_matches = pd.DataFrame({tok: note_norm.str.contains(rf"\b{re.escape(tok)}\b", regex=True, na=False) for tok in tokens[:4]})
                if not token_matches.empty:
                    masks.append(token_matches.sum(axis=1) >= min(2, max(1, len(tokens[:4]))))
            if masks:
                combined = masks[0]
                for extra in masks[1:]:
                    combined = combined | extra
                hist_match = hist[combined]
                if not hist_match.empty:
                    counts = hist_match["category"].value_counts()
                    if not counts.empty:
                        top_category = counts.index[0]
                        dominance = counts.iloc[0] / max(len(hist_match), 1)
                        add_score(str(top_category), 4 + 4 * dominance)
                        history_reason = f"history:{top_category}:{len(hist_match)}"

    for category, keywords in keyword_map.items():
        for keyword in keywords:
            keyword_norm = normalize_quick_text(keyword)
            if not keyword_norm:
                continue
            if keyword_norm in normalized:
                add_score(category, 2.5 if " " in keyword_norm else 1.5)
            for tok in tokens:
                if tok == keyword_norm:
                    add_score(category, 2)

    if tx_type == "expense":
        if any(tok in {"coffee", "lunch", "dinner", "breakfast", "pizza", "burger"} for tok in tokens):
            add_score("Cafe", 1.5)
        if any(tok in {"grocery", "groceries", "supermarket"} for tok in tokens):
            add_score("Food", 1.5)
    else:
        if any(tok in {"salary", "bonus", "refund", "gift"} for tok in tokens):
            mapping = {"salary": "Salary", "bonus": "Bonus", "refund": "Refund", "gift": "Gift"}
            for tok in tokens:
                if tok in mapping:
                    add_score(mapping[tok], 2)

    if scores:
        best_category, best_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)[0]
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
        gap = best_score - second_score
        confidence = "high" if best_score >= 6 or gap >= 3 else "medium" if best_score >= 3 else "low"
        reason = "merchant" if matched_merchant else history_reason or "keywords"
        return {
            "category": best_category,
            "confidence": confidence,
            "reason": reason,
            "scores": dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
            "merchant": merchant or matched_merchant,
        }

    return {"category": fallback, "confidence": "low", "reason": "fallback", "scores": {}, "merchant": merchant}


def extract_merchant(note: str, category: str) -> str:
    text = (note or "").strip()
    if not text:
        return category
    normalized = re.sub(r"[^\w\s&-]", " ", text).strip()
    parts = [p for p in normalized.split() if p]
    if not parts:
        return category
    return " ".join(parts[:2]).title()


def parse_quick_add(text: str, history_df: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    raw = (text or "").strip()
    result: Dict[str, object] = {
        "ok": False,
        "amount": None,
        "currency": "EUR",
        "date": date.today(),
        "category": "Other",
        "note": raw,
        "subscription": False,
        "tx_type": "expense",
        "confidence": "low",
        "category_reason": "fallback",
        "merchant_guess": "",
        "category_scores": {},
        "error": "Could not parse the entry. Example: 2026-03-17 12.50 EUR coffee at Starbucks",
    }
    if not raw:
        return result

    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw)
    if date_match:
        try:
            result["date"] = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except Exception:
            pass
    else:
        short_match = re.search(r"\b(\d{1,2}[./-]\d{1,2})(?:[./-](\d{2,4}))?\b", raw)
        if short_match:
            token = short_match.group(0).replace(".", "-").replace("/", "-")
            parts = token.split("-")
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else date.today().year
            if year < 100:
                year += 2000
            try:
                result["date"] = date(year, month, day)
            except Exception:
                pass

    amount_search_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", raw)
    amount_match = re.search(r"(?<!\d)(\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)(?!\d)", amount_search_text)
    if not amount_match:
        return result
    amount_token = amount_match.group(1).replace(" ", "")
    if "," in amount_token and "." in amount_token:
        amount_token = amount_token.replace(",", "")
    else:
        amount_token = amount_token.replace(",", ".")
    amount = safe_float(amount_token, None)
    if amount is None:
        return result
    result["amount"] = amount

    currency_match = re.search(r"(EUR|USD|UAH|€|\$|₴)", raw, flags=re.IGNORECASE)
    if currency_match:
        token = currency_match.group(1).upper()
        result["currency"] = {"€": "EUR", "$": "USD", "₴": "UAH"}.get(token, token)

    lowered = raw.lower()
    result["subscription"] = any(word in lowered for word in ["subscription", "sub", "abo", "monthly", "netflix", "spotify"])
    income_markers = ["income", "salary", "bonus", "refund", "cashback", "gift", "freelance", "paid", "payment received"]
    result["tx_type"] = "income" if any(word in lowered for word in income_markers) else "expense"
    default_fallback = "Other Income" if result["tx_type"] == "income" else "Other"
    category_info = infer_category(raw, fallback=default_fallback, history_df=history_df, tx_type=result["tx_type"])
    result["category"] = category_info.get("category", default_fallback)
    result["confidence"] = category_info.get("confidence", "low")
    result["category_reason"] = category_info.get("reason", "fallback")
    result["merchant_guess"] = category_info.get("merchant", "")
    result["category_scores"] = category_info.get("scores", {})
    result["ok"] = True
    result["error"] = ""
    return result
