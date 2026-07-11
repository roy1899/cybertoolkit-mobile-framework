"""
Session log: a lightweight, append-only local record of module runs
within a session, so the `reporting` module has something to aggregate.

This is intentionally NOT a database or anything fancy - one JSON object
per line (JSONL), one file, appended to by the CLI after each `ctk run`.
It lives entirely on-device (no capability needed to read/write it beyond
passive_local, since it's local application state, not network access).

Location defaults to ~/.cache/cybertoolkit/session.jsonl but can be
overridden via the CTK_SESSION_LOG environment variable, which is what
tests use to avoid touching a real home directory.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


def session_log_path() -> Path:
    override = os.environ.get("CTK_SESSION_LOG")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "cybertoolkit" / "session.jsonl"


def append_entry(module_name: str, profile_name: str, result: Dict[str, Any]) -> Path:
    path = session_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": module_name,
        "profile": profile_name,
        "result": result,
    }

    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return path


def read_entries(path: Optional[Path] = None) -> Iterator[Dict[str, Any]]:
    target = path or session_log_path()
    if not target.exists():
        return

    with open(target) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Skip a corrupted line rather than failing the whole read -
                # a partially-written entry (e.g. app killed mid-write)
                # shouldn't take down reporting for the rest of the session.
                continue


def clear(path: Optional[Path] = None) -> None:
    target = path or session_log_path()
    if target.exists():
        target.unlink()
