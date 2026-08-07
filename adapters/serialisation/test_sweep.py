#!/usr/bin/env python3
"""sweep.py: which works get asked about, and how an answer is written down."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sweep as S                                                              # noqa: E402
import testkit                                                                 # noqa: E402

SERIES = {"series": [
    {"id": "w1", "work": "印刷だけの本", "author": "作者A", "first": "2020-04", "url": None,
     "chapters": 0, "print": [{"work_id": "C1", "publisher": "[発売]講談社",
                               "imprint": "IDコミックス"}]},
    {"id": "w2", "work": "古い本", "author": "作者B", "first": "2008-05", "url": None,
     "chapters": 0, "print": [{"work_id": "C2", "publisher": "太田出版"}]},
    {"id": "w3", "work": "日付のない本", "author": "作者C", "first": None, "url": None,
     "chapters": 0, "print": [{"work_id": "C3", "publisher": "ナンバーナイン"}]},
    {"id": "w4", "work": "連載中", "author": "作者D", "first": "2021-01",
     "url": "https://example.jp/a", "chapters": 12, "print": []},
    {"id": "w5", "work": "章だけある", "author": "作者E", "first": "2021-01", "url": None,
     "chapters": 3, "print": []},
]}


def population(**kw):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "series.json"
        p.write_text(json.dumps(SERIES, ensure_ascii=False))
        return S.population(str(p), **kw)


def main(s):
    got = population(since="2019")
    s.eq([w["id"] for w in got], ["w1"], "only the dated, print-only, recent work is asked about")

    s.eq([w["id"] for w in population(since="2000")], ["w1", "w2"],
         "lowering the cutoff reaches the older book")

    # AN UNDATED WORK IS NOT AN OLD ONE. 1,151 of the print-only rows carry no date at all, almost
    # all of them digital-first labels that state no printing date. THE BUG THIS PINS: a date
    # filter drops every one of them silently, and "we could not date it" is not "it is too old to
    # have been serialised".
    s.check("w3" not in [w["id"] for w in population(since="1900")],
            "an undated work is not swept in by lowering the cutoff")
    s.eq(sorted(w["id"] for w in population(since="1900", include_undated=True)),
         ["w1", "w2", "w3"], "it takes asking for it")

    ids = [w["id"] for w in population(since="1900", include_undated=True)]
    s.check("w4" not in ids, "a work with a web address is not print-only")
    s.check("w5" not in ids, "and neither is one with chapters and no address")

    row = got[0]
    s.eq(row["publisher"], ["講談社"],
         "the cataloguing bracket comes off the publisher, so it can be compared with a page")
    s.eq(row["imprint"], ["IDコミックス"],
         "and the imprint is carried, because RUNBOOK §11 accepts it as a join")
    s.eq(row["madb"], ["C1"], "with the record the join will attach to")

    # THE WRITTEN FILE HAS TO PARSE, and it is written by hand-shaped lines rather than dumped, so
    # a nested list under a scalar key is the failure mode. THE BUG THIS PINS: `nico: hit` followed
    # by an indented list of hits produced a file no reader could load.
    import yaml
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / "search.yaml"
        S.write(out, [dict(row, queries=["印刷だけの本"], nico_state="hit", antenna_state="none",
                           nico=[{"comic_id": "1", "title": "印刷だけの本", "author": "作者A",
                                  "url": "https://manga.nicovideo.jp/comic/1",
                                  "updated": "2026-01-01"}],
                           antenna=[])], "2019", "2026-08-07")
        doc = yaml.safe_load(out.read_text())
    s.eq(doc["works"], 1, "the file states how many works were asked about")
    s.eq(doc["asked"][0]["nico"], "hit", "the outcome is a scalar")
    s.eq(doc["asked"][0]["nico_hits"][0]["comic_id"], "1", "and the hits are a list of their own")
    s.eq(doc["asked"][0]["antenna"], "none", "a site with nothing to say still says so")
    s.check("antenna_hits" not in doc["asked"][0], "and lists nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, pathlib.Path(__file__).name))
