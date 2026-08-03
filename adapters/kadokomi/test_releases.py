#!/usr/bin/env python3
"""kadokomi/releases.py: episodes and their access, read from the page's embedded JSON.

COVERS = ['adapters/kadokomi/releases.py']

The access rule here is asymmetric on purpose, and the asymmetry is the whole test: カドコミ states
when a chapter IS open and says nothing about why a closed one is closed. Inferring 有料 from the
absence put a free one-shot in the reader's interface as paid.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as k


def page(work):
    return ('<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"dehydratedState": {"queries": [
                {"state": {"data": work}}]}}}})
            + "</script>")


def main(s):
    work = {"work": {"title": "t"}, "latestEpisodes": {"result": [
        {"code": "A", "title": "第1話", "updateDate": "2026-08-03T02:00:00Z", "isActive": True},
        {"code": "B", "title": "第2話", "updateDate": "2026-08-10T02:00:00Z", "isActive": False},
        {"code": "C", "title": "第3話", "updateDate": "2026-08-17T02:00:00Z", "isActive": True,
         "deliveryPeriod": "2026-09-01T00:00:00Z"},
        {"code": "D", "title": "第4話", "updateDate": "2026-08-24T02:00:00Z", "isActive": True,
         "deliveryPeriod": "9999-12-31T00:00:00Z"},
    ]}}

    s.check(k.work_data(page(work)) is not None, "the embedded JSON is found")
    s.check(k.work_data("<html>no script</html>") is None,
            "a page without the block yields None rather than raising")

    rows = {r["code"]: r for r in k.ep_rows(k.work_data(page(work)))}
    s.eq(len(rows), 4, "every episode is read")

    s.eq(rows["A"].get("access_modes"), ["free"], "isActive true means the platform says free")
    # The asymmetry. Closed does not mean paid, because カドコミ never says which it is.
    s.check("access_modes" not in rows["B"],
            "isActive false records NOTHING, because the reason is unstated")
    s.eq(rows["C"].get("free_until"), "2026-09-01", "a real delivery period is kept as free_until")
    # 9999-12-31 is the platform's way of writing "no end", so storing it would publish a date that
    # is not a date.
    s.check("free_until" not in rows["D"], "9999-12-31 means no end and is not stored as a date")

    s.eq(rows["A"]["updated"], "2026-08-03", "the timestamp is trimmed to a date")
    s.eq(rows["A"]["title"], "第1話", "the title is carried through")

    # Deduplication by code, since latestEpisodes and firstEpisodes overlap on short series.
    both = {"work": {}, "latestEpisodes": {"result": [{"code": "A", "title": "x",
                                                       "updateDate": "2026-01-01"}]},
            "firstEpisodes": {"result": [{"code": "A", "title": "x", "updateDate": "2026-01-01"}]}}
    s.eq(len(k.ep_rows(both)), 1, "an episode listed in both blocks appears once")

    # Malformed entries must be skipped rather than taking the run down.
    junk = {"work": {}, "latestEpisodes": {"result": [None, "text", {"title": "no code"},
                                                      {"code": "Z", "title": "ok"}]}}
    s.eq([r["code"] for r in k.ep_rows(junk)], ["Z"], "junk entries are skipped, valid ones kept")

    # WHAT THE PLATFORM ANNOUNCES, out of the payload rather than the prose beside it. カドコミ
    # carries nextUpdateDateText, and 未定 is itself a statement: a platform saying
    # it has not settled a date differs from a page that says nothing at all.
    s.eq(k._next_update({"nextUpdateDateText": "2026/08/10"}), {"next_update": "2026-08-10"},
         "a whole date needs nothing inferred")
    s.eq(k._next_update({"nextUpdateDateText": "未定"}), {"next_update_undecided": True},
         "未定 is recorded as the statement it is")
    s.eq(k._next_update({"nextUpdateDateText": ""}), None, "an empty field states nothing")
    s.eq(k._next_update({}), None, "and neither does a missing one")
    s.eq(k._next_update({"nextUpdateDateText": "2026/02/30"}), None,
         "a date the calendar does not have is not invented")
    s.eq(k._next_update({"nextUpdateDateText": "来週くらい"}), None,
         "and prose where a date should be is not guessed at")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kadokomi.releases"))
