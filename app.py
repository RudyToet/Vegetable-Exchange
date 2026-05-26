"""
Oxin Prijsindex — Streamlit dashboard voor WhatsApp marktprijzen Oxin Growers.
Upload de WhatsApp-export (.zip of .txt) en zie dagprijzen, trends, YoY en alerts.
"""
import re
import io
import zipfile
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

# ============================================================================
# CONFIG
# ============================================================================
st.set_page_config(
    page_title="Oxin Prijsindex",
    page_icon="🥒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DUTCH_MONTHS = ["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun",
                "Jul", "Aug", "Sep", "Okt", "Nov", "Dec"]

# ============================================================================
# PARSER
# ============================================================================
def parse_chat(text: str) -> pd.DataFrame:
    """Parse WhatsApp chat export and return a tidy DataFrame of prices."""
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

        # Find product header line (contains weekday + dd-mm, no colon)
        header = None
        header_idx = None
        for idx, line in enumerate(lines):
            if line.startswith("["):
                continue
            if ":" in line:
                continue
            if date_re.search(line):
                header = line
                header_idx = idx
                break
        if header is None:
            continue

        # Classify category
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

        # Extract price lines
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
                "low": low,
                "high": high,
                "mid": (low + high) / 2,
            })

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def parse_cached(text: str) -> pd.DataFrame:
    """Cached wrapper — Streamlit re-uses result if the same text is uploaded again."""
    return parse_chat(text)


# ============================================================================
# HELPERS
# ============================================================================
def read_uploaded(uploaded) -> str:
    """Read either a .zip (containing _chat.txt) or .txt directly."""
    name = uploaded.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(uploaded) as z:
            txt_files = [n for n in z.namelist() if n.lower().endswith(".txt")]
            if not txt_files:
                return ""
            with z.open(txt_files[0]) as f:
                return f.read().decode("utf-8", errors="replace")
    return uploaded.read().decode("utf-8", errors="replace")


def fmt_eur(v) -> str:
    return f"€{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(v) else "—"


def category_mid_on(df: pd.DataFrame, cat: str, target_date) -> float:
    """Average mid-price across all sizes for a category on a specific date."""
    sub = df[(df["category"] == cat) & (df["date"] == target_date)]
    return sub["mid"].mean() if len(sub) else float("nan")


# ============================================================================
# UI — HEADER
# ============================================================================
st.title("🥒 Oxin Prijsindex")
st.caption("Marktprijzen Oxin Growers — dashboard op basis van WhatsApp-export")

# ============================================================================
# UPLOAD
# ============================================================================
with st.expander("📁 Upload WhatsApp-export", expanded="df" not in st.session_state):
    uploaded = st.file_uploader(
        "Sleep de export hierheen (.zip of .txt)",
        type=["zip", "txt"],
        help=(
            "WhatsApp → Oxin Growers chat openen → naam aantikken → "
            "'Chat exporteren' → 'Zonder media'. Mail het bestand naar jezelf "
            "of sla het op in je telefoon, en upload het hier."
        ),
    )
    if uploaded is not None:
        text = read_uploaded(uploaded)
        if not text:
            st.error("Geen .txt in de ZIP gevonden.")
            st.stop()
        with st.spinner("Berichten parseren..."):
            st.session_state.df = parse_cached(text)

if "df" not in st.session_state:
    st.info("👆 Upload eerst een WhatsApp-export om te beginnen. Er wordt niets opgeslagen.")
    st.stop()

df = st.session_state.df
if df.empty:
    st.error("Geen prijzen herkend in dit bestand. Klopt de export?")
    st.stop()

# Header stat
min_d, max_d = df["date"].min().date(), df["date"].max().date()
n_days = df["date"].nunique()
st.success(f"✅ **{len(df):,} prijzen** — {n_days} dagen tussen {min_d:%d-%m-%Y} en {max_d:%d-%m-%Y}".replace(",", "."))

# ============================================================================
# TABS
# ============================================================================
tab_today, tab_trend, tab_yoy, tab_alerts = st.tabs(
    ["📊 Vandaag", "📈 Trends", "↔️ YoY", "🔔 Alerts"]
)

# ----------------------------------------------------------------------------
# TAB 1 — VANDAAG
# ----------------------------------------------------------------------------
with tab_today:
    latest_date = df["date"].max()
    weekday_nl = ["Maandag", "Dinsdag", "Woensdag", "Donderdag",
                  "Vrijdag", "Zaterdag", "Zondag"][latest_date.weekday()]
    st.subheader(f"{weekday_nl} {latest_date:%d-%m-%Y}")

    latest = df[df["date"] == latest_date]
    categories_today = sorted(latest["category"].unique())

    if not categories_today:
        st.warning("Geen data op laatste datum.")
    else:
        for cat in categories_today:
            cat_today = latest[latest["category"] == cat]
            cur_mid = cat_today["mid"].mean()

            # Previous available date for this category
            prev_dates = df[(df["category"] == cat) & (df["date"] < latest_date)]["date"]
            if len(prev_dates):
                prev_date = prev_dates.max()
                prev_mid = category_mid_on(df, cat, prev_date)
                delta = cur_mid - prev_mid
                delta_pct = (delta / prev_mid * 100) if prev_mid else 0
                delta_str = f"{delta:+.2f} ({delta_pct:+.0f}%) vs {prev_date:%d-%m}"
            else:
                delta_str = None

            st.metric(cat.capitalize(), f"€{cur_mid:.2f}", delta_str)

            with st.expander(f"Per sortering — {cat}"):
                for _, row in cat_today.iterrows():
                    st.write(f"**{row['size']}** — €{row['low']:.2f} – €{row['high']:.2f}")
            st.divider()

# ----------------------------------------------------------------------------
# TAB 2 — TRENDS
# ----------------------------------------------------------------------------
with tab_trend:
    st.subheader("Prijsverloop per product")

    all_cats = sorted(df["category"].unique())
    default = [c for c in ["paprika rood", "komkommer", "trostomaat"] if c in all_cats][:3]
    if not default:
        default = all_cats[:3]
    selected = st.multiselect("Producten", all_cats, default=default)

    period = st.radio("Periode", ["Laatste 30 dgn", "Laatste 90 dgn", "Alles"],
                      index=2, horizontal=True)

    if selected:
        plot_df = (df[df["category"].isin(selected)]
                   .groupby(["date", "category"])["mid"].mean()
                   .reset_index())
        max_d_dt = plot_df["date"].max()
        if period == "Laatste 30 dgn":
            plot_df = plot_df[plot_df["date"] >= max_d_dt - timedelta(days=30)]
        elif period == "Laatste 90 dgn":
            plot_df = plot_df[plot_df["date"] >= max_d_dt - timedelta(days=90)]

        chart = (alt.Chart(plot_df)
                 .mark_line(point=True, strokeWidth=2)
                 .encode(
                     x=alt.X("date:T", title=None),
                     y=alt.Y("mid:Q", title="Mid-prijs (€)"),
                     color=alt.Color("category:N", title=None),
                     tooltip=["date:T", "category:N",
                              alt.Tooltip("mid:Q", format=".2f", title="€")]
                 )
                 .properties(height=380)
                 .interactive())
        st.altair_chart(chart, use_container_width=True)

        # 7-day rolling average
        with st.expander("7-daags rollend gemiddelde"):
            rolling_dfs = []
            for cat in selected:
                cat_df = plot_df[plot_df["category"] == cat].sort_values("date").copy()
                cat_df["rolling"] = cat_df["mid"].rolling(7, min_periods=1).mean()
                rolling_dfs.append(cat_df)
            roll = pd.concat(rolling_dfs)
            roll_chart = (alt.Chart(roll)
                          .mark_line(strokeWidth=2)
                          .encode(
                              x=alt.X("date:T", title=None),
                              y=alt.Y("rolling:Q", title="7-d gem. (€)"),
                              color=alt.Color("category:N", title=None)
                          )
                          .properties(height=300)
                          .interactive())
            st.altair_chart(roll_chart, use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 3 — YOY
# ----------------------------------------------------------------------------
with tab_yoy:
    st.subheader("YoY vergelijking")

    df_yoy = df.copy()
    df_yoy["year"] = df_yoy["date"].dt.year
    df_yoy["month"] = df_yoy["date"].dt.month

    years = sorted(df_yoy["year"].unique())
    if len(years) < 2:
        st.info("Nog niet genoeg historie voor YoY-vergelijking (minimaal 2 jaren nodig).")
    else:
        all_cats_yoy = sorted(df_yoy["category"].unique())
        cat_yoy = st.selectbox("Product", all_cats_yoy,
                               index=all_cats_yoy.index("paprika rood") if "paprika rood" in all_cats_yoy else 0)

        cat_data = df_yoy[df_yoy["category"] == cat_yoy]
        monthly = (cat_data.groupby(["year", "month"])["mid"]
                   .mean().reset_index())
        monthly["month_name"] = monthly["month"].apply(lambda m: DUTCH_MONTHS[m - 1])

        chart = (alt.Chart(monthly)
                 .mark_bar()
                 .encode(
                     x=alt.X("month_name:N",
                             sort=DUTCH_MONTHS,
                             title=None),
                     y=alt.Y("mid:Q", title="Gem. mid-prijs (€)"),
                     color=alt.Color("year:O", title="Jaar",
                                     scale=alt.Scale(scheme="set2")),
                     xOffset="year:O",
                     tooltip=["year:O", "month_name:N",
                              alt.Tooltip("mid:Q", format=".2f", title="€")]
                 )
                 .properties(height=380))
        st.altair_chart(chart, use_container_width=True)

        # Pivot table with YoY %
        pivot = monthly.pivot(index="month", columns="year", values="mid").round(2)
        pivot.index = [DUTCH_MONTHS[m - 1] for m in pivot.index]
        if pivot.shape[1] >= 2:
            y_prev, y_cur = pivot.columns[-2], pivot.columns[-1]
            yoy_pct = ((pivot[y_cur] - pivot[y_prev]) / pivot[y_prev] * 100).round(0)
            pivot[f"YoY {y_cur} vs {y_prev}"] = yoy_pct.astype("Int64").astype(str) + "%"
        st.dataframe(pivot, use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 4 — ALERTS
# ----------------------------------------------------------------------------
with tab_alerts:
    st.subheader("Grote bewegingen")

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider("Drempel %", 5, 50, 15, step=5)
    with col2:
        window_label = st.selectbox("Periode", ["1 dag", "7 dagen", "30 dagen", "365 dagen"], index=1)
    days_back = {"1 dag": 1, "7 dagen": 7, "30 dagen": 30, "365 dagen": 365}[window_label]

    latest_date = df["date"].max()
    target = latest_date - timedelta(days=days_back)

    alerts = []
    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        cur_mid = category_mid_on(df, cat, latest_date)
        if pd.isna(cur_mid):
            continue
        # closest historical date on or before target
        hist_candidates = cat_df[cat_df["date"] <= target]
        if hist_candidates.empty:
            continue
        hist_date = hist_candidates["date"].max()
        hist_mid = category_mid_on(df, cat, hist_date)
        if not hist_mid or pd.isna(hist_mid):
            continue
        pct = (cur_mid - hist_mid) / hist_mid * 100
        if abs(pct) >= threshold:
            alerts.append({
                "cat": cat,
                "hist_date": hist_date,
                "hist_mid": hist_mid,
                "cur_mid": cur_mid,
                "pct": pct,
            })

    if not alerts:
        st.success(f"Geen producten bewogen ≥{threshold}% over {window_label.lower()}. 😴")
    else:
        alerts.sort(key=lambda a: abs(a["pct"]), reverse=True)
        st.caption(f"{len(alerts)} producten bewogen ≥{threshold}% sinds {target.date():%d-%m-%Y}")
        for a in alerts:
            arrow = "📈" if a["pct"] > 0 else "📉"
            color_emoji = "🔴" if a["pct"] > 0 else "🟢"
            st.markdown(f"### {arrow} {a['cat'].capitalize()}  &nbsp;&nbsp; {color_emoji} **{a['pct']:+.0f}%**")
            st.caption(
                f"€{a['hist_mid']:.2f} ({a['hist_date']:%d-%m}) → "
                f"€{a['cur_mid']:.2f} ({latest_date.date():%d-%m})"
            )
            st.divider()

# ============================================================================
# FOOTER
# ============================================================================
with st.expander("ℹ️ Over deze app"):
    st.markdown("""
- **Bron**: WhatsApp-export Oxin Growers (jouw eigen telefoon).
- **Privacy**: data wordt alleen in je browsersessie geladen. Niets blijft op de server staan.
- **Update-flow**: exporteer de chat elke ochtend opnieuw en upload — de export bevat altijd de volledige geschiedenis.
- **Mid-prijs**: gemiddelde van de min-max bandbreedte per dag/sortering. Categoriegemiddelde weegt sorteringen even zwaar.
    """)
