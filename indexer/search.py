"""Hybrid search: FTS5 keyword + cosine semantic + Reciprocal Rank Fusion."""

import re
import time
import threading

import numpy as np

import config
from indexer import db
from indexer.embeddings import embed_query

# Cached embedding matrix — refreshed periodically
_cache_lock = threading.Lock()
_cached_ids: list[int] = []
_cached_matrix: np.ndarray = np.zeros((0, 768), dtype=np.float32)
_cache_time: float = 0


def refresh_cache():
    """Reload all embeddings from DB into memory."""
    global _cached_ids, _cached_matrix, _cache_time
    with _cache_lock:
        _cached_ids, _cached_matrix = db.get_all_embeddings()
        _cache_time = time.time()


def _ensure_cache():
    """Refresh cache if stale (older than 60s)."""
    if time.time() - _cache_time > 60:
        refresh_cache()


def search(query: str, limit: int = 10) -> list[dict]:
    """Hybrid search combining FTS5 keyword and semantic vector search.

    Returns list of dicts with: chunk_id, file_path, file_name, extension,
    modified_at, snippet, score
    """
    _ensure_cache()

    # 1. FTS5 keyword search
    fts_results = _fts_search(query)

    # 2. Semantic vector search
    semantic_results = _semantic_search(query)

    # 3. Path search
    path_results = _path_search(query)

    # 4. Reciprocal Rank Fusion
    merged = _rrf_merge(fts_results, semantic_results, path_results, k=60)

    # 5. Fetch file metadata and build results
    results = []
    seen_files = set()
    for chunk_id, score in merged:
        info = db.get_chunk_with_file(chunk_id)
        if not info:
            continue
        # Deduplicate by file — show best chunk per file
        if info["path"] in seen_files:
            continue
        seen_files.add(info["path"])

        snippet = _make_snippet(info["text"], query)
        results.append({
            "file_path": info["path"],
            "file_name": info["name"],
            "extension": info["extension"],
            "modified_at": info["modified_at"],
            "snippet": snippet,
            "score": round(score, 4),
        })
        if len(results) >= limit:
            break

    return results


def _fts_search(query: str) -> list[tuple[int, int]]:
    """FTS5 search. Returns [(chunk_id, rank_position), ...]."""
    # Sanitize query for FTS5 — remove special chars, wrap tokens in quotes
    tokens = re.findall(r'\w+', query)
    if not tokens:
        return []
    fts_query = " OR ".join(f'"{t}"' for t in tokens)

    try:
        rows = db.fts_search(fts_query, limit=50)
        return [(r["chunk_id"], i) for i, r in enumerate(rows)]
    except Exception:
        return []


def _semantic_search(query: str) -> list[tuple[int, int]]:
    """Cosine similarity search. Returns [(chunk_id, rank_position), ...]."""
    with _cache_lock:
        if len(_cached_ids) == 0:
            return []
        ids = _cached_ids.copy()
        matrix = _cached_matrix.copy()

    try:
        query_vec = np.array(embed_query(query), dtype=np.float32)
    except Exception:
        return []

    # Cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normalized = matrix / norms

    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []
    query_normalized = query_vec / query_norm

    similarities = normalized @ query_normalized
    top_indices = np.argsort(similarities)[::-1][:50]

    return [(ids[i], rank) for rank, i in enumerate(top_indices)]


def _path_search(query: str) -> list[tuple[int, int]]:
    """Search file paths. Returns [(chunk_id, rank), ...] for best chunk per matching file."""
    tokens = re.findall(r'\w+', query)
    if not tokens:
        return []

    # Try full query first
    matches = db.path_search(query)
    if not matches:
        # Try individual tokens
        for token in tokens:
            matches.extend(db.path_search(token))

    # Get first chunk_id for each matching file
    results = []
    seen = set()
    for i, m in enumerate(matches):
        if m["file_id"] in seen:
            continue
        seen.add(m["file_id"])
        chunk = db.get_first_chunk_for_file(m["file_id"])
        if chunk:
            results.append((chunk["id"], i))
    return results


def _rrf_merge(*rank_lists: list[tuple[int, int]],
               k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: score = sum(1 / (k + rank))."""
    scores: dict[int, float] = {}

    for rank_list in rank_lists:
        for chunk_id, rank in rank_list:
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _make_snippet(text: str, query: str, max_len: int = 200) -> str:
    """Extract a relevant snippet from chunk text."""
    tokens = re.findall(r'\w+', query.lower())
    text_lower = text.lower()

    # Find the best window around a matching token
    best_pos = 0
    for token in tokens:
        pos = text_lower.find(token)
        if pos >= 0:
            best_pos = pos
            break

    start = max(0, best_pos - max_len // 2)
    end = start + max_len

    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
