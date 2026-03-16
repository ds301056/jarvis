"""Split text into overlapping chunks for embedding."""

import config


def chunk_text(text: str) -> list[str]:
    """Split text into ~SEARCH_CHUNK_SIZE char chunks with SEARCH_CHUNK_OVERLAP overlap."""
    max_size = config.SEARCH_CHUNK_SIZE
    overlap = config.SEARCH_CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks = []
    buffer = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(buffer) + len(para) + 2 <= max_size:
            buffer = f"{buffer}\n\n{para}" if buffer else para
        else:
            if buffer:
                chunks.append(buffer)
                # Carry overlap from end of buffer
                buffer = buffer[-overlap:] if len(buffer) > overlap else buffer

            if len(para) > max_size:
                # Hard-split long paragraphs on sentence boundaries
                for piece in _split_long(para, max_size):
                    chunks.append(piece)
                buffer = piece[-overlap:] if len(piece) > overlap else piece
            else:
                buffer = f"{buffer}\n\n{para}" if buffer else para

    if buffer and buffer not in (chunks[-1] if chunks else ""):
        chunks.append(buffer)

    return chunks


def _split_long(text: str, max_size: int) -> list[str]:
    """Split a long paragraph on sentence boundaries ('. ')."""
    sentences = text.replace(". ", ".\n").split("\n")
    pieces = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) + 1 <= max_size:
            current = f"{current} {sent}" if current else sent
        else:
            if current:
                pieces.append(current)
            if len(sent) > max_size:
                # Last resort: hard character split
                for i in range(0, len(sent), max_size):
                    pieces.append(sent[i:i + max_size])
                current = ""
            else:
                current = sent

    if current:
        pieces.append(current)

    return pieces
