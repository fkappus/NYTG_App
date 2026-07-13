"""Backfill from a WhatsApp iOS chat export (_chat.txt).

WhatsApp exports have no user IDs, only display names. To merge each
friend's WhatsApp history with their Telegram identity, this script uses
name_map.csv (whatsapp_name,player_id,player_name).

Usage:
  python whatsapp_backfill.py path/to/_chat.txt
    First run: if name_map.csv is missing, a template is generated from
    the sender names found in the export plus the players already in
    results.db. Fill in the blanks, then run again.

For friends who never joined Telegram, leave player_id empty in the CSV
and run with --allow-unmapped: they get a stable synthetic (negative) ID.
Idempotent: safe to re-run.
"""

import csv
import re
import sys
import zlib
from datetime import datetime
from pathlib import Path

import db
from nyt_parser import parse_message

MAP_PATH = Path("name_map.csv")

# iOS export line: [date, time] Name: message   (optionally prefixed with
# invisible marks). Also matches Android's "date, time - Name: message".
MSG_RE = re.compile(
    r"^[\u200e\u200f\ufeff]*"
    r"(?:\[(?P<ts1>[^\]]+)\]\s|(?P<ts2>[^-\n]{6,25})\s-\s)"
    r"(?P<name>[^:]+?):\s?(?P<text>.*)$"
)

DATE_FORMATS = [
    "%d.%m.%y, %H:%M:%S", "%d.%m.%Y, %H:%M:%S",   # German iOS
    "%m/%d/%y, %H:%M:%S", "%m/%d/%Y, %H:%M:%S",   # US iOS
    "%d/%m/%y, %H:%M:%S", "%d/%m/%Y, %H:%M:%S",
    "%d.%m.%y, %H:%M", "%m/%d/%y, %H:%M", "%d/%m/%y, %H:%M",  # Android
]


def parse_ts(raw: str) -> str:
    raw = raw.strip().replace("\u202f", " ")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return raw  # keep raw string if the locale format is unknown


def iter_messages(path: str):
    """Yield (timestamp, name, full_text) — continuation lines re-joined."""
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = MSG_RE.match(line)
            if m:
                if cur:
                    yield cur
                cur = [parse_ts(m.group("ts1") or m.group("ts2")),
                       m.group("name").strip("\u200e\u200f ").strip(),
                       m.group("text")]
            elif cur:
                cur[2] += "\n" + line.lstrip("\u200e\u200f")
    if cur:
        yield cur


def load_map() -> dict:
    mapping = {}
    with open(MAP_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            wa = (row.get("whatsapp_name") or "").strip()
            if not wa:
                continue
            pid = (row.get("player_id") or "").strip()
            mapping[wa] = {
                "player_id": int(pid) if pid else None,
                "player_name": (row.get("player_name") or wa).strip(),
            }
    return mapping


def write_template(names: set):
    conn = db.connect()
    known = conn.execute(
        "SELECT DISTINCT player_id, player_name FROM results "
        "ORDER BY player_name").fetchall()
    conn.close()
    with open(MAP_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["whatsapp_name", "player_id", "player_name"])
        for n in sorted(names):
            w.writerow([n, "", ""])
    print(f"Created {MAP_PATH} with {len(names)} WhatsApp name(s).")
    print("Fill in player_id / player_name, then re-run this script.")
    if known:
        print("\nKnown players in results.db (from Telegram):")
        for pid, name in known:
            print(f"  {pid}\t{name}")
    else:
        print("\nNo players in results.db yet — run the Telegram backfill "
              "first so you can map WhatsApp names to Telegram IDs.")


def synthetic_id(name: str) -> int:
    return -int(zlib.crc32(name.encode("utf-8")))  # stable, negative


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_unmapped = "--allow-unmapped" in sys.argv
    if len(args) != 1:
        sys.exit("Usage: python whatsapp_backfill.py path/to/_chat.txt "
                 "[--allow-unmapped]")
    chat_path = args[0]

    messages = list(iter_messages(chat_path))
    senders = {name for _, name, _ in messages}
    print(f"Found {len(messages)} message(s) from {len(senders)} sender(s).")

    if not MAP_PATH.exists():
        write_template(senders)
        return

    mapping = load_map()
    unmapped = sorted(n for n in senders
                      if n not in mapping or mapping[n]["player_id"] is None)
    if unmapped and not allow_unmapped:
        print("These WhatsApp names have no player_id in name_map.csv:")
        for n in unmapped:
            print(f"  {n}")
        sys.exit("Fill them in, or re-run with --allow-unmapped to give "
                 "them synthetic IDs.")

    conn = db.connect()
    new_rows = 0
    for ts, name, text in messages:
        parsed_list = parse_message(text)
        if not parsed_list:
            continue
        entry = mapping.get(name) or {}
        pid = entry.get("player_id") or synthetic_id(name)
        pname = entry.get("player_name") or name
        for parsed in parsed_list:
            if db.upsert_result(conn, pid, pname, ts, parsed):
                new_rows += 1
    conn.commit()
    conn.close()
    print(f"WhatsApp backfill complete: {new_rows} new result(s).")


if __name__ == "__main__":
    main()
