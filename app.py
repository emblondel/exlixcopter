import io
import re
import sqlite3
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import db
import elix_scraper
import srs

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "media" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
db.init_db()


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "mot"


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/search")
def api_search():
    word = request.args.get("q", "").strip()
    if not word:
        return jsonify({"error": "missing query"}), 400
    try:
        result = elix_scraper.search_word(word)
    except Exception as exc:  # noqa: BLE001 - surface scrape failures to the UI
        return jsonify({"error": str(exc)}), 502

    all_urls = {u for m in result["meanings"] for u in m["video_urls"]}
    saved = {}
    if all_urls:
        conn = db.get_conn()
        try:
            placeholders = ",".join("?" for _ in all_urls)
            rows = conn.execute(
                f"SELECT id, video_url FROM cards WHERE video_url IN ({placeholders})",
                tuple(all_urls),
            ).fetchall()
            saved = {r["video_url"]: r["id"] for r in rows}
        finally:
            conn.close()
    result["saved"] = saved
    return jsonify(result)


@app.post("/api/cards")
def api_create_card():
    data = request.get_json(force=True)
    word = (data.get("word") or "").strip()
    video_url = (data.get("video_url") or "").strip()
    definition = (data.get("definition") or "").strip()
    part_of_speech = (data.get("part_of_speech") or "").strip()
    source_url = (data.get("source_url") or "").strip()

    if not word or not video_url:
        return jsonify({"error": "word and video_url are required"}), 400

    conn = db.get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM cards WHERE video_url = ?", (video_url,)
        ).fetchone()
        if existing:
            return jsonify({"error": "This video is already saved as a flashcard", "id": existing["id"]}), 409

        slug = slugify(word)
        count = conn.execute(
            "SELECT COUNT(*) c FROM cards WHERE word = ?", (word,)
        ).fetchone()["c"]
        filename = f"{slug}-{count + 1}.mp4"
        dest_path = VIDEO_DIR / filename

        elix_scraper.download_video(video_url, str(dest_path))

        now = srs.now_iso()
        cur = conn.execute(
            """
            INSERT INTO cards (word, part_of_speech, definition, source_url, video_url, video_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (word, part_of_speech, definition, source_url, video_url, f"videos/{filename}", now),
        )
        card_id = cur.lastrowid
        for mode in db.MODES:
            conn.execute(
                "INSERT INTO progress (card_id, mode, due_at) VALUES (?, ?, ?)",
                (card_id, mode, now),
            )
        conn.commit()
        card = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return jsonify(deck_card_to_dict(conn, card)), 201
    finally:
        conn.close()


@app.get("/api/cards")
def api_list_cards():
    conn = db.get_conn()
    try:
        rows = conn.execute("SELECT * FROM cards ORDER BY created_at DESC").fetchall()
        return jsonify([deck_card_to_dict(conn, r) for r in rows])
    finally:
        conn.close()


@app.delete("/api/cards/<int:card_id>")
def api_delete_card(card_id: int):
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        video_file = BASE_DIR / "media" / row["video_path"]
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        conn.commit()
        if video_file.exists():
            video_file.unlink()
        return jsonify({"ok": True})
    finally:
        conn.close()


@app.get("/api/review/next")
def api_review_next():
    mode = request.args.get("mode", "recognize")
    if mode not in db.MODES:
        return jsonify({"error": "mode must be one of recognize/produce"}), 400

    conn = db.get_conn()
    try:
        now = srs.now_iso()
        row = conn.execute(
            """
            SELECT cards.*, progress.ease_factor, progress.interval_days, progress.repetitions,
                   progress.lapses, progress.due_at, progress.last_reviewed_at
            FROM cards JOIN progress ON progress.card_id = cards.id
            WHERE progress.mode = ? AND progress.due_at <= ?
            ORDER BY progress.due_at ASC LIMIT 1
            """,
            (mode, now),
        ).fetchone()
        if not row:
            next_due = conn.execute(
                "SELECT due_at FROM progress WHERE mode = ? ORDER BY due_at ASC LIMIT 1",
                (mode,),
            ).fetchone()
            return jsonify({"card": None, "next_due_at": next_due["due_at"] if next_due else None})
        return jsonify({"card": review_card_to_dict(row), "next_due_at": None})
    finally:
        conn.close()


@app.post("/api/review/<int:card_id>")
def api_review_submit(card_id: int):
    data = request.get_json(force=True)
    grade = data.get("grade")
    mode = data.get("mode", "recognize")
    if grade not in srs.GRADE_QUALITY:
        return jsonify({"error": "grade must be one of again/hard/good/easy"}), 400
    if mode not in db.MODES:
        return jsonify({"error": "mode must be one of recognize/produce"}), 400

    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM progress WHERE card_id = ? AND mode = ?", (card_id, mode)
        ).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        result = srs.schedule(grade, row["ease_factor"], row["interval_days"], row["repetitions"])
        conn.execute(
            """
            UPDATE progress SET ease_factor=?, interval_days=?, repetitions=?, due_at=?,
                                 last_reviewed_at=?, lapses = lapses + ?
            WHERE card_id=? AND mode=?
            """,
            (
                result["ease_factor"],
                result["interval_days"],
                result["repetitions"],
                result["due_at"],
                result["last_reviewed_at"],
                result["lapse"],
                card_id,
                mode,
            ),
        )
        conn.commit()
        updated = conn.execute(
            """
            SELECT cards.*, progress.ease_factor, progress.interval_days, progress.repetitions,
                   progress.lapses, progress.due_at, progress.last_reviewed_at
            FROM cards JOIN progress ON progress.card_id = cards.id
            WHERE cards.id = ? AND progress.mode = ?
            """,
            (card_id, mode),
        ).fetchone()
        return jsonify(review_card_to_dict(updated))
    finally:
        conn.close()


@app.get("/media/<path:filename>")
def media(filename: str):
    return send_from_directory(BASE_DIR / "media", filename)


@app.get("/api/backup")
def api_backup():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if db.DB_PATH.exists():
            zf.writestr("data/flashcards.db", _consistent_db_snapshot())
        for video_file in sorted(VIDEO_DIR.glob("*.mp4")):
            zf.write(video_file, arcname=f"media/videos/{video_file.name}")

    buffer.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"elixcopter-backup-{timestamp}.zip",
    )


def _consistent_db_snapshot() -> bytes:
    """Copy the SQLite file via the backup API rather than reading its bytes
    directly, so a concurrent write from another request can't land us a
    torn/inconsistent copy.
    """
    source = sqlite3.connect(db.DB_PATH)
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "flashcards.db"
            dest = sqlite3.connect(tmp_path)
            try:
                source.backup(dest)
            finally:
                dest.close()
            return tmp_path.read_bytes()
    finally:
        source.close()


def review_card_to_dict(row) -> dict:
    """Flat shape used during an active review session (single mode's progress)."""
    d = dict(row)
    d["proficiency"] = srs.proficiency(row["ease_factor"], row["repetitions"], row["lapses"])
    d["video_src"] = f"/media/{row['video_path']}"
    return d


def deck_card_to_dict(conn, row) -> dict:
    """Shape used for the deck listing: card info plus both modes' progress."""
    d = dict(row)
    d["video_src"] = f"/media/{row['video_path']}"
    progress_rows = conn.execute(
        "SELECT * FROM progress WHERE card_id = ?", (row["id"],)
    ).fetchall()
    progress = {}
    for p in progress_rows:
        progress[p["mode"]] = {
            "ease_factor": p["ease_factor"],
            "interval_days": p["interval_days"],
            "repetitions": p["repetitions"],
            "lapses": p["lapses"],
            "due_at": p["due_at"],
            "last_reviewed_at": p["last_reviewed_at"],
            "proficiency": srs.proficiency(p["ease_factor"], p["repetitions"], p["lapses"]),
        }
    d["progress"] = progress
    return d


if __name__ == "__main__":
    app.run(debug=True, port=5057)
