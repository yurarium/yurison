#!/usr/bin/env python3
"""pixivcomic/releases.py: pure helpers over the API's JSON.

COVERS = ['adapters/pixivcomic/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as px


class R:
    def __init__(self):
        self.suspicious_dates = 0


def main(s):
    s.eq(px.clean_str("  x  "), "x", "whitespace is trimmed")
    s.check(px.clean_str("   ") is None, "a blank string is nothing, not an empty string")
    s.check(px.clean_str(None) is None, "None is nothing")
    s.check(px.clean_str(42) is None, "a non-string is nothing rather than coerced")

    # Tags arrive with a leading hash and duplicates.
    tags = px.extract_tags([{"name": "#百合"}, {"name": "百合"}, {"name": " GL "}, {"bad": 1}, None])
    s.eq(tags, ["百合", "GL"], "the hash is stripped and duplicates collapse")
    s.eq(px.extract_tags("not a list"), [], "a non-list yields no tags")
    s.eq(px.extract_tags([]), [], "an empty list yields no tags")

    # Epoch milliseconds. A wrong unit would land every date in 1970, so it is surfaced rather than
    # emitted quietly.
    r = R()
    s.eq(px.epoch_ms_to_date(1785715200000, r), "2026-08-03", "milliseconds convert to a JST date")
    s.check(px.epoch_ms_to_date(None, r) is None, "None yields no date")
    s.check(px.epoch_ms_to_date(0, r) is None, "zero yields no date")
    s.check(px.epoch_ms_to_date(-1, r) is None, "a negative stamp yields no date")
    s.check(px.epoch_ms_to_date("1785715200000", r) is None, "a string is not accepted silently")
    # True is an int in Python, and would otherwise convert to 1970-01-01.
    s.check(px.epoch_ms_to_date(True, r) is None, "a boolean is not a timestamp")

    before = r.suspicious_dates
    px.epoch_ms_to_date(1785715200, r)      # seconds, not milliseconds: lands in 1970
    s.check(r.suspicious_dates > before, "a wrong unit is counted as suspicious rather than hidden")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "pixivcomic.releases"))
