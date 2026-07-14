"""Merge duplicate players in results.db.

Usage:
  python3 merge_players.py                 -> list all players with IDs
  python3 merge_players.py FROM_ID TO_ID   -> move FROM's results onto TO

Rows that exist for both (same game + puzzle, from the switchover overlap)
are dropped from FROM and TO's copy is kept. Run once per duplicate pair.
"""

import sqlite3
import sys

conn = sqlite3.connect("results.db")

if len(sys.argv) == 1:
    print(f"{'player_id':>15}  {'results':>7}  name")
    for pid, name, n in conn.execute(
            "SELECT player_id, player_name, COUNT(*) FROM results "
            "GROUP BY player_id ORDER BY player_name"):
        print(f"{pid:>15}  {n:>7}  {name}")
    print("\nMerge with: python3 merge_players.py FROM_ID TO_ID")
    print("(FROM = the duplicate to absorb, TO = the Telegram identity "
          "to keep)")
    sys.exit(0)

if len(sys.argv) != 3:
    sys.exit(__doc__)

frm, to = int(sys.argv[1]), int(sys.argv[2])
names = dict(conn.execute(
    "SELECT player_id, player_name FROM results "
    "WHERE player_id IN (?,?) GROUP BY player_id", (frm, to)))
if frm not in names or to not in names:
    sys.exit(f"Unknown ID(s). Known: {names}")

dup = conn.execute(
    """SELECT COUNT(*) FROM results a WHERE a.player_id=? AND EXISTS
       (SELECT 1 FROM results b WHERE b.player_id=? AND b.game=a.game
        AND b.puzzle_number=a.puzzle_number)""", (frm, to)).fetchone()[0]
conn.execute(
    """DELETE FROM results WHERE player_id=? AND EXISTS
       (SELECT 1 FROM results b WHERE b.player_id=? AND b.game=results.game
        AND b.puzzle_number=results.puzzle_number)""", (frm, to))
moved = conn.execute(
    "UPDATE results SET player_id=?, player_name=? WHERE player_id=?",
    (to, names[to], frm)).rowcount
conn.commit()
print(f"Merged '{names[frm]}' ({frm}) into '{names[to]}' ({to}): "
      f"{moved} results moved, {dup} overlap duplicate(s) dropped.")
