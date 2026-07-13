"""NYT Games group dashboard — dark, mobile-first, tile-themed."""

import sqlite3
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Bermuda NYT Games", page_icon="🟪",
                   layout="centered",
                   initial_sidebar_state="collapsed")

# ---------- palette: NYT tiles on Wordle dark ----------
BG = "#121213"
CARD = "#1E1E1F"
BORDER = "#3A3A3C"
TEXT = "#F5F5F6"
MUTED = "#9A9A9C"
GREEN = "#6AAA64"    # wordle green
YELLOW = "#F9DF6D"   # connections yellow
BLUE = "#B0C4EF"     # connections blue
PURPLE = "#BA81C5"   # connections purple
PLAYER_COLORS = [GREEN, PURPLE, YELLOW, BLUE]

st.markdown(f"""
<style>
  .stApp {{ background: {BG}; }}
  .block-container {{ padding-top: 2.2rem; max-width: 680px; }}
  h1, h2, h3 {{ letter-spacing: -0.02em; }}
  .tile-row {{ display:flex; gap:6px; margin:2px 0 14px 0; }}
  .tile {{ width:26px; height:26px; border-radius:5px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(2,1fr);
               gap:10px; margin:6px 0 4px 0; }}
  .kpi {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
          padding:12px 14px; }}
  .kpi .v {{ font-size:1.55rem; font-weight:800; color:{TEXT};
             line-height:1.1; }}
  .kpi .l {{ font-size:0.72rem; color:{MUTED}; text-transform:uppercase;
             letter-spacing:0.08em; margin-top:3px; }}
  .hero {{ background:linear-gradient(135deg, #1E1E1F 0%, #26262a 100%);
           border:1px solid {BORDER}; border-radius:16px;
           padding:18px 18px 14px 18px; margin-bottom:6px; }}
  .hero .crown {{ font-size:2rem; }}
  .hero .name {{ font-size:1.7rem; font-weight:800; color:{TEXT}; }}
  .hero .sub {{ color:{MUTED}; font-size:0.85rem; }}
  .sup {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
          padding:11px 13px; margin-bottom:8px;
          display:flex; align-items:center; gap:12px; }}
  .sup .e {{ font-size:1.5rem; }}
  .sup .t {{ font-weight:700; color:{TEXT}; font-size:0.95rem; }}
  .sup .d {{ color:{MUTED}; font-size:0.78rem; }}
  .h2h {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px;
          padding:12px 14px; margin-bottom:8px; text-align:center; }}
  .h2h .score {{ font-size:1.5rem; font-weight:800; color:{TEXT}; }}
  .h2h .names {{ color:{MUTED}; font-size:0.8rem; }}
</style>""", unsafe_allow_html=True)


# ---------- optional shared-password gate ----------
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
st.markdown("# 🟨🟩🟦🟪 Bermuda Games")
if full.empty:
    st.info("No results yet — check back after the next ingest run.")
    st.stop()

# ---------- period selector ----------
period = st.segmented_control(
    "Period", ["This week", "This month", "All-time"],
    default="This week", label_visibility="collapsed")
today = full["puzzle_date"].max().date()
if period == "This week":
    cutoff = today - timedelta(days=today.weekday())          # Monday
elif period == "This month":
    cutoff = today.replace(day=1)
else:
    cutoff = date(2000, 1, 1)
df = full[full["puzzle_date"].dt.date >= cutoff].copy()
if df.empty:
    st.info("No games in this period yet.")
    st.stop()

players = sorted(full["player_name"].unique())
color_of = {p: PLAYER_COLORS[i % len(PLAYER_COLORS)]
            for i, p in enumerate(players)}


# ---------- points: per game+puzzle, 1st=3 2nd=2 3rd=1, ties split ----------
def with_points(d: pd.DataFrame) -> pd.DataFrame:
    d = d.dropna(subset=["score"]).copy()
    grp = d.groupby(["game", "puzzle_number"])
    rank = grp["score"].rank(method="average", ascending=True)
    n = grp["player_name"].transform("size")
    d["points"] = (n - rank + 1).clip(lower=0)
    return d


pts = with_points(df)
totals = pts.groupby("player_name")["points"].sum().sort_values(
    ascending=False)


def plotly_base(fig, height=260):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=13), height=height,
        margin=dict(l=8, r=8, t=8, b=8), showlegend=False,
        xaxis=dict(gridcolor=BORDER, zeroline=False),
        yaxis=dict(gridcolor=BORDER, zeroline=False))
    return fig


# ---------- hero: champion ----------
leader = totals.index[0]
lead_pts = totals.iloc[0]
gap = lead_pts - (totals.iloc[1] if len(totals) > 1 else 0)
tiles = "".join(
    f"<div class='tile' style='background:{c}'></div>"
    for c in [YELLOW, GREEN, BLUE, PURPLE, GREEN])
label = {"This week": "leads this week", "This month": "leads this month",
         "All-time": "all-time champion"}[period]
st.markdown(f"""
<div class="hero">
  <div class="tile-row">{tiles}</div>
  <span class="crown">👑</span>
  <span class="name">{leader}</span>
  <div class="sub">{label} · {lead_pts:.0f} pts ·
    +{gap:.0f} ahead</div>
</div>""", unsafe_allow_html=True)

# ---------- combined points race ----------
st.markdown("### 🏆 Points race")
fig = go.Figure(go.Bar(
    x=totals.values, y=totals.index, orientation="h",
    marker_color=[color_of[p] for p in totals.index],
    text=[f"{v:.0f}" for v in totals.values], textposition="outside",
    textfont=dict(size=15, color=TEXT)))
fig.update_yaxes(autorange="reversed", showgrid=False)
fig.update_xaxes(visible=False)
st.plotly_chart(plotly_base(fig, height=60 + 52 * len(totals)),
                width="stretch",
                config={"displayModeBar": False})
st.caption("Per game & day: best result 3 pts, 2nd 2 pts, 3rd 1 pt — "
           "ties split.")

# ---------- per-game sections ----------
for game, emoji, metric, better in [
        ("wordle", "🟩", "guesses", "fewer"),
        ("connections", "🟪", "mistakes", "fewer")]:
    g = pts[pts["game"] == game]
    if g.empty:
        continue
    st.markdown(f"### {emoji} {game.capitalize()}")
    by = g.groupby("player_name")
    best_p = by["score"].mean().idxmin()
    kpis = [
        (f"{by['score'].mean().min():.2f}",
         f"best avg {metric} · {best_p}"),
        (f"{int(by.size().max())}",
         f"most played · {by.size().idxmax()}"),
        (f"{by['solved'].mean().max()*100:.0f}%",
         f"best solve rate · {by['solved'].mean().idxmax()}"),
        (f"{int((g['score'] == g['score'].min()).sum())}",
         f"results at best score ({g['score'].min():.0f})"),
    ]
    st.markdown("<div class='kpi-grid'>" + "".join(
        f"<div class='kpi'><div class='v'>{v}</div>"
        f"<div class='l'>{l}</div></div>" for v, l in kpis)
        + "</div>", unsafe_allow_html=True)

    # score distribution — grouped bars per player
    fig = go.Figure()
    scores = sorted(g["score"].unique())
    lab = (lambda s: "X" if s == 7 else str(int(s))) if game == "wordle" \
        else (lambda s: str(int(s)))
    for p in totals.index:
        sub = g[g["player_name"] == p]["score"].value_counts()
        fig.add_bar(name=p, x=[lab(s) for s in scores],
                    y=[int(sub.get(s, 0)) for s in scores],
                    marker_color=color_of[p])
    fig.update_layout(barmode="group", showlegend=True,
                      legend=dict(orientation="h", y=1.12, x=0))
    plotly_base(fig, height=240)
    fig.update_layout(showlegend=True)
    st.plotly_chart(fig, width="stretch",
                    config={"displayModeBar": False})

# ---------- trends (always all-time context) ----------
st.markdown("### 📈 Form curve")
game_pick = st.segmented_control(
    "Game", ["Wordle", "Connections"], default="Wordle",
    label_visibility="collapsed", key="trend_game")
tg = with_points(full)[with_points(full)["game"] == game_pick.lower()]
pivot = tg.pivot_table(index="puzzle_date", columns="player_name",
                       values="score")
roll = pivot.rolling(14, min_periods=3).mean()
fig = go.Figure()
for p in players:
    if p in roll:
        fig.add_scatter(x=roll.index, y=roll[p], name=p, mode="lines",
                        line=dict(color=color_of[p], width=3))
fig.update_layout(showlegend=True,
                  legend=dict(orientation="h", y=1.12, x=0))
plotly_base(fig, height=260)
fig.update_layout(showlegend=True)
fig.update_yaxes(title="14-day avg (lower = better)")
st.plotly_chart(fig, width="stretch",
                config={"displayModeBar": False})

# ---------- superlatives ----------
st.markdown("### 🎖️ Superlatives")


def current_streak(dates: pd.Series) -> int:
    days = sorted(set(dates.dt.date))
    if not days:
        return 0
    s = 1
    for a, b in zip(reversed(days[:-1]), reversed(days[1:])):
        if (b - a).days == 1:
            s += 1
        else:
            break
    return s


sups = []
streaks = df.groupby("player_name")["puzzle_date"].agg(current_streak)
sups.append(("🔥", "On Fire", streaks.idxmax(),
             f"{int(streaks.max())}-day active streak"))
w = df[df["game"] == "wordle"]
if not w.empty:
    snip = w[w["score"] <= 2].groupby("player_name").size()
    if not snip.empty:
        sups.append(("🎯", "Sharpshooter", snip.idxmax(),
                     f"{int(snip.max())} Wordles in ≤2 guesses"))
c = df[df["game"] == "connections"]
if not c.empty:
    perf = c[c["score"] == 0].groupby("player_name").size()
    if not perf.empty:
        sups.append(("🧠", "Galaxy Brain", perf.idxmax(),
                     f"{int(perf.max())} perfect Connections"))
    pf = c[c["raw"].str.startswith("🟪🟪🟪🟪", na=False)] \
        .groupby("player_name").size()
    if not pf.empty:
        sups.append(("🟪", "Purple Hunter", pf.idxmax(),
                     f"goes for purple first · {int(pf.max())}×"))
fails = df[df["solved"] == 0].groupby("player_name").size()
if not fails.empty:
    sups.append(("💀", "Grave Digger", fails.idxmax(),
                 f"{int(fails.max())} failed puzzles"))
ts = pd.to_datetime(df["message_ts"], errors="coerce", utc=True,
                    format="mixed")
hours = df.assign(h=ts.dt.hour).dropna(subset=["h"]) \
          .groupby("player_name")["h"].mean()
if not hours.empty:
    sups.append(("🐦", "Early Bird", hours.idxmin(),
                 f"posts ~{hours.min():.0f}:00 on average"))

st.markdown("".join(
    f"<div class='sup'><div class='e'>{e}</div><div>"
    f"<div class='t'>{t} — {who}</div><div class='d'>{d}</div>"
    f"</div></div>" for e, t, who, d in sups), unsafe_allow_html=True)

# ---------- head-to-head ----------
st.markdown("### ⚔️ Head-to-head")
st.caption("Daily duels per game — win = strictly better result that day.")
merged = pts[["player_name", "game", "puzzle_number", "score"]]
cards = []
for i, a in enumerate(players):
    for b in players[i + 1:]:
        m = merged[merged["player_name"] == a].merge(
            merged[merged["player_name"] == b],
            on=["game", "puzzle_number"], suffixes=("_a", "_b"))
        if m.empty:
            continue
        wa = int((m["score_a"] < m["score_b"]).sum())
        wb = int((m["score_a"] > m["score_b"]).sum())
        dr = len(m) - wa - wb
        ca, cb = color_of[a], color_of[b]
        cards.append(
            f"<div class='h2h'><div class='score'>"
            f"<span style='color:{ca}'>{wa}</span>"
            f"<span style='color:{MUTED}'> – </span>"
            f"<span style='color:{cb}'>{wb}</span></div>"
            f"<div class='names'><span style='color:{ca}'>{a}</span>"
            f" vs <span style='color:{cb}'>{b}</span>"
            f" · {dr} draws</div></div>")
st.markdown("".join(cards), unsafe_allow_html=True)

st.caption(f"{len(df)} results in view · "
           f"{df['puzzle_date'].min():%d %b %Y} – "
           f"{df['puzzle_date'].max():%d %b %Y} · updates every 6 h")
