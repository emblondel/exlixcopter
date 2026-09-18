import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "flashcards.db"

MODES = ("recognize", "produce")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    part_of_speech TEXT,
    definition TEXT,
    source_url TEXT,
    video_url TEXT NOT NULL,
    video_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK(mode IN ('recognize', 'produce')),
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days REAL NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    due_at TEXT NOT NULL,
    last_reviewed_at TEXT,
    PRIMARY KEY (card_id, mode)
);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_srs_columns_into_progress(conn: sqlite3.Connection) -> None:
    """One-time migration: the old schema kept a single SM-2 state per card,
    shared by both review directions. Split it into a per-mode `progress`
    row so 'recognize' (video -> word) and 'produce' (word -> sign) track
    independently -- knowing a sign one way doesn't mean you know it the
    other way. The old shared state becomes the 'recognize' history (the
    only direction that existed before modes were introduced); 'produce'
    starts fresh.
    """
    old_cards = conn.execute(
        """
        SELECT id, ease_factor, interval_days, repetitions, lapses, due_at, last_reviewed_at, created_at
        FROM cards
        """
    ).fetchall()

    conn.execute("ALTER TABLE cards RENAME TO cards_old")
    conn.execute(
        """
        CREATE TABLE cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            part_of_speech TEXT,
            definition TEXT,
            source_url TEXT,
            video_url TEXT NOT NULL,
            video_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO cards (id, word, part_of_speech, definition, source_url, video_url, video_path, created_at)
        SELECT id, word, part_of_speech, definition, source_url, video_url, video_path, created_at FROM cards_old
        """
    )
    conn.execute(
        """
        CREATE TABLE progress (
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            mode TEXT NOT NULL CHECK(mode IN ('recognize', 'produce')),
            ease_factor REAL NOT NULL DEFAULT 2.5,
            interval_days REAL NOT NULL DEFAULT 0,
            repetitions INTEGER NOT NULL DEFAULT 0,
            lapses INTEGER NOT NULL DEFAULT 0,
            due_at TEXT NOT NULL,
            last_reviewed_at TEXT,
            PRIMARY KEY (card_id, mode)
        )
        """
    )
    for row in old_cards:
        conn.execute(
            """
            INSERT INTO progress (card_id, mode, ease_factor, interval_days, repetitions, lapses, due_at, last_reviewed_at)
            VALUES (?, 'recognize', ?, ?, ?, ?, ?, ?)
            """,
            (row["id"], row["ease_factor"], row["interval_days"], row["repetitions"], row["lapses"], row["due_at"], row["last_reviewed_at"]),
        )
        conn.execute(
            """
            INSERT INTO progress (card_id, mode, ease_factor, interval_days, repetitions, lapses, due_at, last_reviewed_at)
            VALUES (?, 'produce', 2.5, 0, 0, 0, ?, NULL)
            """,
            (row["id"], row["created_at"]),
        )
    conn.execute("DROP TABLE cards_old")


def init_db() -> None:
    conn = get_conn()
    try:
        existing_tables = {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "cards" in existing_tables and "ease_factor" in _column_names(conn, "cards"):
            _migrate_srs_columns_into_progress(conn)
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
