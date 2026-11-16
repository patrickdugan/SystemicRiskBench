"""Atomic JSON snapshots with bounded retries for Windows sharing violations."""
import json
import os
from pathlib import Path
import time
import uuid


def save_json(path, value, *, attempts=20, delay=.1):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    for attempt in range(attempts):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt+1 == attempts:
                raise
            time.sleep(delay)


def save_status(path, value):
    """A blocked status pointer must not abort the waiting or inference process."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".jsonl").open("a", encoding="utf-8") as journal:
        journal.write(json.dumps(value, allow_nan=False)+"\n")
    try:
        save_json(path, value)
    except PermissionError:
        # The append-only journal remains the authoritative latest state until
        # the transient file lock clears on a later update.
        return False
    return True
