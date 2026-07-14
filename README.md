# Bermuda Triangle 🍪 — NYT Games Tracker

## What this is

Our friend group shares daily [New York Times Games](https://www.nytimes.com/crosswords) results — **Wordle** and **Connections** — in a Telegram group chat. This project automatically collects those share messages, parses them into structured data, and serves a live leaderboard dashboard.

No one has to do anything: post your result in the group like always, and it shows up on the dashboard after the next update. The full history is included, all the way back to the original WhatsApp group (September 2025) from before we switched to Telegram.

**How it works:**

```
Telegram group ──► bot reads new messages
                        │  (GitHub Actions, daily at noon)
                        ▼
                  ingest.py parses Wordle / Connections share texts
                        │
                        ▼
                  results.db (SQLite, committed to this repo)
                        │
                        ▼
                  Streamlit dashboard (auto-redeploys on every commit)
```

## For players

- **Dashboard:** https://YOUR-APP-NAME.streamlit.app *(ask in the group for the link and password)*
- Post your results in the Telegram group using the official **Share** button in the NYT app — that exact format is what the parser understands. Typed-out results or screenshots are ignored.
- Data updates **daily at noon** (German time). Results posted after noon appear the next day. The "last refreshed" stamp under the title shows how current the data is.
- What you'll find: current play streaks per game, podium rankings by average attempts/mistakes, and guess/mistake distributions — filterable by day, last 7 days, last 30 days, or all-time.
- Scoring: Wordle = number of guesses (X counts as 7). Connections = number of mistakes (0 = perfect).
- Tip: on iPhone, open the dashboard in Safari → Share → **Add to Home Screen** for an app-like experience.

## Setup (for whoever maintains this)

**Components**

| File | Purpose |
|---|---|
| `nyt_parser.py` | Regex parsing of Wordle / Connections share texts |
| `db.py` | SQLite schema + idempotent upserts (keyed on player + game + puzzle) |
| `ingest.py` | Polls the Telegram Bot API for new messages |
| `backfill.py` | One-time import from a Telegram Desktop JSON export |
| `whatsapp_backfill.py` | One-time import from a WhatsApp iOS export (uses `name_map.csv`) |
| `app.py` | The Streamlit dashboard (display names are set in `DISPLAY_NAMES` at the top) |
| `.github/workflows/ingest.yml` | Scheduled ingest; commits the updated DB back to the repo |

**One-time setup steps**

1. Create a bot via @BotFather, **disable Group Privacy** (Bot Settings → Group Privacy → off), and add it to the group. The bot only sees messages sent after it joins.
2. Get the group chat ID (negative number) from `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending a message in the group.
3. Add two GitHub Actions secrets on this repo: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. Run the **Ingest NYT results** workflow once manually (Actions tab) to verify; after that it runs on schedule.
5. Deploy on [Streamlit Community Cloud](https://share.streamlit.io): point it at this repo, main file `app.py`. Optional password: add `APP_PASSWORD = "..."` in the app's Streamlit secrets.
6. History imports (already done, kept for reference): `python backfill.py result.json` for Telegram Desktop exports, `python whatsapp_backfill.py _chat.txt` for WhatsApp exports.

**Maintenance notes**

- The Action commits to this repo, so **always `git pull --rebase` before pushing** local changes.
- Re-running any ingest or backfill is safe — everything upserts on (player, game, puzzle number).
- Need fresh data right now? Actions tab → *Ingest NYT results* → **Run workflow**.
- The bot token lives only in Actions secrets. If it ever leaks, revoke it via @BotFather and update the secret.
