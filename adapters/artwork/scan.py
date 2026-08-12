#!/usr/bin/env python3
"""Which cover images a person has already looked at, and what they saw.

WHY THIS IS A FILE AND NOT A MEMORY. Reading 1,339 images is a job that outlives any one sitting:
it is cancelled, resumed, and picked up days later. `covers.py`'s ledger records what was FETCHED;
this records what was READ, which is the half a person does. Without it a second pass starts at the
top and looks at the same artwork again.

IT HOLDS THE DECISION AND NOT THE FINDING. The findings live in `data/queue/cover-names.yaml`,
which is committed and reviewed. This is the index into them: file, work, what was seen, and
nothing else. A file recorded here with `found: none` is one somebody has ruled on, which is why an
empty answer is worth writing down at all.
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import paths                                                            # noqa: E402

STATE = paths.CACHE_ROOT / "covers-cache" / "examined.json"


def load():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save(rows):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    tmp.replace(STATE)


def mark(rows, file, work, found, detail=""):
    rows[file] = {"work": work, "found": found, "detail": detail,
                  "at": time.strftime("%Y-%m-%dT%H:%M:%S")}


if __name__ == "__main__":
    r = load()
    import collections
    print(f"{len(r)} image(s) examined: {dict(collections.Counter(x['found'] for x in r.values()))}")
