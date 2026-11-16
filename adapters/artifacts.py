"""Pinned local inference artifact checks; no model loading or CUDA calls."""

import hashlib
from pathlib import Path
from urllib.request import urlopen


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4*1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path, expected_sha256, expected_bytes=None):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"artifact missing: {path.name}")
    size = path.stat().st_size
    if expected_bytes is not None and size != expected_bytes:
        raise ValueError(f"artifact size mismatch: {path.name}")
    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        raise ValueError(f"artifact SHA256 mismatch: {path.name}")
    return {"path": str(path), "bytes": size, "sha256": actual, "verified": True}


def fetch_pinned(url, destination, expected_sha256, expected_bytes):
    if not url.startswith("https://huggingface.co/"):
        raise ValueError("artifact URL must be the registered HTTPS Hugging Face release")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return verify_file(destination, expected_sha256, expected_bytes)
    temporary = destination.with_suffix(destination.suffix+".partial")
    count = 0
    with urlopen(url, timeout=90) as response, temporary.open("wb") as handle:
        while True:
            block = response.read(1024*1024)
            if not block:
                break
            count += len(block)
            if count > expected_bytes:
                raise ValueError("download exceeds registered artifact size")
            handle.write(block)
    result = verify_file(temporary, expected_sha256, expected_bytes)
    temporary.replace(destination)
    result["path"] = str(destination.resolve())
    return result
