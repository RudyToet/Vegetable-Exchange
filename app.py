"""
Vegetable Price Tracker — markttracker voor verse groenten.
Combilo-groen, Apple-Aandelen navigatie, KNMI-weer + prijsvoorspelling.
"""
import base64
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ============================================================================
# CONFIG
# ============================================================================
_icon = "logo.png" if os.path.exists("logo.png") else "🌿"
st.set_page_config(
    page_title="Vegetable Price Tracker",
    page_icon=_icon,
    layout="centered",
    initial_sidebar_state="collapsed",
)

GREEN = "#6FB72D"
GREEN_BRIGHT = "#82D845"
BG = "#0A170D"
BG_CARD = "#102414"
BORDER = "#1B3825"
TEXT = "#F2F4F0"
TEXT_DIM = "#8AA088"
UP = GREEN
ACCENT = GREEN
DOWN = "#FF453A"
SUN = "#FFB627"
FORECAST = "#5AC8FA"

DUTCH_WD = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
DUTCH_MO = ["januari", "februari", "maart", "april", "mei", "juni",
            "juli", "augustus", "september", "oktober", "november", "december"]
DUTCH_MO_SHORT = ["jan", "feb", "mrt", "apr", "mei", "jun",
                  "jul", "aug", "sep", "okt", "nov", "dec"]

DATA_FILE = "data/chat.txt"
COMMENTARY_FILE = "data/commentary.md"

LOGO_SVG = f"""<svg width="34" height="34" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" rx="22" fill="{GREEN}"/>
  <rect x="20" y="62" width="14" height="22" rx="2.5" fill="#FFFFFF"/>
  <rect x="40" y="48" width="14" height="36" rx="2.5" fill="#FFFFFF"/>
  <rect x="60" y="32" width="14" height="52" rx="2.5" fill="#FFFFFF"/>
  <path d="M 67 28 C 60 16, 74 10, 84 14 C 88 24, 80 32, 70 30 C 68 30, 67 28, 67 28 Z" fill="#FFFFFF"/>
  <path d="M 70 27 L 82 17" stroke="{GREEN}" stroke-width="1.5" fill="none" stroke-linecap="round"/>
</svg>"""

# ============================================================================
# STYLE
# ============================================================================
st.markdown(f"""
<style>
  .stApp {{ background: {BG}; color: {TEXT}; }}
  .main .block-container {{ padding-top: 1rem; padding-bottom: 5rem; max-width: 540px; }}
  #MainMenu, footer {{visibility: hidden;}}
  header[data-testid="stHeader"] {{ background: transparent; }}

  .ve-brand {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 4px 10px 4px; border-bottom: 0.5px solid {BORDER}; margin-bottom: 8px;
  }}
  .ve-brand-left {{ display: flex; align-items: center; gap: 10px; }}
  .ve-brand-title {{ font-size: 21px; font-weight: 800; letter-spacing: -0.02em; color: {TEXT}; line-height: 1; }}
  .ve-brand-sub {{ font-size: 10px; color: {TEXT_DIM}; font-variant-numeric: tabular-nums; text-transform: uppercase; letter-spacing: 0.05em; }}

  .summary-card {{
    background: {BG_CARD}; border: 0.5px solid {BORDER}; border-radius: 14px;
    padding: 16px; margin-bottom: 14px;
  }}
  .summary-card .sc-label {{ font-size: 10px; font-weight: 700; color: {GREEN}; text-transform: uppercase; letter-spacing: 0.1em; }}
  .summary-card .sc-body {{ font-size: 14px; color: {TEXT}; line-height: 1.5; margin-top: 6px; }}
  .summary-card .sc-comment {{ font-size: 13px; color: {TEXT_DIM}; line-height: 1.5; margin-top: 10px; padding-top: 10px; border-top: 0.5px solid {BORDER}; white-space: pre-wrap; }}

  .ticker {{ display: flex; align-items: center; padding: 13px 2px; gap: 10px; }}
  .ticker-name {{ flex: 0 0 38%; min-width: 0; }}
  .ticker-name .cat {{ font-size: 16px; font-weight: 600; color: {TEXT}; line-height: 1.15; text-transform: capitalize; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .ticker-name .meta {{ font-size: 11px; color: {TEXT_DIM}; margin-top: 2px; }}
  .ticker-spark {{ flex: 0 0 26%; display: flex; justify-content: center; align-items: center; }}
  .ticker-price {{ flex: 1; text-align: right; min-width: 0; }}
  .ticker-price .price {{ font-size: 16px; font-weight: 600; color: {TEXT}; font-variant-numeric: tabular-nums; line-height: 1.15; }}
  .pill {{ display: inline-block; padding: 3px 7px; border-radius: 5px; font-size: 12px; font-weight: 700; margin-top: 4px; min-width: 56px; text-align: center; font-variant-numeric: tabular-nums; }}
  .pill-up   {{ background: {UP};   color: #042311; }}
  .pill-down {{ background: {DOWN}; color: #2A0A09; }}
  .pill-flat {{ background: {BORDER}; color: {TEXT_DIM}; }}

  .ve-section {{ font-size: 11px; font-weight: 700; color: {TEXT_DIM}; text-transform: uppercase; letter-spacing: 0.08em; margin: 16px 0 2px 2px; }}

  .detail-cat {{ font-size: 13px; color: {TEXT_DIM}; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 6px; }}
  .detail-price {{ font-size: 46px; font-weight: 700; color: {TEXT}; line-height: 1.05; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; margin-top: 2px; }}
  .detail-change {{ font-size: 15px; font-weight: 600; margin-top: 2px; font-variant-numeric: tabular-nums; }}
  .dc-up {{ color: {UP}; }}
  .dc-down {{ color: {DOWN}; }}

  .predict-card {{
    background: linear-gradient(135deg, {BG_CARD}, #0d2b1a); border: 0.5px solid {GREEN};
    border-radius: 14px; padding: 16px; margin: 14px 0;
  }}
  .predict-card .pc-label {{ font-size: 10px; font-weight: 700; color: {FORECAST}; text-transform: uppercase; letter-spacing: 0.1em; }}
  .predict-card .pc-price {{ font-size: 32px; font-weight: 700; color: {TEXT}; font-variant-numeric: tabular-nums; margin-top: 4px; }}
  .predict-card .pc-sub {{ font-size: 12px; color: {TEXT_DIM}; margin-top: 4px; }}

  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; border-top: 0.5px solid {BORDER}; margin-top: 8px; }}
  .stat {{ padding: 12px 4px; border-bottom: 0.5px solid {BORDER}; }}
  .stat-label {{ font-size: 11px; color: {TEXT_DIM}; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-value {{ font-size: 16px; font-weight: 600; color: {TEXT}; margin-top: 2px; font-variant-numeric: tabular-nums; }}

  .alert-row {{ background: {BG_CARD}; border: 0.5px solid {BORDER}; border-radius: 10px; padding: 13px; margin-bottom: 8px; }}
  .alert-row .a-cat {{ font-size: 15px; font-weight: 600; text-transform: capitalize; color: {TEXT}; }}
  .alert-row .a-change {{ font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .alert-row .a-meta {{ font-size: 11px; color: {TEXT_DIM}; margin-top: 4px; font-variant-numeric: tabular-nums; }}

  /* chevron / nav buttons */
  div[data-testid="stButton"] button {{
    background: {BG_CARD}; border: 0.5px solid {BORDER}; color: {TEXT};
    border-radius: 10px; font-weight: 600;
  }}
  div[data-testid="stButton"] button:hover {{ border-color: {GREEN}; color: {GREEN}; }}

  .stSelectbox > div > div {{ background: {BG_CARD}; border-color: {BORDER}; color: {TEXT}; }}
  .stRadio > div {{ background: {BG_CARD}; border-radius: 8px; padding: 4px; gap: 0; }}
  .stRadio label {{ color: {TEXT_DIM}; font-size: 12px; font-weight: 600; }}
  .streamlit-expanderHeader {{ background: {BG_CARD}; border: 0.5px solid {BORDER}; border-radius: 8px; color: {TEXT_DIM}; font-size: 13px; }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPERS
# ============================================================================
def fmt_eur(v, d=2):
    if pd.isna(v): return "—"
    return f"€{v:.{d}f}".replace(".", ",")

def fmt_pct(v, d=1):
    if pd.isna(v): return "—"
    return f"{'+' if v>0 else ''}{v:.{d}f}%"

def fmt_dutch_date(d):
    if not isinstance(d, datetime): d = pd.Timestamp(d).to_pydatetime()
    return f"{DUTCH_WD[d.weekday()]} {d.day} {DUTCH_MO[d.month-1]}"

def fmt_dutch_short(d):
    if not isinstance(d, datetime): d = pd.Timestamp(d).to_pydatetime()
    return f"{d.day} {DUTCH_MO_SHORT[d.month-1]}"

def sparkline_svg(values, width=100, height=26, color=UP):
    vals = [v for v in values if v is not None and not pd.isna(v)]
    if len(vals) < 2: return f'<svg width="{width}" height="{height}"></svg>'
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin: vmax = vmin + 0.01
    n = len(vals); pts = []
    for i, v in enumerate(vals):
        x = i*width/(n-1); y = height-2-((v-vmin)/(vmax-vmin))*(height-4)
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M " + " L ".join(pts); lx, ly = pts[-1].split(",")
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
            f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2" fill="{color}"/></svg>')

# ============================================================================
# PARSER
# ============================================================================
def parse_chat(text):
    mp = re.compile(r"\[(\d{2})-(\d{2})-(\d{4}), \d{2}:\d{2}:\d{2}\]")
    dr = re.compile(r"\b(ma|di|wo|do|vr|za|zo)\s+(\d{2})-(\d{2})\b")
    pr = re.compile(r"^(.*?):\s*([0-9]+\.[0-9]+)\s*-\s*([0-9]+\.[0-9]+)\s*$")
    pos = [(m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in mp.finditer(text)]
    rows = []
    for i, (p, d, mo, y) in enumerate(pos):
        end = pos[i+1][0] if i+1 < len(pos) else len(text)
        lines = [l.strip() for l in text[p:end].split("\n")]
        hdr = None; hi = None
        for idx, l in enumerate(lines):
            if l.startswith("[") or ":" in l: continue
            if dr.search(l): hdr = l; hi = idx; break
        if hdr is None: continue
        h = hdr.lower(); cat = None
        if h.startswith("trostomaat"): cat = "trostomaat"
        elif h.startswith("tomaat los"): cat = "tomaat los"
        elif "firenze" in h: cat = "firenze"
        elif h.startswith("komkommer"): cat = "komkommer"
        elif h.startswith("paprika"):
            pp = h.split()
            if len(pp) >= 2: cat = f"paprika {pp[1]}"
        elif h.startswith("aubergine"): cat = "aubergine"
        if cat is None: continue
        for l in lines[hi+1:]:
            if not l or l.startswith("["): continue
            m = pr.match(l)
            if not m: continue
            try: lo = float(m.group(2)); hh = float(m.group(3))
            except ValueError: continue
            rows.append({"date": datetime(y, mo, d), "category": cat,
                         "size": m.group(1).strip(), "low": lo, "high": hh, "mid": (lo+hh)/2})
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def parse_cached(text): return parse_chat(text)

def read_uploaded(uploaded):
    if uploaded.name.lower().endswith(".zip"):
        with zipfile.ZipFile(uploaded) as z:
            txt = [n for n in z.namelist() if n.lower().endswith(".txt")]
            if not txt: return ""
            with z.open(txt[0]) as f: return f.read().decode("utf-8", errors="replace")
    return uploaded.read().decode("utf-8", errors="replace")

# ============================================================================
# GITHUB STORAGE
# ============================================================================
def commit_to_github(content: str, path: str, label: str):
    token = st.secrets.get("GITHUB_TOKEN", ""); repo = st.secrets.get("GITHUB_REPO", "")
    if not token or not repo:
        return False, "GitHub-token of repo niet geconfigureerd in secrets."
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json", "User-Agent": "vpt/1.0"}
    sha = None
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200: sha = r.json().get("sha")
    except Exception: pass
    payload = {"message": f"{label} {datetime.now():%Y-%m-%d %H:%M}",
               "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
    if sha: payload["sha"] = sha
    try:
        r = requests.put(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        return False, f"Netwerkfout: {e}"
    if r.status_code in (200, 201):
        return True, "✅ Opgeslagen op GitHub. Streamlit deployt opnieuw in ~30 sec."
    return False, f"GitHub-fout {r.status_code}: {r.text[:160]}"

def load_text_file(path):
    p = Path(path)
    if p.exists():
        try: return p.read_text(encoding="utf-8", errors="replace")
        except Exception: return ""
    return ""

# ============================================================================
# WEATHER — KNMI historical + KNMI-model forecast (via Open-Meteo)
# ============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_knmi(start_d, end_d):
    try:
        r = requests.post("https://www.daggegevens.knmi.nl/klimatologie/daggegevens",
            data={"start": start_d.strftime("%Y%m%d"), "end": end_d.strftime("%Y%m%d"),
                  "vars": "SQ:TG:RH", "stns": "260"},
            headers={"User-Agent": "vpt/1.0"}, timeout=20)
        r.raise_for_status()
        recs = []
        for ln in r.text.split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith("#"): continue
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 5: continue
            try:
                _, ymd, sq, tg, rh = parts[:5]
                recs.append({"date": pd.to_datetime(ymd, format="%Y%m%d"),
                             "sunshine_h": (float(sq)/10) if sq else None,
                             "temp_c": (float(tg)/10) if tg else None,
                             "rain_mm": (max(0.0, float(rh))/10) if rh else None})
            except (ValueError, IndexError): continue
        return pd.DataFrame(recs)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_forecast(days=14):
    base = {"latitude": 52.10, "longitude": 5.18,
            "daily": "sunshine_duration,temperature_2m_mean,precipitation_sum",
            "forecast_days": days, "timezone": "Europe/Amsterdam"}
    for params in ({**base, "models": "knmi_seamless"}, base):
        try:
            r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=20)
            r.raise_for_status(); j = r.json(); dl = j.get("daily", {})
            if not dl.get("time"): continue
            return pd.DataFrame({
                "date": pd.to_datetime(dl["time"]),
                "sunshine_h": [(s/3600 if s is not None else None) for s in dl["sunshine_duration"]],
                "temp_c": dl["temperature_2m_mean"],
                "rain_mm": dl["precipitation_sum"]})
        except Exception:
            continue
    return pd.DataFrame()

# ============================================================================
# PREDICTION MODEL (ridge regression, numpy)
# ============================================================================
def make_weather_daily(knmi_hist, forecast_df):
    frames = []
    for f in (knmi_hist, forecast_df):
        if f is not None and not f.empty:
            frames.append(f[["date", "sunshine_h", "temp_c"]])
    if not frames: return pd.DataFrame()
    w = (pd.concat(frames).dropna(subset=["date"]).drop_duplicates("date").sort_values("date").set_index("date"))
    w = w.asfreq("D")
    w[["sunshine_h", "temp_c"]] = w[["sunshine_h", "temp_c"]].interpolate().ffill().bfill()
    return w

def train_and_forecast(cat, cat_daily, weather_daily, horizon=7):
    s = cat_daily[cat_daily.category == cat][["date", "mid"]].dropna().sort_values("date")
    if len(s) < 60 or weather_daily.empty: return None
    s = s.set_index("date").asfreq("D"); s["mid"] = s["mid"].interpolate(limit=3)
    d = s.join(weather_daily, how="left")
    d["sun_trail7"] = d["sunshine_h"].rolling(7, min_periods=3).mean()
    d["temp_trail7"] = d["temp_c"].rolling(7, min_periods=3).mean()
    d["price_lag7"] = d["mid"].shift(7)
    doy = d.index.dayofyear
    d["doy_sin"] = np.sin(2*np.pi*doy/365.25); d["doy_cos"] = np.cos(2*np.pi*doy/365.25)
    fc = ["doy_sin", "doy_cos", "price_lag7", "sun_trail7", "temp_trail7"]
    tr = d.dropna(subset=fc+["mid"])
    if len(tr) < 50: return None
    X = tr[fc].values.astype(float); y = tr["mid"].values.astype(float)
    mu = X.mean(0); sd = X.std(0); sd[sd == 0] = 1; Xs = (X-mu)/sd
    Xb = np.column_stack([np.ones(len(Xs)), Xs]); lam = 1.0
    A = Xb.T@Xb + lam*np.eye(Xb.shape[1]); A[0, 0] -= lam
    try: w = np.linalg.solve(A, Xb.T@y)
    except Exception: return None
    resid = y - Xb@w; sigma = float(resid.std())
    ss_res = float((resid**2).sum()); ss_tot = float(((y-y.mean())**2).sum())
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
    last = s.index.max(); rows = []
    for h in range(1, horizon+1):
        dd = last + pd.Timedelta(days=h); dyd = dd.dayofyear
        lagd = dd - pd.Timedelta(days=7); lagp = d["mid"].get(lagd, np.nan)
        if pd.isna(lagp): lagp = d["mid"].dropna().iloc[-1]
        win = pd.date_range(dd - pd.Timedelta(days=6), dd)
        s7 = weather_daily["sunshine_h"].reindex(win).mean()
        t7 = weather_daily["temp_c"].reindex(win).mean()
        feat = np.array([np.sin(2*np.pi*dyd/365.25), np.cos(2*np.pi*dyd/365.25), lagp, s7, t7])
        fs = (feat-mu)/sd; pred = max(0.0, float(np.r_[1.0, fs]@w))
        rows.append({"date": dd, "pred": pred, "lo": max(0.0, pred-sigma), "hi": pred+sigma})
    return {"forecast": pd.DataFrame(rows), "sigma": sigma, "r2": r2, "last_price": float(y[-1])}

# ============================================================================
# AUTO MARKET SUMMARY
# ============================================================================
def generate_summary(cat_daily, categories, latest_date, cat_on, prev_date_for):
    ups = downs = 0; movers = []
    for cat in categories:
        cur = cat_on(cat, latest_date)
        pd_ = prev_date_for(cat, latest_date)
        if pd_ is not None and not pd.isna(cur):
            prev = cat_on(cat, pd_)
            if prev:
                ch = (cur-prev)/prev*100
                if ch > 0.5: ups += 1
                elif ch < -0.5: downs += 1
        d7 = latest_date - timedelta(days=7)
        h = cat_daily[(cat_daily.category == cat) & (cat_daily.date <= d7)]["date"]
        if len(h):
            p7 = cat_on(cat, h.max())
            if p7 and not pd.isna(cur): movers.append((cat, (cur-p7)/p7*100))
    parts = [f"{ups} omhoog, {downs} omlaag t.o.v. de vorige notering."]
    if movers:
        movers.sort(key=lambda x: abs(x[1]), reverse=True)
        top = movers[:2]
        bits = [f"{c} {fmt_pct(p,0)}" for c, p in top]
        parts.append("Grootste bewegers (7d): " + ", ".join(bits) + ".")
        pap = [p for c, p in movers if c.startswith("paprika")]
        if pap:
            avg = sum(pap)/len(pap)
            if abs(avg) >= 3:
                parts.append(f"Paprika gemiddeld {fmt_pct(avg,0)} over de week.")
    return " ".join(parts)

# ============================================================================
# HEADER
# ============================================================================
now = datetime.now()
st.markdown(f"""
<div class="ve-brand">
  <div class="ve-brand-left">{LOGO_SVG}<div class="ve-brand-title">Vegetable Price Tracker</div></div>
  <div class="ve-brand-sub">{fmt_dutch_short(now)} · {now.strftime('%H:%M')}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# VIEWER AUTH
# ============================================================================
viewer_pass = st.secrets.get("VIEWER_PASSWORD", "")
if viewer_pass and not st.session_state.get("viewer_auth"):
    st.markdown(f"<div style='padding:48px 0 16px;text-align:center;'>"
                f"<div style='font-size:13px;color:{TEXT_DIM};text-transform:uppercase;letter-spacing:0.12em;font-weight:600;'>Toegang vereist</div>"
                f"<div style='font-size:13px;color:{TEXT_DIM};margin-top:6px;'>Voer het wachtwoord in om de markt te zien</div></div>",
                unsafe_allow_html=True)
    pw_in = st.text_input("Wachtwoord", type="password", label_visibility="collapsed", placeholder="Wachtwoord")
    if pw_in:
        if pw_in == viewer_pass:
            st.session_state.viewer_auth = True; st.rerun()
        else: st.error("Verkeerd wachtwoord.")
    st.stop()

# ============================================================================
# DATA LOAD
# ============================================================================
if "df" not in st.session_state or st.session_state.get("df") is None:
    txt = load_text_file(DATA_FILE)
    if txt.strip():
        d = parse_cached(txt)
        if not d.empty: st.session_state.df = d
df = st.session_state.get("df")

if "commentary" not in st.session_state:
    st.session_state.commentary = load_text_file(COMMENTARY_FILE)

# ============================================================================
# ADMIN PANEL
# ============================================================================
admin_pass = st.secrets.get("ADMIN_PASSWORD", "")
with st.expander("⚙️ Admin", expanded=(df is None or df.empty)):
    if not admin_pass:
        st.warning("Geen ADMIN_PASSWORD in secrets — tijdelijke upload (alleen deze sessie).")
        up = st.file_uploader("WhatsApp-export", type=["zip", "txt"], label_visibility="collapsed")
        if up is not None:
            t = read_uploaded(up)
            if t: st.session_state.df = parse_cached(t); st.success("Data geladen (alleen sessie)."); st.rerun()
    else:
        pw = st.text_input("Admin-wachtwoord", type="password", key="admin_pw")
        if pw and pw == admin_pass:
            st.success("✓ Toegang")
            up = st.file_uploader("1. Upload WhatsApp-export", type=["zip", "txt"], label_visibility="visible")
            if up is not None:
                t = read_uploaded(up)
                if t:
                    with st.spinner("Opslaan op GitHub..."):
                        ok, msg = commit_to_github(t, DATA_FILE, "Update marktdata")
                    st.session_state.df = parse_cached(t)
                    (st.success if ok else st.error)(msg)
                    if ok: st.balloons()
            st.markdown("---")
            txt_comment = st.text_area("2. Marktcommentaar (zichtbaar voor iedereen)",
                                       value=st.session_state.get("commentary", ""), height=120)
            if st.button("Commentaar opslaan"):
                with st.spinner("Opslaan..."):
                    ok, msg = commit_to_github(txt_comment, COMMENTARY_FILE, "Update commentaar")
                st.session_state.commentary = txt_comment
                (st.success if ok else st.error)(msg)
        elif pw:
            st.error("Verkeerd wachtwoord.")

if df is None or df.empty:
    st.info("Nog geen data. Vraag de beheerder om via Admin te uploaden.")
    st.stop()

# ============================================================================
# DERIVED
# ============================================================================
cat_daily = (df.groupby(["date", "category"])["mid"].mean().reset_index().sort_values(["category", "date"]))
categories = sorted(df["category"].unique())
latest_date = df["date"].max()

def cat_on(cat, d):
    sub = cat_daily[(cat_daily.category == cat) & (cat_daily.date == d)]
    return float(sub["mid"].iloc[0]) if len(sub) else float("nan")

def prev_date_for(cat, ref):
    sub = cat_daily[(cat_daily.category == cat) & (cat_daily.date < ref)]["date"]
    return sub.max() if len(sub) else None

if "selected_product" not in st.session_state:
    st.session_state.selected_product = None

# ============================================================================
# DETAIL VIEW
# ============================================================================
def render_detail(cat_sel):
    if st.button("‹ Markt", key="back_btn"):
        st.session_state.selected_product = None; st.rerun()

    period = st.radio("Periode", ["1W", "1M", "3M", "6M", "YTD", "1J", "ALL"],
                      index=2, horizontal=True, label_visibility="collapsed")
    cat_data = cat_daily[cat_daily.category == cat_sel].sort_values("date").copy()
    last_d = cat_data["date"].max()
    starts = {"1W": last_d-timedelta(days=7), "1M": last_d-timedelta(days=30),
              "3M": last_d-timedelta(days=90), "6M": last_d-timedelta(days=180),
              "YTD": datetime(last_d.year, 1, 1), "1J": last_d-timedelta(days=365),
              "ALL": cat_data["date"].min()}
    start_d = starts[period]
    pdf = cat_data[cat_data["date"] >= start_d].copy()
    cur = pdf["mid"].iloc[-1] if len(pdf) else float("nan")
    first = pdf["mid"].iloc[0] if len(pdf) else float("nan")
    delta = (cur-first) if pd.notna(cur) and pd.notna(first) else 0
    pct = (delta/first*100) if first else 0
    cls = "dc-up" if delta >= 0 else "dc-down"; sign = "+" if delta >= 0 else ""
    st.markdown(f"""<div class="detail-cat">{cat_sel}</div>
      <div class="detail-price">{fmt_eur(cur)}</div>
      <div class="detail-change {cls}">{sign}{fmt_eur(delta).replace('€','')} ({fmt_pct(pct,2)}) · {period}</div>""",
      unsafe_allow_html=True)

    show_weather = st.toggle("☀️ KNMI zon overlay", value=True)
    show_predict = st.toggle("🔮 Voorspelling (7 dagen)", value=True)

    knmi_df = fetch_knmi(start_d.date(), last_d.date()) if show_weather else pd.DataFrame()

    fc_res = None
    if show_predict:
        with st.spinner("Voorspelling berekenen..."):
            knmi_full = fetch_knmi((cat_data["date"].min()-timedelta(days=14)).date(), last_d.date())
            forecast_w = fetch_forecast(14)
            weather_daily = make_weather_daily(knmi_full, forecast_w)
            fc_res = train_and_forecast(cat_sel, cat_daily, weather_daily, horizon=7)

    color_line = UP if delta >= 0 else DOWN
    layers = []
    price_line = alt.Chart(pdf).mark_line(strokeWidth=2.2, color=color_line).encode(
        x=alt.X("date:T", axis=alt.Axis(labelColor=TEXT_DIM, tickColor=BORDER, domainColor=BORDER, grid=False, title=None, format="%d %b")),
        y=alt.Y("mid:Q", axis=alt.Axis(labelColor=TEXT_DIM, tickColor=BORDER, domainColor=BORDER, gridColor=BORDER, gridOpacity=0.3, title="€", titleColor=TEXT_DIM, format=".2f")),
        tooltip=[alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"), alt.Tooltip("mid:Q", title="Prijs", format=".2f")])
    layers.append(price_line)

    if show_predict and fc_res is not None:
        fc = fc_res["forecast"].copy()
        bridge = pd.DataFrame([{"date": last_d, "pred": cur, "lo": cur, "hi": cur}])
        fc_line = pd.concat([bridge, fc], ignore_index=True)
        band = alt.Chart(fc_line).mark_area(opacity=0.15, color=FORECAST).encode(
            x="date:T", y=alt.Y("lo:Q"), y2="hi:Q")
        fline = alt.Chart(fc_line).mark_line(strokeWidth=2, color=FORECAST, strokeDash=[4, 3]).encode(
            x="date:T", y="pred:Q",
            tooltip=[alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"), alt.Tooltip("pred:Q", title="Verwacht", format=".2f")])
        layers += [band, fline]

    if show_weather and not knmi_df.empty:
        sun = alt.Chart(knmi_df).mark_bar(color=SUN, opacity=0.22, size=4).encode(
            x="date:T", y=alt.Y("sunshine_h:Q", axis=alt.Axis(labelColor=SUN, tickColor=BORDER, domainColor=BORDER, gridOpacity=0, title="zon (uur)", titleColor=SUN, orient="right")),
            tooltip=[alt.Tooltip("date:T", title="Datum", format="%d-%m-%Y"), alt.Tooltip("sunshine_h:Q", title="Zonuren", format=".1f"), alt.Tooltip("temp_c:Q", title="Temp °C", format=".1f")])
        chart = alt.layer(sun, *layers).resolve_scale(y="independent")
    else:
        chart = alt.layer(*layers)
    chart = chart.properties(height=250, background=BG, padding={"left": 0, "right": 0, "top": 4, "bottom": 0}).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # Prediction card
    if show_predict:
        if fc_res is not None:
            pred7 = fc_res["forecast"]["pred"].iloc[-1]
            pdelta = pred7 - cur; ppct = (pdelta/cur*100) if cur else 0
            arrow = "▲" if pdelta >= 0 else "▼"; pcolor = UP if pdelta >= 0 else DOWN
            conf = "hoog" if fc_res["r2"] > 0.7 else ("gemiddeld" if fc_res["r2"] > 0.5 else "laag")
            st.markdown(f"""<div class="predict-card">
              <div class="pc-label">🔮 Verwacht over 7 dagen</div>
              <div class="pc-price">{fmt_eur(pred7)} <span style="font-size:16px;color:{pcolor};">{arrow} {fmt_pct(ppct,0)}</span></div>
              <div class="pc-sub">Bandbreedte {fmt_eur(fc_res['forecast']['lo'].iloc[-1])} – {fmt_eur(fc_res['forecast']['hi'].iloc[-1])} · betrouwbaarheid {conf} (R²={fc_res['r2']:.2f})</div>
              <div class="pc-sub">Model: prijshistorie + KNMI-weersverwachting. Indicatief, geen garantie.</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("Te weinig historie voor een betrouwbare voorspelling van dit product.")

    # Stats
    if len(pdf) > 0:
        pmin, pmax, pavg = pdf["mid"].min(), pdf["mid"].max(), pdf["mid"].mean()
        try:
            ys, ye = start_d - pd.DateOffset(years=1), last_d - pd.DateOffset(years=1)
            ydf = cat_data[(cat_data.date >= ys) & (cat_data.date <= ye)]
            yavg = ydf["mid"].mean() if len(ydf) else float("nan")
        except Exception:
            yavg = float("nan")
        yval = f"{fmt_eur(yavg)} ({fmt_pct((pavg-yavg)/yavg*100,0)})" if pd.notna(yavg) and yavg else "—"
        ws = ""
        if show_weather and not knmi_df.empty:
            ws = (f"<div class='stat'><div class='stat-label'>Zon totaal</div><div class='stat-value'>{knmi_df['sunshine_h'].sum():.0f} uur</div></div>"
                  f"<div class='stat'><div class='stat-label'>Temp gem</div><div class='stat-value'>{knmi_df['temp_c'].mean():.1f} °C</div></div>")
        st.markdown(f"""<div class="stat-grid">
          <div class="stat"><div class="stat-label">Laag {period}</div><div class="stat-value">{fmt_eur(pmin)}</div></div>
          <div class="stat"><div class="stat-label">Hoog {period}</div><div class="stat-value">{fmt_eur(pmax)}</div></div>
          <div class="stat"><div class="stat-label">Gem {period}</div><div class="stat-value">{fmt_eur(pavg)}</div></div>
          <div class="stat"><div class="stat-label">YoY vorig jaar</div><div class="stat-value">{yval}</div></div>
          {ws}
        </div>""", unsafe_allow_html=True)

    with st.expander("Per sortering — laatste dag"):
        sub = df[(df.category == cat_sel) & (df.date == latest_date)].sort_values("size")
        for _, r in sub.iterrows():
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid {BORDER};color:{TEXT};font-size:14px;'><span>{r['size']}</span><span style='font-variant-numeric:tabular-nums;'>{fmt_eur(r['low'])} – {fmt_eur(r['high'])}</span></div>", unsafe_allow_html=True)

# ============================================================================
# MAIN (LIST) VIEW
# ============================================================================
def render_list():
    summary = generate_summary(cat_daily, categories, latest_date, cat_on, prev_date_for)
    comment = st.session_state.get("commentary", "").strip()
    comment_html = f'<div class="sc-comment">{comment}</div>' if comment else ""
    st.markdown(f"""<div class="summary-card">
      <div class="sc-label">Marktupdate · {fmt_dutch_date(latest_date)}</div>
      <div class="sc-body">{summary}</div>{comment_html}
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="ve-section">Producten</div>', unsafe_allow_html=True)
    for cat in categories:
        cur = cat_on(cat, latest_date)
        if pd.isna(cur): continue
        pd_ = prev_date_for(cat, latest_date)
        change = ((cur-cat_on(cat, pd_))/cat_on(cat, pd_)*100) if pd_ is not None and cat_on(cat, pd_) else 0
        cutoff = latest_date - timedelta(days=30)
        sv = cat_daily[(cat_daily.category == cat) & (cat_daily.date >= cutoff)]["mid"].tolist()
        scol = UP if (len(sv) >= 2 and sv[-1]-sv[0] >= 0) else (DOWN if len(sv) >= 2 else TEXT_DIM)
        spark = sparkline_svg(sv, color=scol)
        pcls = "pill-flat" if abs(change) < 0.5 else ("pill-up" if change > 0 else "pill-down")
        nsort = len(df[(df.category == cat) & (df.date == latest_date)])
        row_html = f"""<div class="ticker">
          <div class="ticker-name"><div class="cat">{cat}</div><div class="meta">{nsort} sortering{'en' if nsort!=1 else ''}</div></div>
          <div class="ticker-spark">{spark}</div>
          <div class="ticker-price"><div class="price">{fmt_eur(cur)}</div><div class="pill {pcls}">{fmt_pct(change)}</div></div>
        </div>"""
        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        with c1:
            st.markdown(row_html, unsafe_allow_html=True)
        with c2:
            if st.button("›", key=f"open_{cat}"):
                st.session_state.selected_product = cat; st.rerun()
        st.markdown(f"<div style='border-bottom:0.5px solid {BORDER};margin:0 2px;'></div>", unsafe_allow_html=True)

    # Alerts
    st.markdown('<div class="ve-section">Grote bewegingen (7 dagen)</div>', unsafe_allow_html=True)
    target = latest_date - timedelta(days=7); alerts = []
    for cat in categories:
        cur = cat_on(cat, latest_date)
        if pd.isna(cur): continue
        hd = cat_daily[(cat_daily.category == cat) & (cat_daily.date <= target)]["date"]
        if not len(hd): continue
        hm = cat_on(cat, hd.max())
        if not hm or pd.isna(hm): continue
        p = (cur-hm)/hm*100
        if abs(p) >= 10: alerts.append((cat, hm, cur, hd.max(), p))
    if not alerts:
        st.markdown(f"<div style='color:{TEXT_DIM};font-size:13px;padding:4px 2px;'>Geen bewegingen ≥10% deze week.</div>", unsafe_allow_html=True)
    else:
        alerts.sort(key=lambda a: abs(a[4]), reverse=True)
        for cat, hm, cur, hdmax, p in alerts:
            color = UP if p > 0 else DOWN; arrow = "▲" if p > 0 else "▼"
            st.markdown(f"""<div class="alert-row"><div style="display:flex;justify-content:space-between;align-items:start;">
              <div class="a-cat">{cat}</div><div class="a-change" style="color:{color};">{arrow} {fmt_pct(p,0)}</div></div>
              <div class="a-meta">{fmt_eur(hm)} ({fmt_dutch_short(hdmax)}) → {fmt_eur(cur)} ({fmt_dutch_short(latest_date)})</div></div>""", unsafe_allow_html=True)

    st.markdown(f"<div class='ve-section'>Dataset</div><div style='color:{TEXT_DIM};font-size:12px;padding:0 2px;'>{len(df):,} prijzen · {df['date'].nunique()} dagen · {df['date'].min():%d-%m-%Y} t/m {df['date'].max():%d-%m-%Y}</div>".replace(",", "."), unsafe_allow_html=True)

# ============================================================================
# ROUTER
# ============================================================================
if st.session_state.selected_product and st.session_state.selected_product in categories:
    render_detail(st.session_state.selected_product)
else:
    render_list()
