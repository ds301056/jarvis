"""Orchestrates: crawl -> parse -> chunk -> embed -> store."""

import time
import traceback

from indexer import db
from indexer.crawler import crawl
from indexer.parsers import extract_text
from indexer.chunker import chunk_text
from indexer.embeddings import embed_texts


def run_index_cycle():
    """Run one full index cycle: detect changes, parse, chunk, embed."""
    t0 = time.time()

    # Get current state from DB
    indexed = db.get_all_indexed_paths()
    discovered = crawl()
    discovered_paths = {f["path"] for f in discovered}

    # Delete removed files
    for path in set(indexed.keys()) - discovered_paths:
        db.delete_file(path)

    # Process new or modified files
    new_count = 0
    updated_count = 0

    for finfo in discovered:
        path = finfo["path"]
        existing_mtime = indexed.get(path)

        if existing_mtime is not None and finfo["modified_at"] <= existing_mtime:
            continue  # unchanged

        is_new = existing_mtime is None
        try:
            content = extract_text(path)
            error = None
        except Exception as e:
            content = None
            error = str(e)

        file_id = db.upsert_file(
            path=path,
            name=finfo["name"],
            ext=finfo["extension"],
            size=finfo["size_bytes"],
            mtime=finfo["modified_at"],
            indexed_at=time.time(),
            content=content,
            error=error,
        )

        # Re-chunk if content was extracted
        db.delete_chunks_for_file(file_id)
        if content:
            chunks = chunk_text(content)
            if chunks:
                db.insert_chunks(file_id, list(enumerate(chunks)))

        if is_new:
            new_count += 1
        else:
            updated_count += 1

    # Embed any chunks without embeddings
    _embed_pending()

    elapsed = time.time() - t0
    total = db.file_count()
    if new_count or updated_count:
        print(f"[indexer] Indexed {new_count} new, {updated_count} updated files "
              f"({total} total) in {elapsed:.1f}s")

    return {"new": new_count, "updated": updated_count, "total": total}


def _embed_pending():
    """Embed all chunks that don't have embeddings yet."""
    while True:
        rows = db.get_chunks_without_embeddings(limit=100)
        if not rows:
            break

        texts = [r["text"] for r in rows]
        ids = [r["id"] for r in rows]

        try:
            vectors = embed_texts(texts)
        except Exception:
            traceback.print_exc()
            print("[indexer] Embedding failed, will retry next cycle")
            break

        updates = []
        for chunk_id, vec in zip(ids, vectors):
            updates.append((db.embedding_to_blob(vec), chunk_id))

        db.update_embeddings(updates)
