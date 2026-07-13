"""SQLite storage with idempotent upserts."""

import sqlite3

DB_PATH = "results.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    player_id     INTEGER NOT NULL,
    player_name   TEXT,
    game          TEXT    NOT NULL,
    puzzle_number INTEGER NOT NULL,
    puzzle_date   TEXT,
    score         INTEGER,
    solved        INTEGER,
    hard_mode     INTEGER,
    raw           TEXT,
    message_ts    TEXT,
    PRIMARY KEY (player_id, game, puzzle_number)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def upsert_result(conn, player_id, player_name, message_ts, parsed) -> bool:
    """Insert or refresh a result. Returns True if a new row was inserted."""
    existed = conn.execute(
        "SELECT 1 FROM results WHERE player_id=? AND game=? AND puzzle_number=?",
        (player_id, parsed["game"], parsed["puzzle_number"]),
    ).fetchone() is not None
    conn.execute(
        """INSERT INTO results
           (player_id, player_name, game, puzzle_number, puzzle_date,
            score, solved, hard_mode, raw, message_ts)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(player_id, game, puzzle_number) DO UPDATE SET
             player_name=excluded.player_name""",
        (player_id, player_name, parsed["game"], parsed["puzzle_number"],
         parsed["puzzle_date"], parsed["score"], parsed["solved"],
         parsed["hard_mode"], parsed["raw"], message_ts),
    )
    return not existed


def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
