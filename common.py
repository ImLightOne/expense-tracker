"""Shared helpers, auth flow, and translations used by the entry point and
every page in views/. Keeping this in one module (instead of duplicating
across pages, or relying on Streamlit script-global state) is the whole
point of the Wave 2 page split: each page imports what it needs from here
instead of re-declaring it.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from analytics import category_summary
from config import CATEGORY_COLORS, CATEGORY_TRANSLATIONS, STYLE
from db import (
    get_profile_username,
    get_rates_map as db_get_rates_map,
    request_password_reset as db_request_password_reset,
    restore_auth_session,
    sign_in,
    sign_out,
    sign_up,
    update_password,
    username_exists,
    verify_otp,
)
from utils import format_money, lighten_hex, readable_text_color, safe_float

# Inline SVG brand mark (rounded square + three ascending bars — a plain
# growth/analytics glyph). Replaces the old "💸" emoji used as a stand-in
# logo everywhere (sidebar header, pre-login hero, browser tab icon): a
# generic Unicode emoji doing double duty as a product's visual identity
# is one of the more obvious "nobody designed this" tells. fill uses
# var(--app-primary) so the mark automatically follows the same light/dark
# brand color as the rest of the theme (config.py's STYLE block), with no
# separate dark-mode variant needed. The favicon (assets/favicon.png,
# passed to st.set_page_config) is a static PNG render of the same design,
# since browser tab icons can't use CSS variables.
BRAND_MARK_SVG = (
    '<svg viewBox="0 0 256 256" width="{size}" height="{size}" '
    'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="logo">'
    '<rect width="256" height="256" rx="61" fill="var(--app-primary)"/>'
    '<rect x="41" y="163" width="43" height="52" rx="12" fill="#ffffff"/>'
    '<rect x="107" y="125" width="43" height="90" rx="12" fill="#ffffff"/>'
    '<rect x="173" y="86" width="43" height="129" rx="12" fill="#ffffff"/>'
    '</svg>'
)


def brand_header(title: str, size: int = 28, hero: bool = False) -> None:
    """Render the brand mark next to the wordmark text. Used in the sidebar
    header (small) and the pre-login hero (large, hero=True) so both places
    share one identity instead of the sidebar using an emoji+text markdown
    heading and the hero using a different plain st.title().
    """
    css_class = "brand-header brand-hero" if hero else "brand-header"
    st.markdown(
        f'<div class="{css_class}">{BRAND_MARK_SVG.format(size=size)}'
        f'<span class="brand-wordmark">{title}</span></div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Small, quiet company-credit line at the bottom of every page — the
    kind of "who made this" attribution a professional site carries, but
    kept out of the way of the actual content above it.
    """
    st.divider()
    st.markdown(f'<div class="small-muted" style="text-align:center;">{t("footer_text")}</div>', unsafe_allow_html=True)


def inject_style() -> None:
    """Injects the app's <style> block. Must be called explicitly from the
    main script body on every run — NOT left as module-level code here.

    Streamlit reruns expense_tracker_app.py (the main script) top to bottom
    on every interaction, but a `from common import ...` on those reruns
    hits Python's sys.modules cache: common.py's top-level statements only
    execute once, the first time the module is ever imported in this
    process. A bare `st.markdown(STYLE, ...)` at module level here used to
    rely on that one-time execution — so the stylesheet was only ever
    present on a session's very first script run, and vanished from the
    DOM on every rerun after (which is effectively always, since logging
    in alone triggers one). Calling this from the main script instead
    means it re-runs — and re-injects the <style> tag — every single time,
    same as everything else the main script does on every rerun.
    """
    st.markdown(STYLE, unsafe_allow_html=True)


# =========================================================
# UI UTILITIES
# =========================================================

def rerun() -> None:
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


_section_stack: List = []
_section_key_counts: Dict[str, int] = {}


def _section_key(title: str) -> str:
    """Streamlit container keys must be unique within one script run. Titles
    are unique per page in practice, but two different pages can reuse the
    same title (e.g. both "savings.py" and "dashboard.py" have a "Savings
    goals" section) — since only one page's render() runs per script, that's
    fine on its own, but guard against any real duplicate within a single
    run anyway rather than relying on that.
    """
    slug = "".join(c.lower() if c.isalnum() else "_" for c in title).strip("_")
    count = _section_key_counts.get(slug, 0)
    _section_key_counts[slug] = count + 1
    return f"section_{slug}_{count}" if count else f"section_{slug}"


def section(title: str, subtitle: Optional[str] = None) -> None:
    """Opens a visually-styled "card" wrapper (background, border, rounded
    corners — see .section-card / .st-key-section_* in config.py's STYLE)
    around everything rendered until the matching end_section() call.

    This used to be `st.markdown('<div class="section-card">', ...)` here
    and `st.markdown('</div>', ...)` in end_section(). That looked reasonable
    but was silently broken: every st.markdown/st.subheader/etc. call in
    Streamlit renders into its own separate, isolated DOM node, so an
    unclosed <div> opened in one call's HTML and a closing </div> injected
    by a later, different call never actually nest around the content in
    between in the real DOM — confirmed by inspecting the live DOM, every
    .section-card element had zero children. The result: an empty little
    decorative box floating above each section, with the section's actual
    content sitting outside any card at all.

    st.container(key=...) is Streamlit's real (React-level) grouping
    primitive — content written inside a `with` block on it is a genuine
    DOM child — so giving it a CSS class via `key` and manually pairing
    __enter__/__exit__ (mirroring the old open/close call pattern so every
    existing section()/end_section() call site keeps working unchanged) is
    what actually wraps the section on screen.
    """
    container = st.container(key=_section_key(title))
    container.__enter__()
    _section_stack.append(container)
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def end_section() -> None:
    if _section_stack:
        _section_stack.pop().__exit__(None, None, None)


# Fixed status colors (never themed — same hex regardless of light/dark mode).
# Used only as a chip's own background+ink pair, never as page text color, so
# contrast never depends on Streamlit's current theme: the chip carries its own
# background, so it always clears contrast against its own ink.
_TONE_CHIP_STYLE = {
    "good": ("#0ca30c", "#ffffff"),
    "warning": ("#fab219", "#1a1a19"),
    "serious": ("#ec835a", "#1a1a19"),
    "critical": ("#d03b3b", "#ffffff"),
}


def metric_card(label: str, value: str, foot: str = "", tone: Optional[str] = None, chip: Optional[str] = None) -> None:
    """Render a stat tile.

    `tone` (None / "good" / "warning" / "serious" / "critical") colors the card's
    top accent bar and, when `chip` is also given, renders `chip` as a small solid
    pill badge. The headline `value` always stays in the page's normal text color —
    status is carried by the label text, the chip text, and the accent bar together,
    never by tinting the number itself (that would fail contrast on a light theme
    for the warning/serious hues, and color-alone isn't an accessible signal anyway).
    """
    tone_class = f" tone-{tone}" if tone in _TONE_CHIP_STYLE else ""
    chip_html = ""
    if chip and tone in _TONE_CHIP_STYLE:
        bg, ink = _TONE_CHIP_STYLE[tone]
        chip_html = f'<span class="tone-chip" style="background:{bg};color:{ink};">{chip}</span>'
    foot_html = f'<div class="metric-foot">{foot}</div>' if foot else ""
    st.markdown(
        f'<div class="metric-card{tone_class}"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'{chip_html}{foot_html}</div>',
        unsafe_allow_html=True,
    )


def show_empty(text: str) -> None:
    st.markdown(f'<div class="soft-box">{text}</div>', unsafe_allow_html=True)


def privacy_policy_text() -> str:
    """The plain-language Privacy Policy summary, in the current language.

    Shared between the Help page (where it's the canonical, permanent copy)
    and the registration form's expandable preview — a single source of
    truth so the two never drift apart. Registration needs its own copy of
    the text (not a link to the Help page) because a not-yet-registered
    visitor has no session yet and can't navigate to a page that only
    exists inside the logged-in app shell.
    """
    return l(
        "**Who operates this app.** Ledgy is developed and operated by PMG (Pyatnychko Media Group).\n\n"
        "**What we collect.** Your email address (for login), the transactions, savings entries, budgets, "
        "and custom categories you enter, and basic account metadata (username, password hash).\n\n"
        "**Where it's stored.** In a Supabase-hosted Postgres database, protected by row-level security so "
        "only your own account can read or write your rows.\n\n"
        "**Third-party services.** Currency conversion rates are fetched from the Frankfurter and National "
        "Bank of Ukraine (NBU) public APIs. Only the currency codes and dates needed for the conversion are "
        "sent — no personal data or transaction details leave the app for this.\n\n"
        "**Account deletion.** Self-service account deletion isn't available in the app yet. If you'd like "
        "your account and data removed, reach out to the person who manages this app for you.\n\n"
        "**Changes.** This summary may be updated as the app evolves; check back on the Help page for the "
        "current version.",
        "**Хто керує застосунком.** Ledgy розробляє та підтримує PMG (Pyatnychko Media Group).\n\n"
        "**Що ми збираємо.** Твою електронну пошту (для входу), внесені тобою транзакції, записи "
        "накопичень, бюджети й користувацькі категорії, а також базові метадані акаунту (ім'я користувача, "
        "хеш пароля).\n\n"
        "**Де це зберігається.** У базі даних Postgres на Supabase, захищеній row-level security, тому "
        "читати чи змінювати твої рядки може лише твій власний акаунт.\n\n"
        "**Сторонні сервіси.** Курси валют отримуються з публічних API Frankfurter та Національного банку "
        "України (НБУ). Для цього передаються лише коди валют і дати — жодні особисті дані чи деталі "
        "транзакцій не покидають застосунок.\n\n"
        "**Видалення акаунту.** Самостійне видалення акаунту наразі недоступне в застосунку. Якщо хочеш, "
        "щоб твій акаунт і дані видалили, звернись до людини, яка адмініструє цей застосунок для тебе.\n\n"
        "**Зміни.** Цей опис може оновлюватися з розвитком застосунку — перевіряй сторінку Довідки для "
        "актуальної версії.",
        "**Wer diese App betreibt.** Ledgy wird von PMG (Pyatnychko Media Group) entwickelt und betrieben.\n\n"
        "**Was wir erheben.** Deine E-Mail-Adresse (für den Login), die von dir eingegebenen Transaktionen, "
        "Ersparnis-Einträge, Budgets und eigenen Kategorien sowie grundlegende Kontometadaten (Benutzername, "
        "Passwort-Hash).\n\n"
        "**Wo es gespeichert wird.** In einer Supabase-gehosteten Postgres-Datenbank, geschützt durch "
        "Row-Level-Security, sodass nur dein eigenes Konto deine Zeilen lesen oder ändern kann.\n\n"
        "**Drittanbieterdienste.** Wechselkurse werden von den öffentlichen APIs von Frankfurter und der "
        "Nationalbank der Ukraine (NBU) abgerufen. Dabei werden nur die für die Umrechnung nötigen "
        "Währungscodes und Daten übermittelt — keine persönlichen Daten oder Transaktionsdetails.\n\n"
        "**Kontolöschung.** Eine Selbstbedienungs-Kontolöschung ist in der App noch nicht verfügbar. Wenn du "
        "möchtest, dass dein Konto und deine Daten entfernt werden, wende dich an die Person, die diese App "
        "für dich verwaltet.\n\n"
        "**Änderungen.** Diese Zusammenfassung kann sich mit der Weiterentwicklung der App ändern — schau "
        "auf der Hilfeseite für die aktuelle Version vorbei.",
    )


# =========================================================
# CHARTS
#
# "Soft depth" gradient system (chosen by the user from three prototyped
# directions — flat/restrained, soft depth, vibrant glow): every chart fill
# is a two-stop linear gradient from a lighter tint of its own hue to the
# hue itself, never an unrelated second color. Identity charts (the donut)
# keep each category's own color — only the fill *technique* changed, not
# what a color means. Magnitude-only charts (weekday/merchant/trend) use a
# single brand-hue gradient, matching the sequential-encoding rule (one
# hue, light→dark) rather than inventing a second brand color.
# =========================================================


def _active_brand_color() -> str:
    """The primaryColor for whichever theme (light/dark) is currently
    active, so single-hue chart gradients always match the same blue the
    rest of the UI (buttons, links, the sidebar accent) is using — see
    .streamlit/config.toml for the two values this mirrors. Falls back to
    the light-theme blue if the theme can't be read (e.g. outside a live
    browser session, such as a headless test run).
    """
    try:
        return "#5b8cff" if st.context.theme.type == "dark" else "#1d4ed8"
    except Exception:
        return "#1d4ed8"


def _gradient(base_hex: str, light_amount: float = 0.55, vertical: bool = True, fade_to_transparent: bool = False) -> alt.LinearGradient:
    stop_end = f"{base_hex}00" if fade_to_transparent else base_hex
    x2, y2 = (0, 1) if vertical else (1, 0)
    return alt.LinearGradient(
        gradient="linear", x1=0, y1=0, x2=x2, y2=y2,
        stops=[alt.GradientStop(offset=0, color=base_hex if fade_to_transparent else lighten_hex(base_hex, light_amount)),
               alt.GradientStop(offset=1, color=stop_end)],
    )


def render_donut_chart(cat_df: pd.DataFrame, value_col: str = "display_amount", currency: str = "EUR", category_colors: Optional[Dict[str, str]] = None) -> None:
    """Donut chart with the filtered total in the center — replaces the old
    matplotlib pie chart. Hand-rolled inline SVG rather than a charting
    library: it renders on a transparent background (the matplotlib version
    always painted an opaque white figure background, which looked wrong in
    dark mode — a known issue from the last redesign pass, fixed here for
    free as a side effect rather than patched separately), needs no extra
    dependency, and gives full control over the per-segment gradient and
    the center label.

    `cat_df["category"]` must hold the raw (untranslated) category name —
    colors and the legend both key off it, translating only for display.
    """
    if cat_df.empty or float(cat_df[value_col].sum()) <= 0:
        show_empty(l("Not enough data.", "Недостатньо даних.", "Nicht genug Daten."))
        return

    colors_map = category_colors or CATEGORY_COLORS
    fallback = colors_map.get("Other", CATEGORY_COLORS["Other"])
    total = float(cat_df[value_col].sum())

    size = 220
    cx = cy = size / 2
    r_outer = size / 2 - 6
    r_inner = r_outer * 0.62

    def arc_point(radius: float, angle_deg: float) -> Tuple[float, float]:
        a = math.radians(angle_deg - 90)
        return cx + radius * math.cos(a), cy + radius * math.sin(a)

    def segment_path(r_out: float, r_in: float, a0: float, a1: float, gap_deg: float = 1.4) -> str:
        a0, a1 = a0 + gap_deg, a1 - gap_deg
        if a1 <= a0:
            mid = (a0 + a1) / 2
            a0, a1 = mid - 0.35, mid + 0.35
        large_arc = 1 if (a1 - a0) > 180 else 0
        x0, y0 = arc_point(r_out, a0)
        x1, y1 = arc_point(r_out, a1)
        x2, y2 = arc_point(r_in, a1)
        x3, y3 = arc_point(r_in, a0)
        return (
            f"M {x0:.2f} {y0:.2f} A {r_out:.2f} {r_out:.2f} 0 {large_arc} 1 {x1:.2f} {y1:.2f} "
            f"L {x2:.2f} {y2:.2f} A {r_in:.2f} {r_in:.2f} 0 {large_arc} 0 {x3:.2f} {y3:.2f} Z"
        )

    angle = 0.0
    defs: List[str] = []
    paths: List[str] = []
    legend_rows = []
    for i, row in enumerate(cat_df.itertuples(index=False)):
        name = getattr(row, "category")
        value = float(getattr(row, value_col))
        if value <= 0:
            continue
        base = colors_map.get(name, fallback)
        frac = value / total
        a0, a1 = angle, angle + frac * 360
        angle = a1
        gid = f"donut_grad_{i}"
        defs.append(
            f'<linearGradient id="{gid}" x1="0%" y1="0%" x2="100%" y2="100%">'
            f'<stop offset="0%" stop-color="{lighten_hex(base, 0.5)}"/>'
            f'<stop offset="100%" stop-color="{base}"/>'
            f"</linearGradient>"
        )
        title = f"{lcat(name)}: {format_money(value, currency)} ({frac * 100:.1f}%)"
        paths.append(f'<path d="{segment_path(r_outer, r_inner, a0, a1)}" fill="url(#{gid})" filter="url(#donutShadow)"><title>{title}</title></path>')
        legend_rows.append((name, base, value, frac * 100))

    total_label = format_money(total, currency)
    value_font = 21 if len(total_label) <= 14 else 16
    caption = l("total spent", "усього витрачено", "insgesamt ausgegeben")

    svg = (
        '<div class="donut-wrap"><svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        '<defs><filter id="donutShadow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="1.5" stdDeviation="2.2" flood-opacity="0.18"/></filter>{defs}</defs>'
        "{paths}"
        '<text x="{cx}" y="{cy_val}" text-anchor="middle" class="donut-value" font-size="{vf}" font-family="Inter, sans-serif">{total_label}</text>'
        '<text x="{cx}" y="{cy_cap}" text-anchor="middle" class="donut-caption" font-size="12" font-family="Inter, sans-serif">{caption}</text>'
        "</svg></div>"
    ).format(
        size=size, defs="".join(defs), paths="".join(paths), cx=cx, cy_val=cy - 5, cy_cap=cy + 16,
        vf=value_font, total_label=total_label, caption=caption,
    )
    st.markdown(svg, unsafe_allow_html=True)

    legend_rows.sort(key=lambda r: r[2], reverse=True)
    legend_html = ['<div class="donut-legend">']
    for name, base, value, share_pct in legend_rows:
        legend_html.append(
            f'<div class="donut-legend-row"><span class="donut-swatch" style="background:{base}"></span>'
            f'<span class="donut-legend-name">{lcat(name)}</span>'
            f'<span class="donut-legend-value">{format_money(value, currency)} · {share_pct:.1f}%</span></div>'
        )
    legend_html.append("</div>")
    st.markdown("".join(legend_html), unsafe_allow_html=True)


def gradient_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 220, color: Optional[str] = None, sort: Optional[List[str]] = None) -> None:
    """Single-series magnitude bar chart — one brand-hue gradient (light at
    the top, the theme's primaryColor at the base), rounded bar tops, and a
    hover tooltip. For charts encoding category IDENTITY (not just a single
    measure), use `categorical_gradient_bar_chart` instead — this one
    always uses one hue, on purpose (a magnitude-only chart has no per-bar
    identity to encode, so a gradient per bar here would just be noise).
    """
    base = color or _active_brand_color()
    # Fixed pixel bar width (not left to the band scale's auto-stretch) so a
    # chart with very few bars — one merchant, one weekday with data — gets
    # a normal-looking bar instead of one block stretched across the full
    # container width.
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color=_gradient(base), size=44)
        .encode(
            x=alt.X(f"{x_col}:N", title=x_title, sort=sort, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            tooltip=[alt.Tooltip(f"{x_col}:N", title=x_title or x_col), alt.Tooltip(f"{y_col}:Q", title=y_title or y_col, format=",.2f")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def gradient_area_chart(df: pd.DataFrame, x_col: str, y_col: str, x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 220, color: Optional[str] = None) -> None:
    """Single-series trend chart — smooth line with a gradient fill fading
    from the brand hue to transparent, the standard fintech-app treatment
    for a magnitude-over-time series (Sequential = one hue, per the
    data-viz color rules — never a second, unrelated color for the fill).
    """
    base = color or _active_brand_color()
    # `point=` overlays a small dot per data point — without it, a series
    # with only one x-value (e.g. a single month of history) draws nothing
    # at all: a line/area mark has no width to fill with just one point.
    chart = (
        alt.Chart(df)
        .mark_area(
            interpolate="monotone", line={"color": base, "strokeWidth": 2.5},
            color=_gradient(base, fade_to_transparent=True),
            point=alt.OverlayMarkDef(color=base, size=45, filled=True),
        )
        .encode(
            x=alt.X(f"{x_col}:O", title=x_title),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            tooltip=[alt.Tooltip(f"{x_col}:O", title=x_title or x_col), alt.Tooltip(f"{y_col}:Q", title=y_title or y_col, format=",.2f")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def categorical_gradient_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, category_colors: Dict[str, str], x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 260) -> None:
    """Bar chart where each bar IS a category (e.g. spend per category) —
    every bar gets its own category's color as a light→base gradient, the
    same color that category uses everywhere else in the app (the donut,
    the badges), so a category's identity stays consistent across every
    chart on the dashboard rather than each chart inventing its own hue.

    `df[x_col]` must hold RAW (untranslated) category names — colors are
    looked up by that raw name, same rule as `render_donut_chart` (a past
    bug here, fixed in an earlier pass, was color lookups silently missing
    for every non-English UI language because the field held translated
    text instead). Axis ticks and tooltips are translated for display via a
    generated Vega expression that maps each raw name to `lcat(name)`
    without touching the underlying field the color condition matches on.
    """
    if df.empty:
        show_empty(l("Not enough data.", "Недостатньо даних.", "Nicht genug Daten."))
        return
    domain = list(df[x_col])
    fallback = category_colors.get("Other", CATEGORY_COLORS["Other"])

    def _js_escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("'", "\\'")

    # `axis.labelExpr` runs against `datum.value`; `transform_calculate`
    # runs against `datum.<field>` — same mapping, two different Vega
    # expression contexts, so it's built twice with different datum refs.
    ternary_tail = "".join(f"datum.{{ref}} === '{name}' ? '{_js_escape(lcat(name))}' : " for name in domain)
    label_expr_axis = ternary_tail.format(ref="value") + "datum.value"
    label_expr_calc = ternary_tail.format(ref=x_col) + f"datum.{x_col}"

    # Each bar's fill is a `condition` branch keyed on its own category name
    # (Vega-Lite's scale `range` doesn't accept Gradient objects, so a
    # per-category color SCALE can't carry gradients — a chained `when/then`
    # on the raw field, one branch per category, is the supported way to
    # give each bar its own gradient rather than a flat scale color).
    cond = None
    for name in domain:
        base = category_colors.get(name, fallback)
        predicate = getattr(alt.datum, x_col) == name
        branch = alt.when(predicate) if cond is None else cond.when(predicate)
        cond = branch.then(alt.value(_gradient(base)))
    cond = cond.otherwise(alt.value(_gradient(fallback)))

    chart = (
        alt.Chart(df)
        .transform_calculate(category_label=label_expr_calc)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=44)
        .encode(
            x=alt.X(f"{x_col}:N", title=x_title, sort=domain, axis=alt.Axis(labelAngle=-30, labelExpr=label_expr_axis)),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            color=cond,
            tooltip=[alt.Tooltip("category_label:N", title=x_title or x_col), alt.Tooltip(f"{y_col}:Q", title=y_title or y_col, format=",.2f")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


# =========================================================
# AUTH / SESSION
# =========================================================

def require_login() -> str:
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.info("Please log in first.")
        st.stop()
    return str(user_id)


def restore_session() -> None:
    """Re-attach a previously established Supabase Auth session on this rerun.

    Streamlit re-executes the whole script on every interaction, so the
    module-level `supabase` client starts anonymous each time. If we already
    signed in during an earlier run, replay the saved tokens so RLS-protected
    queries keep carrying the user's identity instead of silently returning
    zero rows.
    """
    if st.session_state.get("user_id"):
        return
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")
    if not access_token or not refresh_token:
        return
    try:
        res = restore_auth_session(access_token, refresh_token)
    except Exception:
        res = None
    if res and res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = get_profile_username(res.user.id) or res.user.email
    else:
        for key in ("access_token", "refresh_token", "user_id", "username"):
            st.session_state.pop(key, None)


def login_user(email: str, password: str) -> tuple[bool, str]:
    email = email.strip()
    if not email or not password:
        return False, t("invalid_credentials")
    try:
        res = sign_in(email, password)
    except Exception:
        return False, t("invalid_credentials")
    if not res.session or not res.user:
        return False, t("invalid_credentials")
    st.session_state.access_token = res.session.access_token
    st.session_state.refresh_token = res.session.refresh_token
    st.session_state.user_id = res.user.id
    st.session_state.username = get_profile_username(res.user.id) or res.user.email
    return True, ""


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    email = email.strip()
    if len(username) < 3:
        return False, l("Username must have at least 3 characters.", "Ім'я користувача має містити щонайменше 3 символи.", "Der Benutzername muss mindestens 3 Zeichen lang sein.")
    if not email or "@" not in email:
        return False, l("Enter a valid email address.", "Введи коректну email-адресу.", "Gib eine gültige E-Mail-Adresse ein.")
    if len(password) < 8 or not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
        return False, l("Password must be at least 8 characters and include a letter and a number.", "Пароль має містити щонайменше 8 символів, літеру та цифру.", "Das Passwort muss mindestens 8 Zeichen sowie einen Buchstaben und eine Zahl enthalten.")
    if username_exists(username):
        return False, l("This username already exists.", "Такий користувач уже існує.", "Dieser Benutzername existiert bereits.")
    try:
        res = sign_up(email, password, username)
    except Exception as exc:
        message = str(exc).lower()
        if "already registered" in message or "already exists" in message or "user_repeated_signup" in message:
            return False, l("This email is already registered.", "Ця email-адреса вже зареєстрована.", "Diese E-Mail-Adresse ist bereits registriert.")
        return False, l("Could not create account. Please try again.", "Не вдалося створити акаунт. Спробуй ще раз.", "Konto konnte nicht erstellt werden. Bitte versuche es erneut.")
    if res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = username
        return True, l("Account created successfully.", "Акаунт успішно створено.", "Konto erfolgreich erstellt.")
    return True, l(
        "Account created. Check your email to confirm it before logging in.",
        "Акаунт створено. Перевір пошту й підтверди його перед входом.",
        "Konto erstellt. Bitte bestätige es per E-Mail, bevor du dich anmeldest.",
    )


def request_password_reset(email: str) -> tuple[bool, str]:
    email = email.strip()
    if not email or "@" not in email:
        return False, l("Enter a valid email address.", "Введи коректну email-адресу.", "Gib eine gültige E-Mail-Adresse ein.")
    try:
        db_request_password_reset(email)
    except Exception:
        pass
    # Deliberately generic regardless of outcome, so this can't be used to
    # probe which email addresses have an account.
    return True, l(
        "If that email is registered, a reset link is on its way.",
        "Якщо ця пошта зареєстрована, лист із посиланням уже надіслано.",
        "Falls diese E-Mail registriert ist, ist ein Reset-Link unterwegs.",
    )


def logout_user() -> None:
    try:
        sign_out()
    except Exception:
        pass
    for key in ("access_token", "refresh_token", "user_id", "username", "must_set_password"):
        st.session_state.pop(key, None)


def consume_email_link() -> None:
    """Handle an invite/recovery/signup-confirmation link the user just clicked.

    Supabase's default email templates redirect with the session tokens after a
    `#`, which never reaches Streamlit's Python side. Our email templates are
    configured (in the Supabase dashboard) to link to `{{ .SiteURL }}?token_hash=
    {{ .TokenHash }}&type=...` instead, which Streamlit *can* read via
    `st.query_params`. We exchange that token_hash for a real session here.
    """
    token_hash = st.query_params.get("token_hash")
    otp_type = st.query_params.get("type")
    if not token_hash or not otp_type or st.session_state.get("user_id"):
        return
    try:
        res = verify_otp(token_hash, otp_type)
    except Exception:
        res = None
    st.query_params.clear()
    if res and res.session and res.user:
        st.session_state.access_token = res.session.access_token
        st.session_state.refresh_token = res.session.refresh_token
        st.session_state.user_id = res.user.id
        st.session_state.username = get_profile_username(res.user.id) or res.user.email
        # Invite/recovery links prove the email is theirs but don't carry a
        # password — make them set one before they can use the app.
        st.session_state.must_set_password = otp_type in ("invite", "recovery")
    else:
        st.session_state["email_link_error"] = l(
            "This link is invalid or has expired. Please request a new one.",
            "Це посилання недійсне або застаріло. Запроси нове.",
            "Dieser Link ist ungültig oder abgelaufen. Bitte fordere einen neuen an.",
        )


def render_set_password_screen() -> None:
    st.title(l("Set your password", "Встанови пароль", "Passwort festlegen"))
    st.caption(l(
        "Choose a password to finish setting up your account.",
        "Обери пароль, щоб завершити налаштування акаунта.",
        "Wähle ein Passwort, um dein Konto einzurichten.",
    ))
    new_password = st.text_input(t("password"), type="password", key="set_pw_new")
    confirm_password = st.text_input(
        l("Confirm password", "Підтвердь пароль", "Passwort bestätigen"), type="password", key="set_pw_confirm"
    )
    if st.button(l("Save password", "Зберегти пароль", "Passwort speichern"), use_container_width=True, type="primary"):
        if len(new_password) < 8 or not (any(c.isalpha() for c in new_password) and any(c.isdigit() for c in new_password)):
            st.error(l(
                "Password must be at least 8 characters and include a letter and a number.",
                "Пароль має містити щонайменше 8 символів, літеру та цифру.",
                "Das Passwort muss mindestens 8 Zeichen sowie einen Buchstaben und eine Zahl enthalten.",
            ))
        elif new_password != confirm_password:
            st.error(l("Passwords don't match.", "Паролі не збігаються.", "Passwörter stimmen nicht überein."))
        else:
            try:
                update_password(new_password)
            except Exception:
                st.error(l("Could not save the password. Please try again.", "Не вдалося зберегти пароль. Спробуй ще раз.", "Passwort konnte nicht gespeichert werden. Bitte versuche es erneut."))
            else:
                st.session_state.must_set_password = False
                st.success(l("Password set. You're all set.", "Пароль встановлено.", "Passwort festgelegt."))
                rerun()
    if st.button(l("Cancel and log out", "Скасувати й вийти", "Abbrechen und abmelden")):
        logout_user()
        rerun()
    st.stop()


# =========================================================
# FX RATES
# =========================================================
# db.get_rates_map is itself @st.cache_data(ttl=3600) now (moved there so
# every caller benefits, including the per-row conversions in
# analytics.enrich_expenses — those were the actual hot path, not the calls
# made directly from view code that this module used to wrap). Re-exported
# under this name since views/*.py already import get_rates_map from here.
get_rates_map = db_get_rates_map


def get_date_range_presets(min_date: date, max_date: date) -> Dict[str, Tuple[date, date]]:
    today = date.today()
    month_start = today.replace(day=1)
    last_30 = max(min_date, today - timedelta(days=29))
    last_90 = max(min_date, today - timedelta(days=89))
    year_start = max(min_date, date(today.year, 1, 1))
    return {
        l("This month", "Цей місяць", "Dieser Monat"): (max(min_date, month_start), max_date),
        l("Last 30 days", "Останні 30 днів", "Letzte 30 Tage"): (last_30, max_date),
        l("Last 90 days", "Останні 90 днів", "Letzte 90 Tage"): (last_90, max_date),
        l("Year to date", "Від початку року", "Jahr bis heute"): (year_start, max_date),
        l("All time", "Увесь час", "Gesamter Zeitraum"): (min_date, max_date),
    }


def generate_smart_insights(expense_df: pd.DataFrame, income_df: pd.DataFrame, savings_df: pd.DataFrame, monthly_limit_display: Optional[float], display_currency: str) -> List[str]:
    insights: List[str] = []
    if expense_df.empty and income_df.empty:
        return [l("Add a few transactions to unlock smart insights.", "Додай кілька транзакцій, щоб відкрити розумні інсайти.", "Füge einige Transaktionen hinzu, um smarte Insights freizuschalten.")]
    if not expense_df.empty:
        cat = category_summary(expense_df, "display_abs_amount")
        if not cat.empty:
            insights.append(
                l(
                    "Top expense category: {category} — {amount}",
                    "Найбільша категорія витрат: {category} — {amount}",
                    "Größte Ausgabenkategorie: {category} — {amount}",
                ).format(category=lcat(cat.iloc[0]["category"]), amount=format_money(cat.iloc[0]["display_abs_amount"], display_currency))
            )
        monthly_spent = safe_float(expense_df[expense_df["month"] == pd.Timestamp.today().strftime("%Y-%m")]["display_abs_amount"].sum())
        if monthly_limit_display and monthly_limit_display > 0:
            usage = monthly_spent / monthly_limit_display
            if usage > 1:
                insights.append(l("You are over budget this month.", "Цього місяця ти перевищив бюджет.", "Diesen Monat liegst du über dem Budget."))
            elif usage > 0.85:
                insights.append(l("You are getting close to your monthly budget cap.", "Ти наближаєшся до місячного ліміту бюджету.", "Du näherst dich deinem monatlichen Budgetlimit."))
    if not income_df.empty and not expense_df.empty:
        net = safe_float(income_df["display_abs_amount"].sum()) - safe_float(expense_df["display_abs_amount"].sum())
        insights.append(
            l("Net balance for current filter: {amount}", "Чистий баланс для поточного фільтра: {amount}", "Nettosaldo für den aktuellen Filter: {amount}").format(amount=format_money(net, display_currency))
        )
    if not savings_df.empty:
        total_saved = safe_float(savings_df["saved"].sum())
        total_target = safe_float(savings_df["target"].sum())
        if total_target > 0:
            insights.append(
                l("Savings goals progress: {pct:.1f}% complete.", "Прогрес цілей заощаджень: {pct:.1f}% виконано.", "Fortschritt der Sparziele: {pct:.1f}% erreicht.").format(pct=(total_saved / total_target) * 100)
            )
    return insights[:4]


# =========================================================
# TRANSLATIONS
# =========================================================

TRANSLATIONS = {
    "en": {
        "app_title": "Ledgy",
        "sidebar_title": "Ledgy",
        "sidebar_caption": "Clarity for your everyday spending.",
        "language": "Language",
        "logged_in_as": "Logged in as {username}",
        "log_out": "Log out",
        "mode": "Mode",
        "login": "Login",
        "register": "Register",
        "forgot_password": "Forgot password",
        "username": "Username",
        "email": "Email",
        "password": "Password",
        "create_account": "Create account",
        "send_reset_link": "Send reset link",
        "invalid_credentials": "Invalid email or password.",
        "welcome_text": "One place for spending, subscriptions, savings, and the patterns behind them.",
        "fast_capture": "Fast capture",
        "quick_add": "Quick Add",
        "quick_add_desc": "Paste natural text like: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Smarter insights",
        "analytics_plus": "Analytics+",
        "analytics_plus_desc": "Forecasts, duplicates, anomalies, merchants, streaks",
        "safe_data": "Safer data",
        "bulk_tools": "Bulk tools",
        "bulk_tools_desc": "CSV import, template export, backup-ready downloads",
        "display_currency": "Display currency",
        "fx_caption": "Live FX rates via Frankfurter + NBU",
        "global_filters": "Global filters",
        "quick_range": "Quick range",
        "from": "From",
        "to": "To",
        "categories": "Categories",
        "search_text": "Search text",
        "search_placeholder": "merchant, note, category",
        "subscriptions_only": "Subscriptions only",
        "show_full_history": "Load full history",
        "show_full_history_help": "By default only the last {days} days load, to keep the app fast. Turn this on to include older transactions (search, edit, and charts will include everything, but rendering may be slower).",
        "navigation": "Navigation",
        "nav_group_overview": "Overview",
        "nav_group_add": "Add",
        "nav_group_manage": "Manage",
        "nav_group_insights": "Insights",
        "nav_group_more": "More",
        "dashboard": "Dashboard",
        "add_expense": "Add Expense",
        "manage_expenses": "Manage Expenses",
        "subscriptions": "Subscriptions",
        "savings": "Savings",
        "analytics": "Analytics",
        "import_export": "Import / Export",
        "categories_page": "Categories",
        "help_page": "Help & Privacy",
        "filtered_transactions": "filtered transactions",
        "top_category": "Top category",
        "largest_expense": "Largest expense",
        "savings_rate": "Savings rate",
        "health_score": "Health score",
        "budget": "Budget",
        "saving": "Saving",
        "consistency": "Consistency",
        "footer_text": "Ledgy · built by PMG (Pyatnychko Media Group), est. 2026",
        "privacy_agree": "I've read and agree to the Privacy Policy",
        "privacy_agree_required": "Please confirm you've read the Privacy Policy before creating an account.",
        "privacy_policy_expander": "Read the Privacy Policy",
    },
    "uk": {
        "app_title": "Ledgy",
        "sidebar_title": "Ledgy",
        "sidebar_caption": "Ясність у щоденних витратах.",
        "language": "Мова",
        "logged_in_as": "Ви увійшли як {username}",
        "log_out": "Вийти",
        "mode": "Режим",
        "login": "Увійти",
        "register": "Реєстрація",
        "forgot_password": "Забув пароль",
        "username": "Ім'я користувача",
        "email": "Email",
        "password": "Пароль",
        "create_account": "Створити акаунт",
        "send_reset_link": "Надіслати посилання",
        "invalid_credentials": "Неправильний email або пароль.",
        "welcome_text": "Один простір для витрат, підписок, заощаджень і закономірностей між ними.",
        "fast_capture": "Швидке внесення",
        "quick_add": "Швидке додавання",
        "quick_add_desc": "Встав текст у стилі: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Розумні інсайти",
        "analytics_plus": "Аналітика+",
        "analytics_plus_desc": "Прогнози, дублікати, аномалії, продавці, streaks",
        "safe_data": "Безпечні дані",
        "bulk_tools": "Масові інструменти",
        "bulk_tools_desc": "CSV імпорт, шаблон експорту, резервні копії",
        "display_currency": "Валюта відображення",
        "fx_caption": "Актуальні курси через Frankfurter + NBU",
        "global_filters": "Глобальні фільтри",
        "quick_range": "Швидкий період",
        "from": "Від",
        "to": "До",
        "categories": "Категорії",
        "search_text": "Пошук",
        "search_placeholder": "продавець, нотатка, категорія",
        "subscriptions_only": "Лише підписки",
        "show_full_history": "Завантажити всю історію",
        "show_full_history_help": "За замовчуванням завантажуються лише останні {days} днів, щоб застосунок працював швидко. Увімкни, щоб включити старіші транзакції (пошук, редагування й графіки враховуватимуть усе, але може працювати повільніше).",
        "navigation": "Навігація",
        "nav_group_overview": "Огляд",
        "nav_group_add": "Додати",
        "nav_group_manage": "Керування",
        "nav_group_insights": "Аналітика",
        "nav_group_more": "Ще",
        "dashboard": "Дашборд",
        "add_expense": "Додати витрату",
        "manage_expenses": "Керування витратами",
        "subscriptions": "Підписки",
        "savings": "Заощадження",
        "analytics": "Аналітика",
        "import_export": "Імпорт / Експорт",
        "categories_page": "Категорії",
        "help_page": "Довідка й приватність",
        "filtered_transactions": "відфільтрованих транзакцій",
        "top_category": "Топ категорія",
        "largest_expense": "Найбільша витрата",
        "savings_rate": "Норма заощаджень",
        "health_score": "Фінансовий рейтинг",
        "budget": "Бюджет",
        "saving": "Заощадження",
        "consistency": "Стабільність",
        "footer_text": "Ledgy · створено PMG (Pyatnychko Media Group), 2026",
        "privacy_agree": "Я прочитав(-ла) і погоджуюсь з Політикою конфіденційності",
        "privacy_agree_required": "Будь ласка, підтверди, що прочитав(-ла) Політику конфіденційності, перш ніж створювати акаунт.",
        "privacy_policy_expander": "Прочитати Політику конфіденційності",
    },
    "de": {
        "app_title": "Ledgy",
        "sidebar_title": "Ledgy",
        "sidebar_caption": "Klarheit für deine täglichen Ausgaben.",
        "language": "Sprache",
        "logged_in_as": "Angemeldet als {username}",
        "log_out": "Abmelden",
        "mode": "Modus",
        "login": "Anmelden",
        "register": "Registrieren",
        "forgot_password": "Passwort vergessen",
        "username": "Benutzername",
        "email": "E-Mail",
        "password": "Passwort",
        "create_account": "Konto erstellen",
        "send_reset_link": "Link senden",
        "invalid_credentials": "Ungültige E-Mail-Adresse oder ungültiges Passwort.",
        "welcome_text": "Ein Ort für Ausgaben, Abos, Ersparnisse und die Muster dahinter.",
        "fast_capture": "Schnelle Erfassung",
        "quick_add": "Schnell hinzufügen",
        "quick_add_desc": "Natürlichen Text einfügen wie: 2026-03-17 8.5 EUR coffee",
        "smart_insights": "Smarte Insights",
        "analytics_plus": "Analytics+",
        "analytics_plus_desc": "Prognosen, Duplikate, Anomalien, Händler, Streaks",
        "safe_data": "Sichere Daten",
        "bulk_tools": "Bulk-Tools",
        "bulk_tools_desc": "CSV-Import, Vorlagenexport, Backup-Downloads",
        "display_currency": "Anzeigewährung",
        "fx_caption": "Live-Wechselkurse via Frankfurter + NBU",
        "global_filters": "Globale Filter",
        "quick_range": "Schnellbereich",
        "from": "Von",
        "to": "Bis",
        "categories": "Kategorien",
        "search_text": "Suche",
        "search_placeholder": "Händler, Notiz, Kategorie",
        "subscriptions_only": "Nur Abos",
        "show_full_history": "Vollständige Historie laden",
        "show_full_history_help": "Standardmäßig werden nur die letzten {days} Tage geladen, damit die App schnell bleibt. Aktiviere dies, um ältere Transaktionen einzubeziehen (Suche, Bearbeitung und Diagramme berücksichtigen dann alles, das Laden kann aber langsamer sein).",
        "navigation": "Navigation",
        "nav_group_overview": "Übersicht",
        "nav_group_add": "Hinzufügen",
        "nav_group_manage": "Verwalten",
        "nav_group_insights": "Analysen",
        "nav_group_more": "Mehr",
        "dashboard": "Dashboard",
        "add_expense": "Ausgabe hinzufügen",
        "manage_expenses": "Ausgaben verwalten",
        "subscriptions": "Abos",
        "savings": "Sparen",
        "analytics": "Analysen",
        "import_export": "Import / Export",
        "categories_page": "Kategorien",
        "help_page": "Hilfe & Datenschutz",
        "filtered_transactions": "gefilterte Transaktionen",
        "top_category": "Top-Kategorie",
        "largest_expense": "Größte Ausgabe",
        "savings_rate": "Sparquote",
        "health_score": "Finanz-Score",
        "budget": "Budget",
        "saving": "Sparen",
        "consistency": "Konstanz",
        "footer_text": "Ledgy · entwickelt von PMG (Pyatnychko Media Group), gegr. 2026",
        "privacy_agree": "Ich habe die Datenschutzerklärung gelesen und stimme zu",
        "privacy_agree_required": "Bitte bestätige, dass du die Datenschutzerklärung gelesen hast, bevor du ein Konto erstellst.",
        "privacy_policy_expander": "Datenschutzerklärung lesen",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("lang", "en")
    template = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def l(en: str, uk: str, de: str) -> str:
    lang = st.session_state.get("lang", "en")
    return {"en": en, "uk": uk, "de": de}.get(lang, en)


def lcat(category: str) -> str:
    lang = st.session_state.get("lang", "en")
    if lang == "en":
        return str(category)
    return CATEGORY_TRANSLATIONS.get(str(category), {}).get(lang, str(category))


def ltx(tx_type: str) -> str:
    mapping = {
        "expense": l("Expense", "Витрата", "Ausgabe"),
        "income": l("Income", "Дохід", "Einnahme"),
    }
    return mapping.get(str(tx_type).lower(), str(tx_type).title())


def lrec(recurrence: str) -> str:
    mapping = {
        "weekly": l("Weekly", "Щотижня", "Wöchentlich"),
        "monthly": l("Monthly", "Щомісяця", "Monatlich"),
        "yearly": l("Yearly", "Щорічно", "Jährlich"),
    }
    return mapping.get(str(recurrence).lower(), str(recurrence).title())
