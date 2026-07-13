"""Parse NYT Games share texts (Wordle, Connections) from chat messages."""

import re
from datetime import date, timedelta

WORDLE_EPOCH = date(2021, 6, 19)       # Wordle #0
CONNECTIONS_EPOCH = date(2023, 6, 11)  # Puzzle #1 = 2023-06-12

WORDLE_RE = re.compile(r"Wordle\s+([\d,.\u202f\s]+?)\s+([1-6Xx])/6(\*)?")
CONNECTIONS_RE = re.compile(r"Connections\s*\n\s*Puzzle\s*#?([\d,.]+)", re.IGNORECASE)

# Wordle rows: green/yellow (or orange/blue in high-contrast mode) + black/white absent
WORDLE_ROW_RE = re.compile(r"^[\u2b1b\u2b1c\U0001f7e8\U0001f7e9\U0001f7e7\U0001f7e6]{5}$")
# Connections rows: yellow/green/blue/purple squares
CONNECTIONS_ROW_RE = re.compile(r"^[\U0001f7e8\U0001f7e9\U0001f7e6\U0001f7ea]{4}$")


def _clean_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _grid_rows(text: str, row_re: re.Pattern) -> list[str]:
    rows = []
    for line in text.splitlines():
        line = line.strip().replace("\ufe0f", "")
        if row_re.match(line):
            rows.append(line)
    return rows


def parse_wordle(text: str) -> dict | None:
    m = WORDLE_RE.search(text)
    if not m:
        return None
    puzzle = _clean_int(m.group(1))
    result = m.group(2).upper()
    guesses = 7 if result == "X" else int(result)  # 7 = failed
    rows = _grid_rows(text[m.end():], WORDLE_ROW_RE)
    return {
        "game": "wordle",
        "puzzle_number": puzzle,
        "puzzle_date": (WORDLE_EPOCH + timedelta(days=puzzle)).isoformat(),
        "score": guesses,
        "solved": 1 if result != "X" else 0,
        "hard_mode": 1 if m.group(3) else 0,
        "raw": "\n".join(rows),
    }


def parse_connections(text: str) -> dict | None:
    m = CONNECTIONS_RE.search(text)
    if not m:
        return None
    puzzle = _clean_int(m.group(1))
    rows = _grid_rows(text[m.end():], CONNECTIONS_ROW_RE)
    if not rows:
        return None
    correct = sum(1 for r in rows if len(set(r)) == 1)
    mistakes = sum(1 for r in rows if len(set(r)) > 1)
    return {
        "game": "connections",
        "puzzle_number": puzzle,
        "puzzle_date": (CONNECTIONS_EPOCH + timedelta(days=puzzle)).isoformat(),
        "score": mistakes,               # 0 = perfect, 4 = failed out
        "solved": 1 if correct == 4 else 0,
        "hard_mode": 0,
        "raw": "\n".join(rows),
    }


def parse_message(text: str) -> list[dict]:
    """A single message can theoretically contain both games."""
    if not text:
        return []
    results = []
    for fn in (parse_wordle, parse_connections):
        r = fn(text)
        if r:
            results.append(r)
    return results
