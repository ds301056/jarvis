"""SQLite database for file index — schema creation, connection, queries."""

import os
import sqlite3
import struct
import threading

import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    extension   TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    modified_at REAL NOT NULL,
    indexed_at  REAL NOT NULL,
    content     TEXT,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    embedding   BLOB,
    UNIQUE(file_id, chunk_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, content='chunks', content_rowid='id',
    tokenize='porter unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def _db_path() -> str:
    return os.path.expanduser(config.SEARCH_DB_PATH)


def get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        path = _db_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


# ── File operations ──────────────────────────────────────────────────

def get_file(path: str) -> sqlite3.Row | None:
    return get_conn().execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()


def upsert_file(path: str, name: str, ext: str, size: int, mtime: float,
                indexed_at: float, content: str | None, error: str | None) -> int:
    conn = get_conn()
    conn.execute("""
        INSERT INTO files (path, name, extension, size_bytes, modified_at, indexed_at, content, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name=excluded.name, extension=excluded.extension,
            size_bytes=excluded.size_bytes, modified_at=excluded.modified_at,
            indexed_at=excluded.indexed_at, content=excluded.content, error=excluded.error
    """, (path, name, ext, size, mtime, indexed_at, content, error))
    conn.commit()
    row = conn.execute("SELECT id FROM files WHERE path = ?", (path,)).fetchone()
    return row["id"]


def delete_file(path: str):
    conn = get_conn()
    conn.execute("DELETE FROM files WHERE path = ?", (path,))
    conn.commit()


def get_all_indexed_paths() -> dict[str, float]:
    """Return {path: modified_at} for all indexed files."""
    rows = get_conn().execute("SELECT path, modified_at FROM files").fetchall()
    return {r["path"]: r["modified_at"] for r in rows}


def file_count() -> int:
    return get_conn().execute("SELECT COUNT(*) FROM files").fetchone()[0]


# ── Chunk operations ─────────────────────────────────────────────────

def delete_chunks_for_file(file_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
    conn.commit()


def insert_chunks(file_id: int, chunks: list[tuple[int, str]]):
    """Insert chunks as (chunk_index, text) tuples."""
    conn = get_conn()
    conn.executemany(
        "INSERT INTO chunks (file_id, chunk_index, text) VALUES (?, ?, ?)",
        [(file_id, idx, text) for idx, text in chunks],
    )
    conn.commit()


def get_chunks_without_embeddings(limit: int = 100) -> list[sqlite3.Row]:
    return get_conn().execute(
        "SELECT id, text FROM chunks WHERE embedding IS NULL LIMIT ?", (limit,)
    ).fetchall()


def update_embeddings(updates: list[tuple[bytes, int]]):
    """Set embedding BLOBs: list of (embedding_blob, chunk_id)."""
    conn = get_conn()
    conn.executemany("UPDATE chunks SET embedding = ? WHERE id = ?", updates)
    conn.commit()


# ── Search operations ────────────────────────────────────────────────

def fts_search(query: str, limit: int = 50) -> list[dict]:
    """Full-text search via FTS5. Returns list of {chunk_id, file_id, text, rank}."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id as chunk_id, c.file_id, c.text, fts.rank
        FROM chunks_fts fts
        JOIN chunks c ON c.id = fts.rowid
        WHERE chunks_fts MATCH ?
        ORDER BY fts.rank
        LIMIT ?
    """, (query, limit)).fetchall()
    return [dict(r) for r in rows]


def get_all_embeddings() -> tuple[list[int], 'numpy.ndarray']:
    """Load all chunk embeddings into a numpy array. Returns (chunk_ids, matrix)."""
    import numpy as np
    rows = get_conn().execute(
        "SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL"
    ).fetchall()
    if not rows:
        return [], np.zeros((0, config.SEARCH_EMBEDDING_DIM), dtype=np.float32)
    ids = []
    vecs = []
    dim = config.SEARCH_EMBEDDING_DIM
    for r in rows:
        ids.append(r["id"])
        vecs.append(np.frombuffer(r["embedding"], dtype=np.float32).reshape(dim))
    return ids, np.vstack(vecs)


def get_chunk_with_file(chunk_id: int) -> dict | None:
    row = get_conn().execute("""
        SELECT c.id as chunk_id, c.text, c.chunk_index,
               f.id as file_id, f.path, f.name, f.extension, f.modified_at
        FROM chunks c JOIN files f ON f.id = c.file_id
        WHERE c.id = ?
    """, (chunk_id,)).fetchone()
    return dict(row) if row else None


def path_search(query: str, limit: int = 20) -> list[dict]:
    """Search files by path/name using LIKE. Returns [{file_id, path, name, ...}]."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT id as file_id, path, name, extension, modified_at
        FROM files
        WHERE path LIKE ? COLLATE NOCASE
        ORDER BY modified_at DESC
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()
    return [dict(r) for r in rows]


def get_first_chunk_for_file(file_id: int) -> dict | None:
    """Get the first chunk for a given file."""
    row = get_conn().execute(
        "SELECT id, text FROM chunks WHERE file_id = ? ORDER BY chunk_index LIMIT 1",
        (file_id,)
    ).fetchone()
    return dict(row) if row else None


def embedding_to_blob(vec: list[float]) -> bytes:
    """Convert float list to bytes for storage."""
    return struct.pack(f'{len(vec)}f', *vec)
