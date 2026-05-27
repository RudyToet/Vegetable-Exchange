"""
Vegetable Exchange — markttracker voor verse groenten, iPhone-Aandelen stijl.
Dark mode, donkergroen, sparklines, KNMI-weeroverlay.
"""
import re
import zipfile
from datetime import datetime, timedelta, date
from typing import Optional

import altair as alt
import pandas as pd
import requests
import streamlit as st

# ============================================================================
# CONFIG
# ============================================================================
st.set_page_config(
    page_title="Vegetable Exchange",
    page_icon="🥬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Dark green palette — iOS Aandelen vibe
BG = "#04130C"
BG_CARD = "#0B2418"
BORDER = "#163828"
TEXT = "#F2F4F0"
TEXT_DIM = "#7C9489"
UP = "#30D158"
DOWN = "#FF453A"
ACCENT = "#5EEAA8"
SUN = "#FFB627"

DUTCH_WD = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
DUTCH_MO = ["januari", "februari", "maart", "april", "mei", "juni",
            "juli", "augustus", "september", "oktober", "november", "december"]
DUTCH_MO_SHORT = ["jan", "feb", "mrt", "apr", "mei", "jun",
                  "jul", "aug", "sep", "okt", "nov", "dec"]

# ============================================================================
# STYLE
# ============================================================================
st.markdown(f"""
<style>
  .stApp {{ background: {BG}; color: {TEXT}; }}
  .main .block-container {{
    padding-top: 1rem; padding-bottom: 5rem; max-width: 540px;
  }}
  #MainMenu, footer {{visibility: hidden;}}
  header[data-testid="stHeader"] {{ background: transparent; }}

  .ve-brand {{
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 4px 4px 8px 4px;
    border-bottom: 0.5px solid {BORDER};
    margin-bottom: 4px;
  }}
  .ve-brand-title {{
    font-size: 28px; font-weight: 800; letter-spacing: -0.02em;
    color: {TEXT}; margin: 0; line-height: 1;
  }}
  .ve-brand-sub {{
    font-size: 11px; color: {TEXT_DIM};
    font-variant-numeric: tabular-nums; text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .ticker {{
    display: flex; align-items: center; padding: 14px 6px;
    border-bottom: 0.5px solid {BORDER}; gap: 12px;
  }}
  .ticker:last-child {{ border-bottom: none; }}
  .ticker-name {{ flex: 0 0 38%; min-width: 0; }}
  .ticker-name .cat {{
    font-size: 16px; font-weight: 600; color: {TEXT};
    line-height: 1.15; text-transform: capitalize;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .ticker-name .meta {{
    font-size: 11px; color: {TEXT_DIM}; margin-top: 2px;
  }}
  .ticker-spark {{
    flex: 0 0 28%; display: flex; justify-content: center; align-items: center;
  }}
  .ticker-price {{ flex: 1; text-align: right; min-width: 0; }}
  .ticker-price .price {{
    font-size: 16px; font-weight: 600; color: {TEXT};
    font-variant-numeric: tabular-nums; line-height: 1.15;
  }}
  .pill {{
    display: inline-block; padding: 3px 7px; border-radius: 5px;
    font-size: 12px; font-weight: 700; margin-top: 4px;
    min-width: 56px; text-align: center;
    font-variant-numeric: tabular-nums;
  }}
  .pill-up   {{ background: {UP};   color: #032714; }}
  .pill-down {{ background: {DOWN}; color: #2A0A09; }}
  .pill-flat {{ background: {BORDER}; color: {TEXT_DIM}; }}

  .ve-section {{
    font-size: 11px; font-weight: 700; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-top: 18px; margin-bottom: 4px; padding: 0 4px;
  }}

  .detail-cat {{
    font-size: 12px; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 12px;
  }}
  .detail-price {{
    font-size: 44px; font-weight: 700; color: {TEXT};
    line-height: 1.1; font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em; margin-top: 2px;
  }}
  .detail-change {{
    font-size: 15px; font-weight: 600; margin-top: 2px;
    font-variant-numeric: tabular-nums;
  }}
  .detail-change-up   {{ color: {UP}; }}
  .detail-change-down {{ color: {DOWN}; }}

  .stat-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    border-top: 0.5px solid {BORDER}; margin-top: 16px;
  }}
  .stat {{ padding: 12px 6px; border-bottom: 0.5px solid {BORDER}; }}
  .stat-label {{
    font-size: 11px; color: {TEXT_DIM};
    text-transform: uppercase; letter-spacing: 0.05em;
  }}
  .stat-value {{
    font-size: 16px; font-weight: 600; color: {TEXT};
    margin-top: 2px; font-variant-numeric: tabular-nums;
  }}

  .stTabs [data-baseweb="tab-list"] {{
    background: {BG}; border-bottom: 0.5px solid {BORDER}; gap: 0;
  }}
  .stTabs [data-baseweb="tab"] {{
    background: transparent; color: {TEXT_DIM};
    font-weight: 600; font-size: 13px; padding: 10px 14px;
  }}
  .stTabs [aria-selected="true"] {{
    color: {ACCENT} !important; background: transparent !important;
  }}
  .stTabs [data-baseweb="tab-highlight"] {{ background: {ACCENT}; }}

  .stSelectbox > div > div {{
    background: {BG_CARD}; border-color: {BORDER}; color: {TEXT};
  }}
  .stRadio > div {{
    background: {BG_CARD}; border-radius: 8px; padding: 4px; gap: 0;
  }}
  .stRadio label {{ color: {TEXT_DIM}; font-size: 12px; font-weight: 600; }}

  .streamlit-expanderHeader {{
    background: {BG_CARD}; border: 0.5px solid {BORDER};
    border-radius: 8px; color: {TEXT_DIM}; font-size: 13px;
  }}

  .alert-row {{
    background: {BG_CARD}; border: 0.5px solid {BORDER};
    border-radius: 10px; padding: 14px; margin-bottom: 8px;
  }}
  .alert-row .a-cat {{
    font-size: 15px; font-weight: 600;
    text-transform: capitalize; color: {TEXT};
  }}
  .alert-row .a-change {{
    font-size: 22px; font-weight: 700;
    font-variant-numeric: tabular-nums; margin-top: 4px;
  }}
  .alert-row .a-meta {{
    font-size: 11px; color: {TEXT_DIM}; margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPERS
# ============================================================================
def fmt_eur(v, decimals=2):
    if pd.isna(v):
        return "—"
    return f"€{v:.{decimals}f}".replace(".", ",")


def fmt_pct(v, decimals=1):
    if pd.isna(v):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{decimals}f}%"


def fmt_dutch_date(d):
    if not isinstance(d, datetime):
        d = pd.Timestamp(d).to_pydatetime()
    return f"{DUTCH_WD[d.weekday()]} {d.day} {DUTCH_MO[d.month - 1]}"


def fmt_dutch_short(d):
    if not isinstance(d, datetime):
        d = pd.Timestamp(d).to_pydatetime()
    return f"{d.day} {DUTCH_MO_SHORT[d.month - 1]}"


def sparkline_svg(values, width=110, height=28, color=UP):
    vals = [v for v in values if v is not None and not pd.isna(v)]
    if len(vals) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin:
        vmax = vmin + 0.01
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = i * width / (n - 1)
        y = height - 2 - ((v - vmin) / (vmax - vmin)) * (height - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M " + " L ".join(pts)
    last_x, last_y = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="2" fill="{color}"/>'
        f'</svg>'
    )


# ============================================================================
# PARSER
# ============================================================================
def parse_chat(text):
    msg_pattern = re.compile(r"\[(\d{2})-(\d{2})-(\d{4}), \d{2}:\d{2}:\d{2}\]")
    date_re = re.compile(r"\b(ma|di|wo|do|vr|za|zo)\s+(\d{2})-(\d{2})\b")
    price_re = re.compile(r"^(.*?):\s*([0-9]+\.[0-9]+)\s*-\s*([0-9]+\.[0-9]+)\s*$")

    positions = [(m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3)))
                 for m in msg_pattern.finditer(text)]
    rows = []
    for i, (pos, d, mo, y) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[pos:end]
        lines = [ln.strip() for ln in body.split("\n")]
        header = None
        header_idx = None
        for idx, line in enumerate(lines):
            if line.startswith("[") or ":" in line:
                continue
            if date_re.search(line):
                header = line
                header_idx = idx
                break
        if header is None:
            continue
        cat = None
        h = header.lower()
        if h.startswith("trostomaat"):
            cat = "trostomaat"
        elif h.startswith("tomaat los"):
            cat = "tomaat los"
        elif h.startswith("troscherrytomaat firenze") or "firenze" in h:
            cat = "firenze"
        elif h.startswith("komkommer"):
            cat = "komkommer"
        elif h.startswith("paprika"):
            parts = h.split()
            if len(parts) >= 2:
                cat = f"paprika {parts[1]}"
        elif h.startswith("aubergine"):
            cat = "aubergine"
        if cat is None:
            continue
        for line in lines[header_idx + 1:]:
            if not line or line.startswith("["):
                continue
            m = price_re.match(line)
            if not m:
                continue
            try:
                low = float(m.group(2))
                high = float(m.group(3))
            except ValueError:
                continue
            rows.append({
                "date": datetime(y, mo, d),
                "category": cat,
                "size": m.group(1).strip(),
                "low": low, "high": high, "mid": (low + high) / 2,
            })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def parse_cached(text):
    return parse_chat(text)


def read_uploaded(uploaded):
    if uploaded.name.lower().endswith(".zip"):
        with zipfile.ZipFile(uploaded) as z:
            txt = [n for n in z.namelist() if n.lower().endswith(".txt")]
            if not txt:
                return ""
            with z.open(txt[0]) as f:
                return f.read().decode("utf-8", errors="replace")
    return uploaded.read().decode("utf-8", errors="replace")


# ============================================================================
# KNMI WEATHER — De Bilt (station 260)
# ============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_knmi(start_d, end_d):
    """Sunshine (SQ), mean temp (TG), precipitation (RH) from KNMI."""
    try:
        r = requests.post(
            "https://www.daggegevens.knmi.nl/klimatologie/daggegevens",
            data={
                "start": start_d.strftime("%Y%m%d"),
                "end": end_d.strftime("%Y%m%d"),
                "vars": "SQ:TG:RH",
                "stns": "260",
            },
            headers={"User-Agent": "vegetable-exchange/1.0"},
            timeout=20,
        )
        r.raise_for_status()
        records = []
        for ln in r.text.split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 5:
                continue
            try:
                _, yyyymmdd, sq, tg, rh = parts[:5]
                records.append({
                    "date": pd.to_datetime(yyyymmdd, format="%Y%m%d"),
                    "sunshine_h": (float(sq) / 10) if sq else None,
                    "temp_c": (float(tg) / 10) if tg else None,
                    "rain_mm": (max(0.0, float(rh)) / 10) if rh else None,
                })
            except (ValueError, IndexError):
                continue
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()


# ============================================================================
# HEADER
# ============================================================================
now = datetime.now()
st.markdown(f"""
<div class="ve-brand">
  <div class="ve-brand-title">Vegetable Exchange</div>
  <div class="ve-brand-sub">{fmt_dutch_short(now)} · {now.strftime('%H:%M')}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# UPLOAD
# ============================================================================
with st.expander("⚙️ Update marktdata", expanded="df" not in st.session_state):
    uploaded = st.file_uploader(
        "WhatsApp-export (.zip of .txt)",
        type=["zip", "txt"], label_visibility="collapsed",
    )
    if uploaded is not None:
        text = read_uploaded(uploaded)
        if not text:
            st.error("Geen .txt in de ZIP.")
            st.stop()
        with st.spinner("Verwerken..."):
            st.session_state.df = parse_cached(text)

if "df" not in st.session_state:
    st.info("Upload eerst de WhatsApp-export om te starten.")
    st.stop()

df = st.session_state.df
if df.empty:
    st.error("Geen prijzen herkend.")
    st.stop()

# ============================================================================
# DERIVED — daily category mid prices
# ============================================================================
cat_daily = (df.groupby(["date", "category"])["mid"]
               .mean().reset_index().sort_values(["category", "date"]))
categories = sorted(df["category"].unique())
latest_date = df["date"].max()


def cat_on(cat, d):
    sub = cat_daily[(cat_daily["category"] == cat) & (cat_daily["date"] == d)]
    return float(sub["mid"].iloc[0]) if len(sub) else float("nan")


def prev_date_for(cat, ref):
    sub = cat_daily[(cat_daily["category"] == cat) & (cat_daily["date"] < ref)]["date"]
    return sub.max() if len(sub) else None


# ============================================================================
# TABS
# ============================================================================
tab_markt, tab_detail, tab_yoy, tab_alerts = st.tabs(["Markt", "Detail", "YoY", "Alerts"])

# ---------- MARKT ----------
with tab_markt:
    st.markdown(
        f'<div class="ve-section">Markt — {fmt_dutch_date(latest_date)}</div>',
        unsafe_allow_html=True,
    )
    rows_html = []
    for cat in categories:
        cur_mid = cat_on(cat, latest_date)
        if pd.isna(cur_mid):
            continue
        prev_d = prev_date_for(cat, latest_date)
        if prev_d is not None:
            prev_mid = cat_on(cat, prev_d)
            change_pct = (cur_mid - prev_mid) / prev_mid * 100 if prev_mid else 0
        else:
            change_pct = 0

        cutoff = latest_date - timedelta(days=30)
        spark_df = cat_daily[(cat_daily["category"] == cat) & (cat_daily["date"] >= cutoff)]
        spark_vals = spark_df["mid"].tolist()
        if len(spark_vals) >= 2:
            spark_color = UP if (spark_vals[-1] - spark_vals[0]) >= 0 else DOWN
        else:
            spark_color = TEXT_DIM
        spark_svg = sparkline_svg(spark_vals, color=spark_color)

        if abs(change_pct) < 0.5:
            pill_class = "pill-flat"
        elif change_pct > 0:
            pill_class = "pill-up"
        else:
            pill_class = "pill-down"
        n_sort = len(df[(df["category"] == cat) & (df["date"] == latest_date)])
        rows_html.append(f"""
        <div class="ticker">
          <div class="ticker-name">
            <div class="cat">{cat}</div>
            <div class="meta">{n_sort} sortering{'en' if n_sort != 1 else ''}</div>
          </div>
          <div class="ticker-spark">{spark_svg}</div>
          <div class="ticker-price">
            <div class="price">{fmt_eur(cur_mid)}</div>
            <div class="pill {pill_class}">{fmt_pct(change_pct)}</div>
          </div>
        </div>
        """)
    st.markdown("".join(rows_html), unsafe_allow_html=True)
    st.markdown(
        f'<div class="ve-section">Dataset</div>'
        f'<div style="color:{TEXT_DIM};font-size:12px;padding:0 4px;">'
        f'{len(df):,} prijzen · {df["date"].nunique()} handelsdagen · '
        f'{df["date"].min().strftime("%d-%m-%Y")} t/m {df["date"].max().strftime("%d-%m-%Y")}'
        f'</div>'.replace(",", "."),
        unsafe_allow_html=True,
    )

# ---------- DETAIL ----------
with tab_detail:
    cat_sel = st.selectbox(
        "Product", categories,
        index=categories.index("paprika rood") if "paprika rood" in categories else 0,
        label_visibility="collapsed",
    )
    period = st.radio(
        "Periode", ["1W", "1M", "3M", "6M", "YTD", "1J", "ALL"],
        index=2, horizontal=True, label_visibility="collapsed",
    )
    cat_data = cat_daily[cat_daily["category"] == cat_sel].sort_values("date").copy()
    if len(cat_data) == 0:
        st.warning("Geen data voor dit product.")
        st.stop()
    last_d = cat_data["date"].max()
    if period == "1W":
        start_d = last_d - timedelta(days=7)
    elif period == "1M":
        start_d = last_d - timedelta(days=30)
    elif period == "3M":
        start_d = last_d - timedelta(days=90)
    elif period == "6M":
        start_d = last_d - timedelta(days=180)
    elif period == "YTD":
        start_d = datetime(last_d.year, 1, 1)
    elif period == "1J":
        start_d = last_d - timedelta(days=365)
    else:
        start_d = cat_data["date"].min()

    period_df = cat_data[cat_data["date"] >= start_d].copy()
    cur_mid = period_df["mid"].iloc[-1] if len(period_df) else float("nan")
    first_mid = period_df["mid"].iloc[0] if len(period_df) else float("nan")
    period_delta = (cur_mid - first_mid) if pd.notna(cur_mid) and pd.notna(first_mid) else 0
    period_pct = (period_delta / first_mid * 100) if first_mid else 0
    change_class = "detail-change-up" if period_delta >= 0 else "detail-change-down"
    sign = "+" if period_delta >= 0 else ""

    st.markdown(f"""
    <div class="detail-cat">{cat_sel}</div>
    <div class="detail-price">{fmt_eur(cur_mid)}</div>
    <div class="detail-change {change_class}">
      {sign}{fmt_eur(period_delta).replace('€','')} ({fmt_pct(period_pct, 2)}) · {period}
    </div>
    """, unsafe_allow_html=True)

    show_weather = st.toggle("☀️ KNMI zonneschijn overlay", value=True)
    knmi_df = pd.DataFrame()
    if show_weather:
        with st.spinner("KNMI..."):
            knmi_df = fetch_knmi(start_d.date(), last_d.date())

    color_line = UP if period_delta >= 0 else DOWN
    base = alt.Chart(period_df).encode(
        x=alt.X("date:T", axis=alt.Axis(
            labelColor=TEXT_DIM, tickColor=BORDER, domainColor=BORDER,
            grid=False, title=None, format="%d %b",
        )),
    )
    price_line = base.mark_line(strokeWidth=2.2, color=color_line).encode(
        y=alt.Y("mid:Q", axis=alt.Axis(
            labelColor=TEXT_DIM, tickColor=BORDER, domainColor=BORDER,
            gridColor=BORDER, gridOpacity=0.3, title="€", titleColor=TEXT_DIM,
            format=".2f",
        )),
        tooltip=[
            alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"),
            alt.Tooltip("mid:Q", title="Prijs", format=".2f"),
        ],
    )
    if show_weather and not knmi_df.empty:
        sun_bars = alt.Chart(knmi_df).mark_bar(
            color=SUN, opacity=0.22, size=4,
        ).encode(
            x="date:T",
            y=alt.Y("sunshine_h:Q", axis=alt.Axis(
                labelColor=SUN, tickColor=BORDER, domainColor=BORDER,
                gridOpacity=0, title="zon (uur)", titleColor=SUN, orient="right",
            )),
            tooltip=[
                alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"),
                alt.Tooltip("sunshine_h:Q", title="Zonuren", format=".1f"),
                alt.Tooltip("temp_c:Q", title="Temp °C", format=".1f"),
                alt.Tooltip("rain_mm:Q", title="Neerslag mm", format=".1f"),
            ],
        )
        chart = alt.layer(sun_bars, price_line).resolve_scale(y="independent")
    else:
        chart = price_line
    chart = chart.properties(
        height=240, background=BG,
        padding={"left": 0, "right": 0, "top": 4, "bottom": 0},
    ).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # Stats grid
    if len(period_df) > 0:
        pmin = period_df["mid"].min()
        pmax = period_df["mid"].max()
        pavg = period_df["mid"].mean()
        try:
            yoy_start = start_d - pd.DateOffset(years=1)
            yoy_end = last_d - pd.DateOffset(years=1)
            yoy_df = cat_data[(cat_data["date"] >= yoy_start) & (cat_data["date"] <= yoy_end)]
            yoy_avg = yoy_df["mid"].mean() if len(yoy_df) else float("nan")
        except Exception:
            yoy_avg = float("nan")
        if pd.notna(yoy_avg) and yoy_avg:
            yoy_pct_val = (pavg - yoy_avg) / yoy_avg * 100
            yoy_val = f"{fmt_eur(yoy_avg)} ({fmt_pct(yoy_pct_val, 0)})"
        else:
            yoy_val = "—"

        weather_stats = ""
        if show_weather and not knmi_df.empty:
            sun_total = knmi_df["sunshine_h"].sum()
            temp_avg = knmi_df["temp_c"].mean()
            rain_total = knmi_df["rain_mm"].sum()
            weather_stats = f"""
            <div class="stat">
              <div class="stat-label">Zon totaal</div>
              <div class="stat-value">{sun_total:.0f} uur</div>
            </div>
            <div class="stat">
              <div class="stat-label">Temp gem</div>
              <div class="stat-value">{temp_avg:.1f} °C</div>
            </div>
            <div class="stat">
              <div class="stat-label">Neerslag</div>
              <div class="stat-value">{rain_total:.0f} mm</div>
            </div>
            <div class="stat"></div>
            """
        st.markdown(f"""
        <div class="stat-grid">
          <div class="stat">
            <div class="stat-label">Laag {period}</div>
            <div class="stat-value">{fmt_eur(pmin)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Hoog {period}</div>
            <div class="stat-value">{fmt_eur(pmax)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Gem {period}</div>
            <div class="stat-value">{fmt_eur(pavg)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">YoY vorig jaar</div>
            <div class="stat-value">{yoy_val}</div>
          </div>
          {weather_stats}
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Per sortering — laatste dag"):
        sub = df[(df["category"] == cat_sel) & (df["date"] == latest_date)].sort_values("size")
        for _, row in sub.iterrows():
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                f"border-bottom:0.5px solid {BORDER};color:{TEXT};font-size:14px;'>"
                f"<span>{row['size']}</span>"
                f"<span style='font-variant-numeric:tabular-nums;'>"
                f"{fmt_eur(row['low'])} – {fmt_eur(row['high'])}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ---------- YOY ----------
with tab_yoy:
    df_y = df.copy()
    df_y["year"] = df_y["date"].dt.year
    df_y["month"] = df_y["date"].dt.month
    years = sorted(df_y["year"].unique())
    if len(years) < 2:
        st.info("Minimaal 2 jaar data nodig.")
    else:
        cat_y = st.selectbox(
            "Product", categories,
            index=categories.index("paprika rood") if "paprika rood" in categories else 0,
            label_visibility="collapsed", key="yoy_cat",
        )
        cat_data_y = df_y[df_y["category"] == cat_y]
        monthly = (cat_data_y.groupby(["year", "month"])["mid"].mean().reset_index())
        monthly["month_name"] = monthly["month"].apply(lambda m: DUTCH_MO_SHORT[m - 1])
        chart = (
            alt.Chart(monthly)
            .mark_bar(cornerRadius=2)
            .encode(
                x=alt.X("month_name:N", sort=DUTCH_MO_SHORT,
                        axis=alt.Axis(labelColor=TEXT_DIM, tickColor=BORDER,
                                      domainColor=BORDER, title=None)),
                y=alt.Y("mid:Q",
                        axis=alt.Axis(labelColor=TEXT_DIM, tickColor=BORDER,
                                      domainColor=BORDER, gridColor=BORDER,
                                      gridOpacity=0.3, title="€", titleColor=TEXT_DIM)),
                color=alt.Color("year:O", title="Jaar",
                                scale=alt.Scale(range=["#1F6D45", "#5EEAA8", "#A8F3CB"])),
                xOffset="year:O",
                tooltip=["year:O", "month_name:N", alt.Tooltip("mid:Q", format=".2f")],
            )
            .properties(height=300, background=BG)
            .configure_view(stroke=None)
            .configure_legend(labelColor=TEXT_DIM, titleColor=TEXT_DIM,
                              orient="top", direction="horizontal")
        )
        st.altair_chart(chart, use_container_width=True)
        pivot = monthly.pivot(index="month", columns="year", values="mid").round(2)
        pivot.index = [DUTCH_MO_SHORT[m - 1] for m in pivot.index]
        if pivot.shape[1] >= 2:
            y_prev, y_cur = pivot.columns[-2], pivot.columns[-1]
            pivot["YoY %"] = ((pivot[y_cur] - pivot[y_prev]) / pivot[y_prev] * 100).round(0)
        st.dataframe(pivot, use_container_width=True)

# ---------- ALERTS ----------
with tab_alerts:
    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider("Drempel %", 5, 50, 15, step=5)
    with col2:
        window_label = st.selectbox(
            "Periode", ["1 dag", "7 dagen", "30 dagen", "365 dagen"], index=1,
        )
    days_back = {"1 dag": 1, "7 dagen": 7, "30 dagen": 30, "365 dagen": 365}[window_label]
    target = latest_date - timedelta(days=days_back)
    alerts = []
    for cat in categories:
        cur = cat_on(cat, latest_date)
        if pd.isna(cur):
            continue
        hist_dates = cat_daily[(cat_daily["category"] == cat) &
                                (cat_daily["date"] <= target)]["date"]
        if len(hist_dates) == 0:
            continue
        hist_d = hist_dates.max()
        hist_mid = cat_on(cat, hist_d)
        if not hist_mid or pd.isna(hist_mid):
            continue
        pct = (cur - hist_mid) / hist_mid * 100
        if abs(pct) >= threshold:
            alerts.append({"cat": cat, "hist_d": hist_d, "hist_mid": hist_mid,
                            "cur_mid": cur, "pct": pct})
    if not alerts:
        st.markdown(
            f'<div style="text-align:center;padding:48px 0;color:{TEXT_DIM};">'
            f'Geen bewegingen ≥ {threshold}% over {window_label.lower()}.</div>',
            unsafe_allow_html=True,
        )
    else:
        alerts.sort(key=lambda a: abs(a["pct"]), reverse=True)
        for a in alerts:
            color = UP if a["pct"] > 0 else DOWN
            arrow = "▲" if a["pct"] > 0 else "▼"
            st.markdown(f"""
            <div class="alert-row">
              <div style="display:flex;justify-content:space-between;align-items:start;">
                <div class="a-cat">{a['cat']}</div>
                <div class="a-change" style="color:{color};">{arrow} {fmt_pct(a['pct'], 0)}</div>
              </div>
              <div class="a-meta">
                {fmt_eur(a['hist_mid'])} ({fmt_dutch_short(a['hist_d'])})
                → {fmt_eur(a['cur_mid'])} ({fmt_dutch_short(latest_date)})
              </div>
            </div>
            """, unsafe_allow_html=True)
