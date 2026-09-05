"""Post weekly / monthly trash-talk summaries to the Telegram group.

Usage:
  python3 summary.py weekly            # last full week (Mon-Sun)
  python3 summary.py monthly           # last full calendar month
  python3 summary.py weekly --dry-run  # print instead of sending

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import calendar
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

import pandas as pd

# Keep in sync with DISPLAY_NAMES elsewhere.
DISPLAY_NAMES = {8983515512: "Finn", 5182590002: "Peter",
                 1197776677: "Stella"}

GAMES = [  # key, title, metric label, lower-is-better
    ("wordle", "🟩 Wordle", "guesses", True),
    ("connections", "🟪 Connections", "mistakes", True),
    ("wordle_in_1", "⚡ Wordle in 1", "time", True),
    ("connections_3x3", "🔢 Connections 3x3", "mistakes", True),
]
MIN_ATTENDANCE = 0.5   # play at least half the days to be ranked
MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

# ---------------- trash talk bank ----------------
OPENERS = [
    "Another week, another set of questionable decisions.",
    "The results are in and some of you should be worried.",
    "Gather round. Someone needs to see this.",
    "Statistics don't lie. Unlike some of your excuses.",
    "Grab a coffee. This won't be pleasant for everyone.",
]
LAST_PLACE = [
    "{p} finishes last. The tiles were green, the performance was not.",
    "{p} brought up the rear with the confidence of someone who didn't check the leaderboard.",
    "A moment of silence for {p}, who tried.",
    "{p}, last place. Have you considered Sudoku?",
    "{p} rounds out the podium the way a participation trophy rounds out a shelf.",
]
WINNER = [
    "{p} takes it. Unbearable for the rest of us.",
    "{p} wins. Please do not let them speak about it.",
    "{p} on top. Somebody check if they're using a second phone.",
    "{p} dominates. Group chat morale at an all-time low.",
]
FAILS = [
    "{p} failed {n} puzzle(s). The letters were right there.",
    "{n} fail(s) for {p}. Bold strategy.",
    "{p} logged {n} fail(s). Grave Digger status retained.",
]
DNP = [
    "{p} skipped {n} day(s). Fear is a valid emotion.",
    "{p} only showed up {played}/{total} days. Commitment issues.",
]
PERFECT = [
    "{p} went perfect {n} time(s). Annoying, but respect.",
    "{n} flawless run(s) for {p}. Machines walk among us.",
]
STREAK_KING = [
    "{p} holds the streak crown at {n} days. Touch grass.",
    "{n}-day streak for {p}. Nobody asked, yet here we are.",
]
STREAK_BROKEN = [
    "{p} let the streak die. It had a family.",
    "{p}: streak reset to zero. Devastating. Hilarious.",
]
FASTEST = [
    "{p} solved Wordle in 1 in {t}. Suspicious. Impressive. Suspicious.",
    "Fastest fingers: {p} at {t}. Somebody's been practicing in secret.",
]
IMPROVED = ["{p} improved by {d:.2f} on {game}. Growth. Character development. Fluke."]
DECLINED = ["{p} got {d:.2f} worse at {game}. Regression is a natural part of life."]


def pick(pool, seed):
    return random.Random(seed).choice(pool)


def fmt_time(secs) -> str:
    return f"{int(secs) // 60}:{int(secs) % 60:02d}"


def load(db_path="results.db") -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM results", conn,
                           parse_dates=["puzzle_date"])
    conn.close()
    if df.empty:
        return df
    latest = df.sort_values("message_ts").groupby("player_id")["player_name"].last()
    df["player"] = df["player_id"].map(lambda i: DISPLAY_NAMES.get(i, latest[i]))
    return df


def period_bounds(kind: str, today: date):
    if kind == "weekly":
        end = today - timedelta(days=today.weekday() + 1)   # last Sunday
        start = end - timedelta(days=6)
        prev = (start - timedelta(days=7), start - timedelta(days=1))
        label = f"Week {start.isocalendar()[1]} ({start:%d %b} – {end:%d %b})"
    else:
        first_this = today.replace(day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(day=1)
        pe = start - timedelta(days=1)
        prev = (pe.replace(day=1), pe)
        label = f"{start:%B %Y}"
    return start, end, prev, label


def current_streak(days: list, upto: date) -> int:
    if not days or (upto - days[-1]).days > 1:
        return 0
    s = 1
    for a, b in zip(reversed(days[:-1]), reversed(days[1:])):
        if (b - a).days == 1:
            s += 1
        else:
            break
    return s


def game_block(g: pd.DataFrame, prev: pd.DataFrame, key, title, metric,
               total_days, seed, monthly) -> list[str]:
    lines = [f"<b>{title}</b>"]
    if g.empty:
        return lines + ["Nobody played. Cowards."]
    by = g.groupby("player")
    played = by.size()
    # days this game was actually played by anyone in the period
    total_days = g["puzzle_date"].nunique()
    if key == "wordle_in_1":
        solved = by["solved"].sum()
        rate = (solved / played)
        fastest = g[g["solved"] == 1].sort_values("score")
        rank = pd.DataFrame({"rate": rate, "solved": solved, "played": played}) \
                 .sort_values(["rate", "solved"], ascending=[False, False])
        eligible = rank[rank["played"] >= total_days * MIN_ATTENDANCE]
        bench = rank[rank["played"] < total_days * MIN_ATTENDANCE]
        if eligible.empty:
            eligible, bench = rank, rank.iloc[0:0]
        for i, (p, r) in enumerate(eligible.iterrows()):
            lines.append(f"{MEDALS[i]} {p} — solved {int(r['solved'])}/{int(r['played'])}")
        for p, r in bench.iterrows():
            lines.append(f"🪑 {p} — solved {int(r['solved'])}/{int(r['played'])} (unranked, too few games)")
        rank = eligible if not eligible.empty else rank
        if not fastest.empty:
            f = fastest.iloc[0]
            lines.append(f"⏱ Fastest: {f['player']} {fmt_time(f['score'])}")
            lines.append("<i>" + pick(FASTEST, seed + 1).format(
                p=f["player"], t=fmt_time(f["score"])) + "</i>")
        order = list(rank.index)
    else:
        scored = g.dropna(subset=["score"])
        avg_all = scored.groupby("player")["score"].mean().sort_values()
        elig = [p for p in avg_all.index if played[p] >= total_days * MIN_ATTENDANCE]
        avg = avg_all[elig] if elig else avg_all
        for i, (p, v) in enumerate(avg.items()):
            lines.append(f"{MEDALS[i]} {p} — {v:.2f} avg {metric} · {int(played[p])}/{total_days} played")
        for p, v in avg_all.items():
            if p not in avg.index:
                lines.append(f"🪑 {p} — {v:.2f} avg {metric} · {int(played[p])}/{total_days} played (unranked, too few games)")
        order = list(avg.index)
        if key == "wordle":
            best = scored.sort_values("score").iloc[0]
            lines.append(f"⭐ Best solve: {best['player']} {int(best['score'])}/6 "
                         f"({best['puzzle_date']:%a})")
        else:
            perf = (scored["score"] == 0).groupby(scored["player"]).sum()
            if perf.max() > 0:
                p = perf.idxmax()
                lines.append(f"✨ Most perfect: {p} ({int(perf.max())})")
                lines.append("<i>" + pick(PERFECT, seed + 2).format(
                    p=p, n=int(perf.max())) + "</i>")
        if monthly and not prev.empty:
            pavg = prev.dropna(subset=["score"]).groupby("player")["score"].mean()
            delta = (avg - pavg).dropna()
            if not delta.empty:
                best_p, worst_p = delta.idxmin(), delta.idxmax()
                if delta[best_p] < 0:
                    lines.append("<i>" + pick(IMPROVED, seed + 3).format(
                        p=best_p, d=-delta[best_p], game=title[2:]) + "</i>")
                if delta[worst_p] > 0:
                    lines.append("<i>" + pick(DECLINED, seed + 4).format(
                        p=worst_p, d=delta[worst_p], game=title[2:]) + "</i>")
    if len(order) >= 2:
        lines.append("<i>" + pick(LAST_PLACE, seed + 5).format(p=order[-1]) + "</i>")
    fails = g[g["solved"] == 0].groupby("player").size()
    if not fails.empty:
        p = fails.idxmax()
        lines.append("<i>" + pick(FAILS, seed + 6).format(p=p, n=int(fails.max())) + "</i>")
    return lines


def build(kind: str, today: date, db_path="results.db") -> str:
    df = load(db_path)
    start, end, (pstart, pend), label = period_bounds(kind, today)
    seed = int(start.strftime("%Y%m%d"))
    total_days = (end - start).days + 1
    cur = df[(df["puzzle_date"].dt.date >= start) & (df["puzzle_date"].dt.date <= end)]
    prv = df[(df["puzzle_date"].dt.date >= pstart) & (df["puzzle_date"].dt.date <= pend)]
    head = "🏆 <b>Bermuda Triangle 🍪 — " + label + "</b>"
    if cur.empty:
        return head + "\n\nNobody played anything. The group chat is a ghost town."
    out = [head, "<i>" + pick(OPENERS, seed) + "</i>", ""]

    # overall winner = most game-wins across games (rank 1 in each block)
    wins = {}
    for key, title, metric, _ in GAMES:
        g = cur[cur["game"] == key]
        if g.empty:
            continue
        block = game_block(g, prv[prv["game"] == key], key, title, metric,
                           total_days, seed + hash(key) % 100, kind == "monthly")
        out += block + [""]
        top = block[1].split(" ")[1] if block[1].startswith("🥇") else None
        if top:
            wins[top] = wins.get(top, 0) + 1
    if wins:
        champ = max(wins, key=wins.get)
        out.insert(3, "<i>" + pick(WINNER, seed + 9).format(p=champ) + "</i>\n")

    # streaks (Wordle, as of period end)
    streaks = {}
    for p, sub in df[df["game"] == "wordle"].groupby("player"):
        days = sorted(set(sub["puzzle_date"].dt.date))
        streaks[p] = current_streak([d for d in days if d <= end], end)
    if streaks:
        srt = sorted(streaks.items(), key=lambda kv: -kv[1])
        out.append("🔥 <b>Wordle streaks:</b> " + " · ".join(f"{p} {n}" for p, n in srt))
        king, kn = srt[0]
        if kn >= 7:
            out.append("<i>" + pick(STREAK_KING, seed + 7).format(p=king, n=kn) + "</i>")
        broken = [p for p, n in srt if n == 0 and
                  prv[(prv["game"] == "wordle") & (prv["player"] == p)].shape[0] >= 5]
        if broken:
            out.append("<i>" + pick(STREAK_BROKEN, seed + 8).format(p=" & ".join(broken)) + "</i>")

    # attendance shaming
    for p, sub in cur.groupby("player"):
        d = len(set(sub["puzzle_date"].dt.date))
        if d < total_days * 0.6:
            out.append("<i>" + pick(DNP, seed + 10).format(
                p=p, n=total_days - d, played=d, total=total_days) + "</i>")
    return "\n".join(out).strip()


def send(text: str):
    import requests
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                            "disable_web_page_preview": True}, timeout=30)
    r.raise_for_status()
    print("Sent.")


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if kind not in ("weekly", "monthly"):
        sys.exit(__doc__)
    msg = build(kind, date.today())
    if "--dry-run" in sys.argv:
        print(msg)
    else:
        send(msg)
