"""Bermuda Triangle 🍪 — NYT Games dashboard (dark neon, mobile-first)."""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bermuda Triangle 🍪", page_icon="🍪",
                   layout="centered", initial_sidebar_state="collapsed")

# ---------- palette: neon NYT on black ----------
BG = "#0A0A0B"
CARD = "#141416"
BORDER = "#2A2A2C"
TEXT = "#FFFFFF"
MUTED = "#8A8A8E"
SOFT = "#C9C9CC"
GREEN = "#3DFF6E"    # neon wordle green
YELLOW = "#FFE23B"   # neon connections yellow
BLUE = "#4DA6FF"     # neon connections blue
PURPLE = "#D96BFF"   # neon connections purple
PLAYER_COLORS = [GREEN, YELLOW, PURPLE, BLUE]
PODIUM_SHADES = {"wordle": ["#3DFF6E", "#2BB852", "#1E8A3C"],
                 "connections": ["#D96BFF", "#A94FD1", "#7C37A3"]}
FONT = "'Times New Roman', Times, serif"

st.markdown(f"""
<style>
  .stApp {{ background: {BG}; }}
  .block-container {{ padding-top: 2rem; max-width: 640px; }}
  html, body, .stApp, .stMarkdown, p, span, div, label, button,
  h1, h2, h3, h4 {{ font-family: {FONT} !important; }}
  h1, h2, h3 {{ color: {TEXT} !important; letter-spacing: -0.01em; }}
  .tile-row {{ display:flex; gap:5px; margin:0 0 10px 0; }}
  .tile {{ width:22px; height:22px; border-radius:4px; }}
  .stamp {{ color:{MUTED}; font-size:0.85rem; margin:-6px 0 14px 0; }}
  .sect {{ font-size:1.45rem; font-weight:600; margin:20px 0 4px 0; }}
  .sub {{ color:{MUTED}; font-size:0.8rem; text-transform:uppercase;
          letter-spacing:0.07em; margin:10px 0 6px 0; }}
  .streaks {{ display:flex; gap:8px; margin-bottom:6px; }}
  .streak {{ flex:1; background:{CARD}; border:1px solid {BORDER};
             border-radius:12px; padding:10px 6px; text-align:center; }}
  .streak .n {{ color:{TEXT}; font-size:0.95rem; margin-bottom:4px; }}
  .streak .v {{ font-size:1.15rem; font-weight:700; }}
  .podium {{ display:flex; align-items:flex-end; gap:8px; height:150px;
             margin:4px 0 6px 0; }}
  .pcol {{ flex:1; display:flex; flex-direction:column;
           justify-content:flex-end; height:100%; }}
  .pname {{ text-align:center; color:{TEXT}; font-size:1rem; }}
  .pval {{ text-align:center; color:{SOFT}; font-size:0.9rem;
           margin-bottom:3px; }}
  .pbar {{ border-radius:8px 8px 0 0; display:flex;
           align-items:flex-start; justify-content:center;
           padding-top:5px; color:#0A0A0B; font-weight:700;
           font-size:1.05rem; }}
</style>""", unsafe_allow_html=True)


def gate() -> bool:
    try:
        pw = st.secrets.get("APP_PASSWORD", None)
    except Exception:
        pw = None
    if not pw or st.session_state.get("authed"):
        return True
    st.markdown("## 🟨🟩🟦🟪")
    entered = st.text_input("Group password", type="password")
    if entered:
        if entered == pw:
            st.session_state["authed"] = True
            st.rerun()
        st.error("Wrong password.")
    return False


if not gate():
    st.stop()


@st.cache_data(ttl=300)
def load() -> pd.DataFrame:
    import db as _db
    conn = _db.connect("results.db")
    df = pd.read_sql_query("SELECT * FROM results", conn,
                           parse_dates=["puzzle_date"])
    conn.close()
    return df


full = load()

# ---------- header ----------
tiles = "".join(f"<div class='tile' style='background:{c}'></div>"
                for c in [YELLOW, GREEN, BLUE, PURPLE])
st.markdown(f"<div class='tile-row'>{tiles}</div>", unsafe_allow_html=True)
st.markdown("# Bermuda Triangle 🍪")

if full.empty:
    st.info("No results yet — check back after the next ingest run.")
    st.stop()

latest_wordle = full.loc[full["game"] == "wordle", "puzzle_number"].max()
ts = pd.to_datetime(full["message_ts"], errors="coerce", utc=True,
                    format="mixed")
try:
    updated = ts.max().tz_convert("Europe/Berlin").strftime("%d %b, %H:%M")
except Exception:
    updated = str(ts.max())
st.markdown(f"<div class='stamp'>Data through Wordle "
            f"#{latest_wordle:,.0f} · last refreshed {updated}</div>",
            unsafe_allow_html=True)

players = sorted(full["player_name"].unique())
color_of = {p: PLAYER_COLORS[i % len(PLAYER_COLORS)]
            for i, p in enumerate(players)}


# ---------- current play streaks (always as of today) ----------
def current_streak(dates: pd.Series) -> int:
    days = sorted(set(dates.dt.date))
    if not days:
        return 0
    today = full["puzzle_date"].max().date()
    if (today - days[-1]).days > 1:
        return 0
    s = 1
    for a, b in zip(reversed(days[:-1]), reversed(days[1:])):
        if (b - a).days == 1:
            s += 1
        else:
            break
    return s


st.markdown("<div class='sub'>Current play streaks</div>",
            unsafe_allow_html=True)
cards = []
for p in players:
    sw = current_streak(
        full[(full["player_name"] == p) & (full["game"] == "wordle")]
        ["puzzle_date"])
    sc = current_streak(
        full[(full["player_name"] == p) & (full["game"] == "connections")]
        ["puzzle_date"])
    cards.append(
        f"<div class='streak'><div class='n'>{p}</div><div class='v'>"
        f"<span style='color:{GREEN}'>W {sw}</span>&nbsp;&nbsp;"
        f"<span style='color:{PURPLE}'>C {sc}</span></div></div>")
st.markdown(f"<div class='streaks'>{''.join(cards)}</div>",
            unsafe_allow_html=True)

# ---------- period selector (below streaks) ----------
period = st.segmented_control(
    "Period", ["Day", "Week", "Month", "All-time"], default="Week",
    label_visibility="collapsed")
today = full["puzzle_date"].max().date()
cutoff = {"Day": today,
          "Week": today - timedelta(days=today.weekday()),
          "Month": today.replace(day=1),
          "All-time": full["puzzle_date"].min().date()}[period or "Week"]
df = full[full["puzzle_date"].dt.date >= cutoff]
if df.empty:
    st.info("No games in this period yet.")
    st.stop()


def podium(g: pd.DataFrame, shades, unit: str):
    avg = g.groupby("player_name")["score"].agg(["mean", "size"]) \
           .sort_values("mean")
    order = list(avg.index)
    slots = [1, 0, 2] if len(order) >= 3 else list(range(len(order)))
    heights = [78, 58, 40]
    cols = []
    for slot in slots:
        p = order[slot]
        cols.append(
            f"<div class='pcol'><div class='pname' "
            f"style='color:{shades[0] if slot == 0 else TEXT}'>{p}</div>"
            f"<div class='pval'>{avg.loc[p,'mean']:.2f} · "
            f"{int(avg.loc[p,'size'])} games</div>"
            f"<div class='pbar' style='height:{heights[slot]}%;"
            f"background:{shades[slot]}'>{slot + 1}</div></div>")
    st.markdown(f"<div class='podium'>{''.join(cols)}</div>"
                f"<div class='sub' style='margin-top:0'>avg {unit} — "
                f"lower is better</div>", unsafe_allow_html=True)


def distribution(g: pd.DataFrame, cats, labels, title: str):
    st.markdown(f"<div class='sub'>{title}</div>", unsafe_allow_html=True)
    fig = go.Figure()
    peak = 0
    for p in players:
        sub = g[g["player_name"] == p]
        if sub.empty:
            continue
        pct = (sub["score"].value_counts(normalize=True) * 100)
        vals = [round(pct.get(cat, 0)) for cat in cats]
        peak = max(peak, max(vals))
        fig.add_bar(name=p, y=labels, x=vals, orientation="h",
                    marker_color=color_of[p],
                    text=[f"{v}%" if v else "" for v in vals],
                    textposition="outside",
                    textfont=dict(size=13, color=color_of[p]))
    fig.update_layout(
        barmode="group", height=90 + 60 * len(cats),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=14, family=FONT),
        margin=dict(l=8, r=30, t=4, b=4),
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(visible=False, range=[0, max(62, peak * 1.12)]),
        yaxis=dict(autorange="reversed", gridcolor=BORDER,
                   tickfont=dict(size=15)))
    st.plotly_chart(fig, width="stretch",
                    config={"displayModeBar": False})


w = df[df["game"] == "wordle"]
if not w.empty:
    st.markdown(f"<div class='sect' style='color:{GREEN}'>Wordle</div>",
                unsafe_allow_html=True)
    podium(w, PODIUM_SHADES["wordle"], "attempts")
    distribution(w, cats=[1, 2, 3, 4, 5, 6, 7],
                 labels=["1", "2", "3", "4", "5", "6", "X"],
                 title="Guess distribution — % of each player's games")

c = df[df["game"] == "connections"]
if not c.empty:
    st.markdown(f"<div class='sect' style='color:{PURPLE}'>Connections"
                f"</div>", unsafe_allow_html=True)
    podium(c, PODIUM_SHADES["connections"], "mistakes")
    distribution(c, cats=[0, 1, 2, 3, 4],
                 labels=["0", "1", "2", "3", "4"],
                 title="Mistake distribution — % of each player's games")

st.markdown(f"<div class='stamp' style='margin-top:18px'>{len(df)} results "
            f"in view · {df['puzzle_date'].min():%d %b %Y} – "
            f"{df['puzzle_date'].max():%d %b %Y} · auto-updates every 6 h"
            f"</div>", unsafe_allow_html=True)
