"""File indexer package — background daemon for crawling, parsing, and embedding files."""

import time
import traceback

import config
from indexer import db
from indexer.embeddings import ensure_model
from indexer.engine import run_index_cycle
from indexer.search import refresh_cache

# Indexer state
_indexing = False
_last_scan: float = 0


def is_indexing() -> bool:
    return _indexing


def last_scan_time() -> float:
    return _last_scan


def start_indexer():
    """Main indexer loop — runs in a daemon thread. Blocks forever."""
    global _indexing, _last_scan

    print("[indexer] Starting file indexer...")

    try:
        db.init_db()
        ensure_model()
    except Exception:
        traceback.print_exc()
        print("[indexer] Failed to initialize, will retry in 60s")
        time.sleep(60)

    while True:
        try:
            _indexing = True
            run_index_cycle()
            refresh_cache()
            _last_scan = time.time()
            _indexing = False
        except Exception:
            traceback.print_exc()
            _indexing = False

        time.sleep(config.SEARCH_RESCAN_INTERVAL)


def trigger_reindex():
    """Trigger an immediate re-index (runs in current thread)."""
    global _indexing, _last_scan
    _indexing = True
    try:
        run_index_cycle()
        refresh_cache()
        _last_scan = time.time()
    finally:
        _indexing = False
