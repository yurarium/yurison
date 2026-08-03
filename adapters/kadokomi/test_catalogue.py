#!/usr/bin/env python3
"""kadokomi/catalogue.py: reading a results page without mistaking a page for the whole list.

COVERS = ['adapters/kadokomi/catalogue.py']
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import catalogue as kc


def page(payload):
    return ('<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"dehydratedState": {"queries": [
                {"state": {"data": payload}}]}}}})
            + "</script>")


def main(s):
    total, rows = kc.results(page({"total": 120, "result": [{"code": "A"}, {"code": "B"}]}))
    s.eq(total, 120, "the total is read, so paging knows when to stop")
    s.eq(len(rows), 2, "the page's own rows are read")

    # A page without the block yields nothing rather than an empty success, which would look like
    # "the catalogue is empty" and quietly truncate the crawl.
    s.eq(kc.results("<html>no script</html>"), (None, []), "a page without the block yields none")

    # A query block with no result must not be mistaken for the results block. The page carries
    # several, and picking the wrong one returns an empty list that reads as a finished crawl.
    other = ('<script id="__NEXT_DATA__" type="application/json">'
             + json.dumps({"props": {"pageProps": {"dehydratedState": {"queries": [
                 {"state": {"data": {"something": "else"}}},
                 {"state": {"data": {"total": 5, "result": [{"code": "Z"}]}}}]}}}})
             + "</script>")
    total, rows = kc.results(other)
    s.eq(total, 5, "the block carrying results is the one chosen")
    s.eq([r["code"] for r in rows], ["Z"], "and its rows are returned")

    # A total the platform does not state must stay unknown rather than defaulting to the page size,
    # which would stop the crawl after one page.
    total, rows = kc.results(page({"result": [{"code": "A"}]}))
    s.check(total is None, "an unstated total is unknown, not inferred from the page")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kadokomi.catalogue"))
