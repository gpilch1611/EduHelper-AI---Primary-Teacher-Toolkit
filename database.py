# database.py – SQLite persistence layer

import sqlite3
from datetime import datetime
from config import DB_NAME


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def initialise_db() -> None:
    """Create all tables (idempotent) then run column migrations."""
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                subject     TEXT    NOT NULL DEFAULT 'Other',
                year_group  TEXT    NOT NULL DEFAULT '',
                file_path   TEXT    NOT NULL UNIQUE,
                page_count  INTEGER NOT NULL DEFAULT 0,
                added_at    TEXT    NOT NULL,
                last_used   TEXT
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id             INTEGER NOT NULL
                                        REFERENCES books(id) ON DELETE CASCADE,
                number              INTEGER NOT NULL,
                title               TEXT    NOT NULL,
                start_page          INTEGER,
                end_page            INTEGER,
                learning_objectives TEXT,
                exercise_types      TEXT,
                key_vocabulary      TEXT,
                topics              TEXT
            );

            CREATE TABLE IF NOT EXISTS pages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL
                                REFERENCES books(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                raw_text    TEXT,
                UNIQUE(book_id, page_number)
            );

            CREATE TABLE IF NOT EXISTS lesson_plans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER REFERENCES books(id) ON DELETE SET NULL,
                chapter_id  INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
                title       TEXT    NOT NULL,
                year_group  TEXT,
                duration    TEXT,
                objectives  TEXT,
                content     TEXT,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS worksheets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER REFERENCES books(id) ON DELETE SET NULL,
                title       TEXT    NOT NULL,
                difficulty  TEXT    DEFAULT 'Medium',
                content     TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quiz_questions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER REFERENCES books(id) ON DELETE SET NULL,
                chapter_id  INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
                question    TEXT    NOT NULL,
                answer      TEXT,
                difficulty  TEXT    DEFAULT 'Medium',
                created_at  TEXT    NOT NULL
            );
        """)
    _migrate_db()


def _migrate_db() -> None:
    """Add columns that may be missing from pre-existing installs."""
    new_chapter_cols = [
        ("learning_objectives", "TEXT"),
        ("exercise_types",      "TEXT"),
        ("key_vocabulary",      "TEXT"),
        ("topics",              "TEXT"),
    ]
    with _get_connection() as conn:
        for col_name, col_type in new_chapter_cols:
            try:
                conn.execute(
                    f"ALTER TABLE chapters ADD COLUMN {col_name} {col_type}"
                )
            except Exception:
                pass   # column already exists – ignore


# ── Books ─────────────────────────────────────────────────────────────────────

def add_book(title: str, subject: str, year_group: str,
             file_path: str, page_count: int = 0) -> int:
    """Insert a book record and return its new id."""
    now = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO books
               (title, subject, year_group, file_path, page_count, added_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, subject, year_group, file_path, page_count, now),
        )
        return cur.lastrowid


def get_all_books() -> list[dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM books ORDER BY added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_book(book_id: int) -> dict | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return dict(row) if row else None


def update_book_last_used(book_id: int) -> None:
    with _get_connection() as conn:
        conn.execute(
            "UPDATE books SET last_used = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), book_id),
        )


def delete_book(book_id: int) -> None:
    with _get_connection() as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))


def book_exists(file_path: str) -> bool:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM books WHERE file_path = ?", (file_path,)
        ).fetchone()
        return row is not None


# ── Chapters ──────────────────────────────────────────────────────────────────

def add_chapter(
    book_id: int,
    number:  int,
    title:   str,
    start_page:          int  = None,
    end_page:            int  = None,
    learning_objectives: str  = "",
    exercise_types:      str  = "",
    key_vocabulary:      str  = "",
    topics:              str  = "",
) -> int:
    with _get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO chapters
               (book_id, number, title, start_page, end_page,
                learning_objectives, exercise_types, key_vocabulary, topics)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (book_id, number, title, start_page, end_page,
             learning_objectives, exercise_types, key_vocabulary, topics),
        )
        return cur.lastrowid


def get_chapters(book_id: int) -> list[dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chapters WHERE book_id = ? ORDER BY number",
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Pages ─────────────────────────────────────────────────────────────────────

def save_pages(book_id: int, pages: list[dict]) -> None:
    """Bulk-insert page records.  Each dict: {page_number, raw_text}."""
    with _get_connection() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO pages (book_id, page_number, raw_text)
               VALUES (?, ?, ?)""",
            [(book_id, p["page_number"], p["raw_text"]) for p in pages],
        )


def get_page_text(book_id: int, page_number: int) -> str:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT raw_text FROM pages WHERE book_id=? AND page_number=?",
            (book_id, page_number),
        ).fetchone()
        return row["raw_text"] if row else ""


def get_pages_text_range(book_id: int,
                         start: int, end: int) -> str:
    """Return concatenated raw text for pages [start, end] inclusive."""
    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT raw_text FROM pages
               WHERE book_id=? AND page_number BETWEEN ? AND ?
               ORDER BY page_number""",
            (book_id, start, end),
        ).fetchall()
        return "\n".join(r["raw_text"] or "" for r in rows)


def get_book_page_count_stored(book_id: int) -> int:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM pages WHERE book_id=?",
            (book_id,),
        ).fetchone()
        return row["n"] if row else 0


# ── Lesson Plans ──────────────────────────────────────────────────────────────

def save_lesson_plan(title: str, content: str, book_id: int = None,
                     chapter_id: int = None, year_group: str = "",
                     duration: str = "", objectives: str = "") -> int:
    now = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO lesson_plans
               (book_id, chapter_id, title, year_group, duration,
                objectives, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (book_id, chapter_id, title, year_group,
             duration, objectives, content, now),
        )
        return cur.lastrowid


def get_lesson_plans(book_id: int = None) -> list[dict]:
    with _get_connection() as conn:
        if book_id:
            rows = conn.execute(
                "SELECT * FROM lesson_plans WHERE book_id=? ORDER BY created_at DESC",
                (book_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM lesson_plans ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# ── Worksheets ────────────────────────────────────────────────────────────────

def save_worksheet(title: str, content: str,
                   book_id: int = None, difficulty: str = "Medium") -> int:
    now = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO worksheets
               (book_id, title, difficulty, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (book_id, title, difficulty, content, now),
        )
        return cur.lastrowid


def get_worksheets(book_id: int = None) -> list[dict]:
    with _get_connection() as conn:
        if book_id:
            rows = conn.execute(
                "SELECT * FROM worksheets WHERE book_id=? ORDER BY created_at DESC",
                (book_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM worksheets ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
