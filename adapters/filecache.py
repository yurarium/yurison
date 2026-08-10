#!/usr/bin/env python3
"""A per-file answer remembered against the content it was measured from.

WHY THIS EXISTS. `stock phrasing in comments` cost 12.9 s of an 86 s gate, and almost all of it
re-read files nobody had touched. The same shape fits several other checks that walk the tree and
answer per file, so the mechanism lives here once instead of being typed into each of them.

WHAT MAKES A CACHED ANSWER SAFE, which is the whole of the design:

    THE FILE'S CONTENT is the key, never its path or its timestamp. A file restored to an earlier
    state is the earlier answer, and a touched file with the same bytes is not rescanned.

    THE RULE'S OWN CONTENT is part of the key. The answer is a function of the file AND of whatever
    measures it, so changing a rule throws the WHOLE cache away rather than ageing entries out. A
    cache that survives a rule change reports yesterday's answer about today's rule, which is worse
    than no cache: it is a check that has silently stopped asking.

    THE SET IS SUPPLIED BY THE CALLER on every run, so a file added is measured and a file deleted
    stops counting. Nothing is inferred from what the cache happens to hold.

WHERE IT MAY NOT LIVE. Not under `data/build`: `adapters/greentree.py` hashes that, and a cache
written during a gate would invalidate the token the same gate is about to write.

WHAT IT CANNOT SEE. A rule that reads something other than its own file. If a measure imports a
vocabulary from a second module, hashing the first alone leaves the cache valid across a change to
the second. `rule_files` takes as many paths as the measure actually depends on, and naming them is
the caller's job.
"""
import hashlib
import json
import pathlib

#: Entries kept before the file is reset to the current set. A tracked tree here is about 700
#: files, so this holds roughly thirty rewrites of every one of them.
KEEP = 20000


def digest(paths):
    """One hash over the content of `paths`, which is what a remembered answer is keyed against."""
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(x) for x in paths):
        h.update(str(p).encode("utf-8"))
        try:
            h.update(hashlib.sha256(pathlib.Path(p).read_bytes()).digest())
        except OSError:
            h.update(b"missing")
    return h.hexdigest()


def counted(files, rule_files, run, cache_at):
    """`(total, scanned)` where `run(paths) -> {path: number}` is asked only about what is new.

    `scanned` is how many files the measure actually saw, so a caller can say what the cache saved
    and a test can prove nothing was rescanned.
    """
    files = [pathlib.Path(f) for f in files]
    rules = digest(rule_files)
    cache_at = pathlib.Path(cache_at)

    held = {}
    if cache_at.exists():
        try:
            doc = json.loads(cache_at.read_text(encoding="utf-8"))
            if doc.get("rules") == rules:
                held = doc.get("files") or {}
        except (OSError, ValueError):
            held = {}

    keys, want = {}, []
    for f in files:
        try:
            keys[f] = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            continue
        if keys[f] not in held:
            want.append(f)

    if want:
        for path, n in (run(want) or {}).items():
            k = keys.get(pathlib.Path(path))
            if k is not None:
                held[k] = n

    total = sum(held.get(keys[f], 0) for f in files if f in keys)

    # AN ANSWER ABOUT CONTENT IS STILL TRUE WHEN THE CONTENT COMES BACK. Pruning to the current set
    # looked tidy and made a `git checkout` of one file cost a full rescan of it, which is a thing
    # that happens several times an hour here. Entries are kept, and the whole file is dropped once
    # it passes the cap, because an eviction policy worth arguing about is not worth the seconds.
    try:
        cache_at.parent.mkdir(parents=True, exist_ok=True)
        keep = held if len(held) <= KEEP else {
            keys[f]: held[keys[f]] for f in files if f in keys and keys[f] in held}
        cache_at.write_text(json.dumps({"rules": rules, "files": keep}), encoding="utf-8")
    except OSError:
        pass
    return total, len(want)
