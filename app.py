"""NYT Games group dashboard (Streamlit)."""

import sqlite3

import pandas as pd
import streamlit as st

st.set_page_config(page_title="NYT Games Leaderboard", page_icon="🟪",
                   layout="wide")


# ---------- optional shared-password gate ----------
def gate() -> bool:
    pw = st.secrets.get("APP_PASSWORD", None)
    if not pw:
        return True  # no password configured
    if st.session_state.get("authed"):
        return True
    st.title("🟪 NYT Games Leaderboard")
    entered = st.text_input("Group password", type="password")
    if entered:
        if entered == pw:
            st.session_state["authed"] = True
            st.rerun()
        st.error("Wrong password.")
    return False


if not gate():
    st.stop()


# ---------- data ----------
@st.cache_data(ttl=300)
def load() -> pd.DataFrame:
    import db as _db
    conn = _db.connect("results.db")  # creates schema if missing
    df = pd.read_sql_query("SELECT * FROM results", conn,
                           parse_dates=["puzzle_date"])
    conn.close()
    return df


df = load()
st.title("🟨🟩🟦🟪 NYT Games Leaderboard")

if df.empty:
    st.info("No results yet. Once the bot has seen a few share messages, "
            "they'll show up here after the next ingest run.")
    st.stop()

players = sorted(df["player_name"].dropna().unique())
sel = st.multiselect("Players", players, default=players)
df = df[df["player_name"].isin(sel)]

wordle = df[df["game"] == "wordle"].copy()
conx = df[df["game"] == "connections"].copy()

tab_lead, tab_w, tab_c = st.tabs(["Leaderboard", "Wordle", "Connections"])


def current_streak(dates: pd.Series) -> int:
    """Longest run of consecutive puzzle days ending at the latest one."""
    days = sorted(set(dates.dt.date))
    if not days:
        return 0
    streak = 1
    for a, b in zip(reversed(days[:-1]), reversed(days[1:])):
        if (b - a).days == 1:
            streak += 1
        else:
            break
    return streak


with tab_lead:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Wordle")
        if wordle.empty:
            st.caption("No Wordle results yet.")
        else:
            g = wordle.groupby("player_name")
            board = pd.DataFrame({
                "Played": g.size(),
                "Avg guesses": g["score"].mean().round(2),
                "Solve %": (g["solved"].mean() * 100).round(0).astype(int),
                "Streak": g["puzzle_date"].agg(current_streak),
            }).sort_values("Avg guesses")
            st.dataframe(board, use_container_width=True)
    with c2:
        st.subheader("Connections")
        if conx.empty:
            st.caption("No Connections results yet.")
        else:
            g = conx.groupby("player_name")
            board = pd.DataFrame({
                "Played": g.size(),
                "Avg mistakes": g["score"].mean().round(2),
                "Perfect %": ((g["score"].apply(lambda s: (s == 0).mean()))
                              * 100).round(0).astype(int),
                "Solve %": (g["solved"].mean() * 100).round(0).astype(int),
                "Streak": g["puzzle_date"].agg(current_streak),
            }).sort_values("Avg mistakes")
            st.dataframe(board, use_container_width=True)

    st.subheader("Daily wins (lowest score, ties split)")
    daily = df.dropna(subset=["score"]).copy()
    if not daily.empty:
        mins = daily.groupby(["game", "puzzle_number"])["score"] \
                    .transform("min")
        winners = daily[daily["score"] == mins]
        share = winners.groupby(["game", "puzzle_number"])["player_name"] \
                       .transform("size")
        winners = winners.assign(win=1 / share)
        wins = winners.groupby("player_name")["win"].sum() \
                      .sort_values(ascending=False).round(1)
        st.bar_chart(wins)

with tab_w:
    if wordle.empty:
        st.caption("No Wordle results yet.")
    else:
        st.subheader("Guess distribution")
        labels = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "X"}
        dist = (wordle.assign(g=wordle["score"].map(labels))
                .groupby(["player_name", "g"]).size().unstack(fill_value=0))
        st.bar_chart(dist.T)
        st.subheader("Rolling average (last 30 puzzles)")
        pivot = wordle.pivot_table(index="puzzle_date",
                                   columns="player_name", values="score")
        st.line_chart(pivot.rolling(7, min_periods=1).mean().tail(30))
        st.subheader("Hard mode users")
        hm = wordle.groupby("player_name")["hard_mode"].mean() * 100
        st.dataframe(hm.round(0).astype(int).rename("Hard mode %"))

with tab_c:
    if conx.empty:
        st.caption("No Connections results yet.")
    else:
        st.subheader("Mistake distribution")
        dist = (conx.groupby(["player_name", "score"]).size()
                .unstack(fill_value=0))
        dist.columns = [f"{c} mistake{'s' if c != 1 else ''}"
                        for c in dist.columns]
        st.bar_chart(dist)
        st.subheader("Rolling average mistakes (last 30 puzzles)")
        pivot = conx.pivot_table(index="puzzle_date",
                                 columns="player_name", values="score")
        st.line_chart(pivot.rolling(7, min_periods=1).mean().tail(30))

st.caption(f"{len(df)} results · {df['puzzle_date'].min():%d %b %Y} – "
           f"{df['puzzle_date'].max():%d %b %Y} · data updates every 6 h")
