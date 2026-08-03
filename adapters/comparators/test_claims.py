#!/usr/bin/env python3
"""comparators/claims.py: relative dates from an aggregator.

COVERS = ['adapters/comparators/claims.py']
"""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import claims


def main(s):
    today = datetime.date(2026, 8, 3)

    # The antenna prints relative times for anything recent, and they mean today.
    s.eq(claims.antenna_date("5分前", today), today, "minutes ago is today")
    s.eq(claims.antenna_date("3時間前", today), today, "hours ago is today")

    s.eq(claims.antenna_date("2026年7月1日", today), datetime.date(2026, 7, 1),
         "a full date is read as written")
    s.eq(claims.antenna_date("2026年12月31日", today), datetime.date(2026, 12, 31),
         "two-digit months and days are read")

    # A date without a year assumes the current one, which is the source's own convention.
    got = claims.antenna_date("7月1日", today)
    s.check(got is not None and got.month == 7 and got.day == 1, "a bare date keeps month and day")

    # Anything unrecognised yields None. A claim is a lead, so a wrong date on it sends the
    # verification pass looking in the wrong place.
    s.check(claims.antenna_date("近日公開", today) is None, "text with no date yields None")
    s.check(claims.antenna_date("", today) is None, "empty yields None")
    s.check(claims.antenna_date(None, today) is None, "None yields None rather than raising")

    s.eq(claims.norm("ＹＵＲＩ"), claims.norm("yuri"), "width and case fold for comparison")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "comparators.claims"))
