"""Process-local file identities; a changed file always requires a fresh hash."""
from functools import lru_cache
import hashlib
from pathlib import Path


def file_signature(path):
    stat = Path(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@lru_cache(maxsize=512)
def _digest(path, signature):
    with Path(path).open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    if file_signature(path) != signature:
        raise ValueError(f"Input changed while calculating SHA-256: {path}")
    return value


def sha256_file(path):
    path = Path(path).resolve()
    return _digest(str(path), file_signature(path))
