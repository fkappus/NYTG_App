"""One-time backfill from a Telegram Desktop chat export (result.json).

Telegram Desktop > open the group > three-dot menu > Export chat history
> format: JSON, no media needed.

Run: python backfill.py path/to/result.json
Idempotent: safe to run multiple times.
"""

import json
import re
import sys

import db
from nyt_parser import parse_message


def flatten_text(t) -> str:
    """Export 'text' can be a string or a list of strings/entity dicts."""
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        return "".join(p if isinstance(p, str) else p.get("text", "")
                       for p in t)
    return ""


def main(path: str):
    with open(path, encoding="utf-8") as f:
        export = json.load(f)

    conn = db.connect()
    new_rows = 0
    for msg in export.get("messages", []):
        if msg.get("type") != "message":
            continue
        text = flatten_text(msg.get("text"))
        from_id = str(msg.get("from_id", ""))
        m = re.search(r"(\d+)$", from_id)
        if not m:
            continue
        player_id = int(m.group(1))
        name = msg.get("from") or str(player_id)
        ts = msg.get("date", "")
        for parsed in parse_message(text):
            if db.upsert_result(conn, player_id, name, ts, parsed):
                new_rows += 1
    conn.commit()
    conn.close()
    print(f"Backfill complete: {new_rows} new result(s).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python backfill.py path/to/result.json")
    main(sys.argv[1])
