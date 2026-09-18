"""SM-2 spaced-repetition scheduling (the algorithm behind Anki/SuperMemo).

Cards you get wrong drop back to a short interval and a lower ease factor,
so they come due again soon and keep resurfacing until they stick. Cards you
consistently know grow their interval and are shown less and less often.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# UI grades mapped to classic SM-2 quality (0-5)
GRADE_QUALITY = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
}

MIN_EASE = 1.3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def schedule(
    grade: str,
    ease_factor: float,
    interval_days: float,
    repetitions: int,
) -> dict:
    """Compute the next SM-2 state for a card given a review grade."""
    quality = GRADE_QUALITY[grade]

    if quality < 3:
        # Lapse: reset progress but keep it in the deck for a same-day retry.
        repetitions = 0
        interval_days = 1 / 24  # ~1 hour, so it resurfaces this session
        lapse = 1
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor, 2)
        repetitions += 1
        lapse = 0

    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease_factor = max(MIN_EASE, round(ease_factor, 2))

    due_at = datetime.now(timezone.utc) + timedelta(days=interval_days)

    return {
        "ease_factor": ease_factor,
        "interval_days": interval_days,
        "repetitions": repetitions,
        "due_at": due_at.isoformat(),
        "last_reviewed_at": now_iso(),
        "lapse": lapse,
    }


def proficiency(ease_factor: float, repetitions: int, lapses: int) -> str:
    """A rough 'how well known' label used to visually flag weak cards."""
    if repetitions == 0:
        return "new"
    if lapses >= 2 or ease_factor <= 1.8:
        return "weak"
    if ease_factor >= 2.4 and repetitions >= 3:
        return "strong"
    return "learning"
