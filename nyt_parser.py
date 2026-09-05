"""Parse NYT Games share texts from chat messages.

Games: wordle, connections, wordle_in_1, connections_3x3.
"""

import re
from datetime import date, datetime, timedelta

WORDLE_EPOCH = date(2021, 6, 19)       # Wordle #0
CONNECTIONS_EPOCH = date(2023, 6, 11)  # Puzzle #1 = 2023-06-12

WORDLE_RE = re.compile(r"Wordle\s+([\d,.\u202f\s]+?)\s+([1-6Xx])/6(\*)?")
CONNECTIONS_RE = re.compile(r"Connections\s*\n\s*Puzzle\s*#?([\d,.]+)",
                            re.IGNORECASE)
WORDLE1_RE = re.compile(r"Wordle in 1\b")
C3_RE = re.compile(r"Connections 3x3\b")
BONUS_DATE_RE = re.compile(r"Bonus\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

SQ = "\u2b1b\u2b1c\U0001f7e8\U0001f7e9\U0001f7e7\U0001f7e6\U0001f7ea"
WORDLE_ROW_RE = re.compile(rf"^[{SQ}]{{5}}$")
CONNECTIONS_ROW_RE = re.compile(r"^[\U0001f7e8\U0001f7e9\U0001f7e6\U0001f7ea]{4}$")
C3_ROW_RE = re.compile(r"^[\U0001f7e8\U0001f7e9\U0001f7e6\U0001f7ea]{3}$")


def _clean_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _grid_rows(text: str, row_re: re.Pattern) -> list[str]:
    rows = []
    for line in text.splitlines():
        line = line.strip().replace("\ufe0f", "")
        # allow trailing text on a row (e.g. "🟩🟩🟩🟩🟩 3:59")
        token = line.split(" ")[0] if line else line
        if row_re.match(token):
            rows.append(token)
    return rows


def _bonus_date(text: str):
    m = BONUS_DATE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%B %d, %Y").date()
    except ValueError:
        return None


def parse_wordle(text: str) -> dict | None:
    m = WORDLE_RE.search(text)
    if not m:
        return None
    puzzle = _clean_int(m.group(1))
    result = m.group(2).upper()
    guesses = 7 if result == "X" else int(result)  # 7 = failed
    rows = _grid_rows(text[m.end():], WORDLE_ROW_RE)
    return {"game": "wordle", "puzzle_number": puzzle,
            "puzzle_date": (WORDLE_EPOCH + timedelta(days=puzzle)).isoformat(),
            "score": guesses, "solved": 1 if result != "X" else 0,
            "hard_mode": 1 if m.group(3) else 0, "raw": "\n".join(rows)}


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
    return {"game": "connections", "puzzle_number": puzzle,
            "puzzle_date": (CONNECTIONS_EPOCH + timedelta(days=puzzle)).isoformat(),
            "score": mistakes, "solved": 1 if correct == 4 else 0,
            "hard_mode": 0, "raw": "\n".join(rows)}


def parse_wordle_in_1(text: str) -> dict | None:
    """One-guess Wordle. solved = all-green row; score = seconds (if solved)."""
    if not WORDLE1_RE.search(text):
        return None
    d = _bonus_date(text)
    rows = _grid_rows(text, WORDLE_ROW_RE)
    if d is None or not rows:
        return None
    solved = 1 if rows[-1] in ("🟩🟩🟩🟩🟩", "🟧🟧🟧🟧🟧") else 0
    tail = text.split(rows[-1], 1)[-1]
    t = TIME_RE.search(tail)
    secs = int(t.group(1)) * 60 + int(t.group(2)) if t else None
    return {"game": "wordle_in_1", "puzzle_number": d.toordinal(),
            "puzzle_date": d.isoformat(), "score": secs if solved else None,
            "solved": solved, "hard_mode": 0, "raw": "\n".join(rows)}


def parse_connections_3x3(text: str) -> dict | None:
    """Three groups of three. score = mistakes; solved = 3 clean rows."""
    if not C3_RE.search(text):
        return None
    d = _bonus_date(text)
    rows = _grid_rows(text, C3_ROW_RE)
    if d is None or not rows:
        return None
    correct = sum(1 for r in rows if len(set(r)) == 1)
    mistakes = sum(1 for r in rows if len(set(r)) > 1)
    return {"game": "connections_3x3", "puzzle_number": d.toordinal(),
            "puzzle_date": d.isoformat(), "score": mistakes,
            "solved": 1 if correct == 3 else 0, "hard_mode": 0,
            "raw": "\n".join(rows)}


def parse_message(text: str) -> list[dict]:
    """A single message may contain several games."""
    if not text:
        return []
    if WORDLE1_RE.search(text):
        r = parse_wordle_in_1(text)
        return [r] if r else []
    if C3_RE.search(text):
        r = parse_connections_3x3(text)
        return [r] if r else []
    results = []
    for fn in (parse_wordle, parse_connections):
        r = fn(text)
        if r:
            results.append(r)
    return results
