# NYT Games Group Tracker

Automatically collects Wordle and Connections results shared in a Telegram
group and serves an interactive leaderboard.

**Pipeline:** Telegram bot → GitHub Actions (every 6 h) → `ingest.py` →
`results.db` (SQLite, committed to this repo) → Streamlit dashboard.

## Files

| File | Purpose |
|---|---|
| `nyt_parser.py` | Regex parsing of Wordle / Connections share texts |
| `db.py` | SQLite schema + idempotent upserts |
| `ingest.py` | Polls Telegram `getUpdates`, ingests new results |
| `backfill.py` | One-time import from a Telegram Desktop JSON export |
| `app.py` | Streamlit dashboard |
| `.github/workflows/ingest.yml` | Scheduled ingest, commits DB back |

## Setup (one time)

1. **Bot prep** (already done if your bot is set up): via @BotFather →
   Bot Settings → *Group Privacy* → **Turn off**, then add the bot to the
   group. If it was in the group before disabling privacy, remove and
   re-add it.
2. **Get the group chat ID**: send any message in the group, then open
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and
   find `"chat":{"id":-100…}`. Group IDs are negative.
3. **Create a GitHub repo** with these files and add two
   *Actions secrets* (Settings → Secrets and variables → Actions):
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. **Run the workflow once** manually: Actions tab → *Ingest NYT results*
   → *Run workflow*. It commits an updated `results.db` when it finds
   share messages.
5. **Deploy the dashboard**: [share.streamlit.io](https://share.streamlit.io)
   → New app → point at this repo, main file `app.py`. Optional password:
   app Settings → Secrets → add `APP_PASSWORD = "yourpassword"`.
6. **Optional backfill of old messages**: Telegram Desktop → open group →
   ⋮ → *Export chat history* → format **JSON**, media off. Then locally:
   `python backfill.py path/to/result.json`, commit `results.db`, push.

## Notes

- Telegram only retains unfetched updates ~24 h, so the 6-hour cron never
  misses messages. The bot only sees messages sent **after** it joined —
  use the backfill for anything earlier.
- Re-running ingest or backfill is always safe (upsert on
  player + game + puzzle number).
- Scores: Wordle `score` = guesses (7 = fail); Connections `score` =
  mistakes (0 = perfect).
