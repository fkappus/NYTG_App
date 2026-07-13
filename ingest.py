"""Poll Telegram getUpdates for new messages and ingest game results.

Env vars:
  TELEGRAM_BOT_TOKEN  (required)
  TELEGRAM_CHAT_ID    (optional; if set, only messages from this chat count)

Run: python ingest.py
Idempotent: stores the last processed update_id in the DB.
"""

import os
import sys
from datetime import datetime, timezone

import requests

import db
from nyt_parser import parse_message

API = "https://api.telegram.org/bot{token}/{method}"


def fetch_updates(token: str, offset: int | None):
    params = {"timeout": 0, "allowed_updates": '["message"]', "limit": 100}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(API.format(token=token, method="getUpdates"),
                     params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data["result"]


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN is not set")
    chat_filter = os.environ.get("TELEGRAM_CHAT_ID")

    conn = db.connect()
    offset = db.get_meta(conn, "last_update_id")
    offset = int(offset) + 1 if offset is not None else None

    new_rows, seen_updates = 0, 0
    while True:
        updates = fetch_updates(token, offset)
        if not updates:
            break
        for u in updates:
            seen_updates += 1
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            text = msg.get("text") or msg.get("caption") or ""
            chat_id = str((msg.get("chat") or {}).get("id", ""))
            if chat_filter and chat_id != chat_filter:
                continue
            frm = msg.get("from") or {}
            player_id = frm.get("id")
            if player_id is None:
                continue
            name = " ".join(filter(None, [frm.get("first_name"),
                                          frm.get("last_name")])) \
                or frm.get("username") or str(player_id)
            ts = datetime.fromtimestamp(msg.get("date", 0),
                                        tz=timezone.utc).isoformat()
            for parsed in parse_message(text):
                if db.upsert_result(conn, player_id, name, ts, parsed):
                    new_rows += 1
        db.set_meta(conn, "last_update_id", offset - 1)
        conn.commit()

    conn.commit()
    conn.close()
    print(f"Processed {seen_updates} update(s); {new_rows} new result(s).")


if __name__ == "__main__":
    main()
