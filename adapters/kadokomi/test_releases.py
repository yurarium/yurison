#!/usr/bin/env python3
"""kadokomi/releases.py: episodes and their access, read from the page's embedded JSON.

COVERS = ['adapters/kadokomi/releases.py']

The access rule here is asymmetric on purpose, and the asymmetry is the whole test: カドコミ states
when a chapter IS open and says nothing about why a closed one is closed. Inferring 有料 from the
absence put a free one-shot in the reader's interface as paid.
"""
import json
import datetime
import pathlib
import tempfile
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


    # A DELIVERY DATE IS NOT A PUBLICATION DATE. カドコミ gives `startDate` for when it begins
    # serving a chapter, which for a rotating free window is in the future. Read as the chapter's
    # own date, it made 28 chapters of a 2020 serial surface as new the day it came round, none of
    # them readable and none of them carrying a URL.
    future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    rows = k.ep_rows({"firstEpisodes": {"result": [
        {"code": "c1", "title": "Chapter1", "updateDate": "2020-02-03"},
        {"code": "c2", "title": "Chapter2", "startDate": future},
        {"code": "c3", "title": "Chapter3", "updateDate": future}]}})
    by = {r["code"]: r for r in rows}
    s.eq(by["c1"]["updated"], "2020-02-03", "a stated publication date is the chapter's date")
    s.eq(by["c2"]["updated"], "", "a delivery date is not, so the chapter stays undated")
    s.eq(by["c2"]["opens_on"], future, "and is recorded as what it is")
    s.check(by["c2"]["not_yet_delivered"], "with the fact that it has not opened yet")
    s.eq(by["c3"]["updated"], "", "and no date in the future is a publication date, whatever field it came from")

    # AN UPDATE DATE THAT MOVES IS NOT A PUBLICATION DATE. カドコミ restamps a chapter's entry when
    # it re-enters the free rotation, so 悪いが私は百合じゃない reported chapters 1 to 28 of a 2020
    # serial as updated today while its chapter 55 sat at June. A serial's chapter 28 cannot be
    # published after its chapter 55, and the contradiction is inside the work's own data.
    rot = k.ep_rows({"firstEpisodes": {"result": [
        {"code": "a", "title": "Chapter28 rotated", "updateDate": "2026-08-06"},
        {"code": "b", "title": "Chapter55 newest", "updateDate": "2026-06-23"},
        {"code": "c", "title": "Chapter1 first", "updateDate": "2020-02-03"}]}})
    by = {r["code"]: r for r in rot}
    s.eq(by["a"].get("updated"), None, "a date later than every higher-numbered chapter is dropped")
    s.eq(by["a"]["rotated_date"], "2026-08-06", "and kept as what it is, so a later run can see it")
    s.eq(by["b"]["updated"], "2026-06-23", "the newest chapter keeps its date")
    s.eq(by["c"]["updated"], "2020-02-03", "and so does an old one that does not contradict it")
    s.eq(by["a"]["title"], "Chapter28 rotated",
         "only the date goes: the chapter is still a chapter")

    # A work whose chapters carry no numbers has nothing to check against, and is left alone.
    plain = k.ep_rows({"firstEpisodes": {"result": [
        {"code": "x", "title": "prologue", "updateDate": "2026-08-06"},
        {"code": "y", "title": "epilogue", "updateDate": "2020-01-01"}]}})
    s.eq({r["code"]: r.get("updated") for r in plain}, {"x": "2026-08-06", "y": "2020-01-01"},
         "unnumbered chapters state no order, so no date contradicts another")

    # A FETCH THAT FAILED IS NOT A WORK THAT ENDED. カドコミ answered 398 of 400 and the two that
    # errored were simply not written, which removed them from the corpus and made two curated
    # titles stop naming works we hold, on a run whose only intent was to correct some dates.
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "chapters.yaml"
        f.write_text(
            "works:\n"
            "  - work_title: \"held\"\n    platform_code: \"A\"\n"
            "    chapters:\n      - code: \"a1\"\n        title: \"Chapter1\"\n"
            "  - work_title: \"refetched\"\n    platform_code: \"B\"\n"
            "    chapters:\n      - code: \"b1\"\n        title: \"Chapter1\"\n")
        kept = k.carry_over(f, ["B"])
        s.eq([w["work_title"] for w in kept], ["held"],
             "a work this run did not reach is kept as it was")
        s.eq(len(kept[0]["episodes"]), 1, "with its chapters, under the key the writer emits")
        s.eq(k.carry_over(pathlib.Path(d) / "nothing.yaml", []), [],
             "and a first run has nothing to carry")

if __name__ == "__main__":
    sys.exit(testkit.run(main, "kadokomi.releases"))
