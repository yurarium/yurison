#!/usr/bin/env python3
"""platform_access.py: when a platform counts as closed to us, and when it opens again.

The cost of a wrong answer runs both ways. Calling a platform closed after one bad request would
publish listing-site reports for a platform we can read, and missing a reopening would keep doing it
after the platform's own record was available again.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import platform_access as pa


def main(s):
    st = {}
    pa.record(st, "Gコミ", True, "2026-10-22", note="HTTP 403")
    s.check(pa.closed(st, "Gコミ", "2026-10-23") is None, "one day of refusal is not closed")
    s.check(pa.closed(st, "Gコミ", "2026-10-24") is None, "two days of refusal is not closed")
    pa.record(st, "Gコミ", True, "2026-10-25")
    row = pa.closed(st, "Gコミ", "2026-10-25")
    s.check(row is not None, "three days of unbroken refusal is closed")
    s.eq((row or {}).get("refused_since"), "2026-10-22", "a later refusal keeps the first day")
    s.eq((row or {}).get("note"), "HTTP 403", "the refusal's note is kept")

    pa.record(st, "Gコミ", False, "2026-10-26")
    s.check(pa.closed(st, "Gコミ", "2026-10-30") is None, "a run that let us in reopens it")
    s.check("refused_since" not in st["Gコミ"], "reopening clears the refusal")

    pa.record(st, "Gコミ", True, "2026-10-27")
    s.eq(st["Gコミ"]["refused_since"], "2026-10-27", "a new refusal starts a new count")
    s.check(pa.closed(st, "Gコミ", "2026-10-28") is None, "and the count starts again from it")

    s.check(pa.closed(st, "never-seen", "2026-10-28") is None, "a platform never recorded is open")
    s.check(pa.closed({}, "x", "2026-10-28") is None, "an empty ledger closes nothing")

    s.check(pa.run_refused([403, 403, 429]), "every page refused is a refused run")
    s.check(not pa.run_refused([403, 200]), "one page read is not a refused run")
    s.check(not pa.run_refused([403, 404]), "a missing page is not a refusal")
    s.check(not pa.run_refused([403, 503]), "a server fault is not a refusal")
    s.check(not pa.run_refused([]), "a run that asked nothing refused nothing")

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "access.yaml"
        pa.save(st, p, today="2026-10-28")
        s.eq(pa.load(p), st, "the ledger survives a save and a load")
        s.eq(pa.load(pathlib.Path(d) / "absent.yaml"), {}, "a missing ledger loads empty")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "platform_access"))
