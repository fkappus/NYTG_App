"""Write streaks.json (current + longest streak per player per game).

Runs automatically after each ingest; can also be run standalone:
  python3 export_streaks.py
"""

import json
import sqlite3
from datetime import datetime, timezone

# Keep in sync with DISPLAY_NAMES in app.py.
DISPLAY_NAMES = {
    8983515512: "Finn",
    5182590002: "Peter",
    1197776677: "Stella",
}

GAMES = ("wordle", "connections")


def streaks(days: list) -> tuple[int, int]:
    """Return (current, longest) run of consecutive days."""
    if not days:
        return 0, 0
    longest = run = 1
    for a, b in zip(days, days[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        longest = max(longest, run)
    return run, longest


def export(db_path: str = "results.db", out: str = "streaks.json"):
    conn = sqlite3.connect(db_path)
    latest_overall = conn.execute(
        "SELECT MAX(puzzle_date) FROM results").fetchone()[0]
    if latest_overall is None:
        return
    latest_overall = datetime.fromisoformat(latest_overall).date()

    name_of = dict(conn.execute(
        """SELECT player_id, player_name FROM results r
           WHERE message_ts = (SELECT MAX(message_ts) FROM results
                               WHERE player_id = r.player_id)
           GROUP BY player_id"""))
    players = []
    for pid in sorted(name_of, key=lambda i: DISPLAY_NAMES.get(i,
                                                               name_of[i])):
        entry = {"name": DISPLAY_NAMES.get(pid, name_of[pid])}
        for game in GAMES:
            days = [datetime.fromisoformat(r[0]).date() for r in
                    conn.execute(
                        "SELECT DISTINCT puzzle_date FROM results WHERE "
                        "player_id=? AND game=? ORDER BY puzzle_date",
                        (pid, game))]
            cur, longest = streaks(days)
            if days and (latest_overall - days[-1]).days > 1:
                cur = 0
            entry[game] = {"current": cur, "longest": longest}
        players.append(entry)
    conn.close()

    with open(out, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc)
                   .strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "data_through": latest_overall.isoformat(),
                   "players": players}, f, ensure_ascii=False, indent=1)
    print(f"Wrote {out} for {len(players)} player(s).")


if __name__ == "__main__":
    export()
