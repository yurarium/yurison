#!/usr/bin/env python3
"""Parse a big capture once, not once per question asked about it.

WHY THIS EXISTS. `deploy.sh` took two minutes, and stub generation, which was the suspected cost,
was 0.03 seconds of it. The time was in YAML. `data/queue/bookwalker-volumes.yaml` and its sibling
run to megabytes, and four budget checks plus `status.py` each loaded them independently: the same
file parsed four or five times in one deploy, and again on the next deploy whether or not a capture
had run in between.

TWO CACHES, BECAUSE THERE ARE TWO REPEATS. Within one process the same file is asked for several
times, and a dict answers that. Across processes, and across deploys where nothing was captured,
the parse is still repeated, and a JSON sidecar answers that. JSON loads roughly an order of
magnitude faster than YAML for the same document.

KEYED ON WHAT WOULD MAKE THE ANSWER WRONG. The file's modification time and its size, both read in
one `stat`. A capture that has been rewritten changes at least one of them, so a stale answer is
not served; a run that only read the file changes neither, so the cache holds. Nothing here decides
whether a capture is fresh enough to use, which is the ledger's question and not this one.

WHERE THE CACHE LIVES. Outside the repository, beside the other caches. It is derived from files
that are already committed, so committing it would be storing the same data twice, and it is large.
"""
import hashlib
import json
import os
import pathlib

# One parse per file per process. Cleared by the process ending, which is the whole of its lifetime.
_MEMO = {}


def cache_root():
    """Where sidecars are written. Outside the repository, beside the other caches."""
    env = os.environ.get("YURI_CACHE")
    base = pathlib.Path(env) if env else pathlib.Path(__file__).resolve().parents[2]
    return base / "capture-cache"


def key(path):
    """What identifies this exact content: the path, its size and its modification time.

    One `stat`, no read. A capture that was rewritten changes size or mtime and misses the cache; a
    capture that was only read changes neither and hits it.
    """
    st = pathlib.Path(path).stat()
    return hashlib.sha1(f"{pathlib.Path(path).resolve()}|{st.st_size}|{st.st_mtime_ns}"
                        .encode()).hexdigest()[:16]


def load(path, root=None):
    """The parsed capture, from memory, then from a sidecar, then from YAML.

    Returns `{}` for a file that is not there, which is what every caller already does with a
    missing capture and keeps a missing file from being an exception in a checking pass.
    """
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    k = key(p)
    if k in _MEMO:
        return _MEMO[k]

    side = pathlib.Path(root or cache_root()) / f"{k}.json"
    if side.exists():
        try:
            doc = json.loads(side.read_text())
            _MEMO[k] = doc
            return doc
        except ValueError:
            # A truncated sidecar is a cache miss, never an error: the source is still on disk.
            pass

    import yaml
    doc = yaml.safe_load(p.read_text()) or {}
    _MEMO[k] = doc
    try:
        side.parent.mkdir(parents=True, exist_ok=True)
        # Written through a temporary file so a reader never sees half a document.
        tmp = side.with_suffix(".part")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, default=str))
        tmp.replace(side)
    except OSError:
        # An unwritable cache directory costs speed and nothing else.
        pass
    return doc


def sweep(root=None, keep=40):
    """Drop the oldest sidecars past `keep`, so a directory of them cannot grow without bound."""
    d = pathlib.Path(root or cache_root())
    if not d.exists():
        return 0
    files = sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        f.unlink()
    return max(0, len(files) - keep)
