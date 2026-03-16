"""Directory walker with change detection via mtime."""

import os

import config


# Build sets once for fast lookup
_EXCLUDE_DIRS = set(config.SEARCH_EXCLUDE_DIRS)
_EXCLUDE_EXTS = set(config.SEARCH_EXCLUDE_EXTENSIONS)

# Text/parseable extensions we support
_SUPPORTED_EXTS = {
    ".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".log",
    ".pdf", ".xlsx", ".xls", ".pptx", ".docx",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".zsh", ".fish",
    ".java", ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".rb", ".php",
    ".css", ".scss", ".less", ".sql", ".r", ".m", ".swift",
}


def crawl() -> list[dict]:
    """Walk configured directories and return list of file info dicts.

    Each dict: {path, name, extension, size_bytes, modified_at}
    """
    results = []
    max_size = config.SEARCH_MAX_FILE_SIZE

    for search_dir in config.SEARCH_DIRS:
        root = os.path.expanduser(search_dir)
        if not os.path.isdir(root):
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in _EXCLUDE_DIRS and not d.startswith(".")
            ]

            for fname in filenames:
                if fname.startswith("."):
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext in _EXCLUDE_EXTS:
                    continue
                if ext not in _SUPPORTED_EXTS:
                    continue

                fpath = os.path.join(dirpath, fname)
                try:
                    stat = os.stat(fpath)
                except OSError:
                    continue

                if stat.st_size > max_size or stat.st_size == 0:
                    continue

                results.append({
                    "path": fpath,
                    "name": fname,
                    "extension": ext,
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                })

    return results
