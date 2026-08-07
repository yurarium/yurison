#!/usr/bin/env python3
"""The book run behind a web serialisation, found by asking a shop and answered by the bibliography.

WHY THIS EXISTS. `by_platform_isbn.py` reaches a work's volumes through the work's own platform
page, and 534 of the 645 works with no print edition came back from that route with "the platform
lists no collected volume". That sentence is about the PLATFORM. COMIC FUZ's page model for a
series carries no book field at all, so its silence is structural and says nothing about whether
芳文社 printed the volumes, and it did: `w00537` コンカフェ嬢は恋を着る is three volumes under
ＦＵＺコミックス, marked 完結 by the shop, and its FUZ page links to no shop at all.
`adapters/shopquery/capture.py` asks BOOK☆WALKER about each such work. This asks MADB.

WHY THE JOIN IS A TITLE AND A PERSON HERE, AND AN ISBN ELSEWHERE. The sibling routes hold a number
because コミックシーモア prints one. BOOK☆WALKER sells files and prints none, on any of the 5,968
volumes read from it, and its search is the one this project is permitted to use: cmoa's
robots.txt closes `/search/result/` under `User-agent: *`. So the strongest available identifier is
the one `by_title.py` already established for the same shop's undated rows, and this consumes that
module instead of restating it: a title match proposes, and a person's name has to agree before
anything is written.

TWO PARTIES AGREE BEFORE A RECORD IS WRITTEN, and neither consulted the other. The shop and this
database agree on the title and on a person, which `shopquery/shop.classify` establishes and stores
as `agreement: creator`. The bibliography and this database then agree on the title and on a person
again, which is `by_title.agreeing`. A work that clears the first and fails the second is counted
and named, because a shop and a national library disagreeing about who drew a book is a lead about
one of them and not an absence of evidence (STANDING-INSTRUCTIONS §13).

WHAT LABEL THESE WORKS CARRY. `none`, unless the publisher's own imprint is a yuri line. These
works were admitted before the shop was asked, the shop was asked what it stocks, and stock is
weaker than the genre shelf DEFINITIONS §4 already refuses as publisher-side labelling. `none`
means what §4 says it means, which is nothing about content.

WHAT IS NOT JOINED. A hit the shop matched on the title alone. Those rows are in the capture with
`agreement: title-only` and this module does not look at them, for the reason the capture states:
`トワ・エ・モア` is a 1996 コンパス anthology and a 2024 講談社 series at once, and a wrong join
attaches one work's volumes to another where nobody can see it afterwards.
"""
import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import by_isbn                                                                 # noqa: E402
import by_title                                                                # noqa: E402
import extract                                                                 # noqa: E402

ROUTE = "shop-query"
CAPTURE = "data/queue/shop-query.yaml"

# A work reached by asking a shop what it stocks under a name this database already holds. The
# shop's answer is stock, and stock is not a designation.
LABEL_SHOP = ("none",
              "Identified by asking a licensed retailer what it stocks for a work this database\n"
              "    already held. A shop's stock is not publisher-side labelling (§4), so this\n"
              "    axis stays `none`, which says nothing about content.")

# How many of the shop's creator-agreeing leads must reach a bibliography record before the answer
# is worth writing. Lower than by_isbn's floor for by_platform_isbn's reason and one more: these
# are web serialisations, MADB's 単行本 dataset lags a new release by months, and the join here is a
# title plus a person instead of a number, so it legitimately refuses more.
#
# THE COUNTER-CASE, so this is not lowered later to make a run pass: a release whose
# metadata101.json failed to unpack would answer nothing at all and would fail this correctly, and
# the answer to that is to look at the cache.
MIN_SHARE = 0.2


def leads(paths):
    """`{work_url: lead}` for every capture row the shop and this database agree about.

    Keyed on the work's own platform address, which is what the database already holds for the
    serialisation and what `adapters/identity.py` re-finds a web work by.

    ONLY `agreement: creator` IS READ. The capture stores its title-only hits and this deliberately
    ignores them; `refused_by_the_shop` counts them so the number is visible somewhere.
    """
    import yaml

    out = {}
    for p in paths:
        doc = yaml.safe_load(pathlib.Path(p).read_text()) or {}
        for w in (doc.get("works") or []):
            hits = [h for h in (w.get("hits") or []) if h.get("agreement") == "creator"]
            if not hits:
                continue
            out[w["work_url"]] = {
                "id": w.get("id"), "work": w.get("work"), "author": w.get("author"),
                "platform": w.get("platform"), "query": w.get("query"), "hits": hits}
    return out


def title_only(paths):
    """Capture rows whose only hits matched on the title, as rows for a review file."""
    import yaml

    out = []
    for p in paths:
        doc = yaml.safe_load(pathlib.Path(p).read_text()) or {}
        for w in (doc.get("works") or []):
            hits = w.get("hits") or []
            if not hits or any(h.get("agreement") == "creator" for h in hits):
                continue
            for h in hits:
                out.append({"work_url": w["work_url"], "id": w.get("id"), "work": w.get("work"),
                            "author": w.get("author"), "shop_title": h.get("title_listed"),
                            "shop_author": h.get("shop_author"),
                            "shop_publisher": h.get("publisher"),
                            "series_url": h.get("series_url")})
    return sorted(out, key=lambda r: r["work_url"])


def credit(lead):
    """The names to test a bibliography record against, from both sides of the shop's agreement.

    The shop's credit and ours already share a person, so either would do. Both are offered because
    a catalogue writes a collaboration as `[作画]A / [原作]B` and the platform frequently prints one
    of the two, and a name the platform dropped is still a name the record may carry.
    `by_title.people` reads the joined line, which is `names.inputs.split_authors` and is the
    project's one reader of a credit line.
    """
    parts = [lead.get("author") or ""] + [h.get("shop_author") or "" for h in lead["hits"]]
    return " / ".join(p for p in parts if p)


def titles(lead):
    """Every form of the work's name to look the bibliography up under.

    Both sides again. The shop appends the imprint to a series name and the platform does not, and
    `by_title.keys` folds through `identity.fold`, which strips bracketed matter, so
    コンカフェ嬢は恋を着る（ＦＵＺコミックス） and コンカフェ嬢は恋を着る reach the same key. Where
    they do not, the shop's spelling is the one the publisher's catalogue is likelier to share.
    """
    out = set()
    for t in [lead.get("work")] + [h.get("title_listed") for h in lead["hits"]]:
        out |= by_title.keys(t or "")
    return out


def answer(lead, by_name):
    """The bibliography volume records this lead identifies, or an empty list.

    `by_title.agreeing` is the rule and it lives there. A record naming nobody agrees with nothing,
    which is what stops this collapsing back into the title match it exists to avoid being.
    """
    found = {}
    for key in titles(lead):
        for r in by_name.get(key, []):
            found[id(r)] = r
    return by_title.agreeing({"creator": credit(lead)}, list(found.values()))


def identified_by(lead, retrieved):
    """The lines naming how this edition was identified, for one record."""
    hit = lead["hits"][0]
    return ["identified_by:",
            f"  route: {ROUTE}",
            "  shop: bookwalker.jp",
            f"  query: {extract.yaml_str(lead.get('query') or '')}",
            f"  url: {extract.yaml_str(hit.get('series_url') or '')}",
            f"  serialisation: {extract.yaml_str(lead.get('platform') or '')}",
            f"  retrieved: {retrieved}",
            "  note: >-",
            "    The shop was asked what it stocks for a work this database already held, and its",
            "    answer agreed on the title and on a person. A shop is discovery only",
            "    (REQUIREMENTS §1) and states no ISBN here; this record is the national",
            "    bibliography's, joined on the title and on a person's name."]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a pinned MADB release directory")
    ap.add_argument("--tag", required=True, help="MADB release tag, recorded in every record")
    ap.add_argument("--retrieved", required=True, help="ISO date the cache was downloaded")
    ap.add_argument("--capture", nargs="+", default=[CAPTURE])
    ap.add_argument("--out", default="data/source/madb")
    ap.add_argument("--joins", default="data/queue/shop-query-joins.yaml",
                    help="where the work-level joins are written for adapters/identity.py")
    ap.add_argument("--review", default="data/queue/shop-query-title-only.yaml",
                    help="hits the shop matched on the title alone, recorded and joined to nothing")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    found = leads(a.capture)
    if not found:
        sys.exit("no creator-agreeing leads in the capture(s) given; nothing to ask")

    books = extract.load(a.cache, "metadata101.json")
    series = {r["schema:identifier"]: r for r in extract.load(a.cache, "metadata104.json")}
    by_name = by_title.index(books)

    # Which lead each bibliography work came from. A work reached from two leads is kept once and
    # both addresses are recorded, because losing one would lose a join.
    seeds, from_url, unanswered = {}, collections.defaultdict(list), []
    idx = extract.title_index(series)
    for url, lead in sorted(found.items()):
        vols = answer(lead, by_name)
        if not vols:
            unanswered.append(lead)
            continue
        for r in vols:
            key = extract.key_of(r, series, idx)[0]
            seeds[id(r)] = r
            if url not in from_url[key]:
                from_url[key].append(url)

    share = (len(found) - len(unanswered)) / len(found)
    if share < MIN_SHARE:
        sys.exit(f"HEALTH: {len(found) - len(unanswered)} of {len(found)} leads reached a record "
                 f"({share:.0%}), under the {MIN_SHARE:.0%} floor. That is a truncated release "
                 "rather than a shelf of unpublished books. Refusing to write.")

    whole = by_isbn.expand(books, list(seeds.values()), series)
    by_series, grouping = extract.group(whole, series)
    by_series = extract.dedupe(by_series)

    # A work another route already wrote is that route's, and the imprint route reached it with
    # better evidence. Its join is still recorded below, because the record existing and the record
    # being attached to this serialisation are different facts.
    held = by_isbn.owned_elsewhere(a.out, ROUTE)
    skipped = sorted(k for k in by_series if extract.work_id(k) in held)
    for k in skipped:
        del by_series[k]

    joins = []
    for sid in sorted(set(by_series) | set(skipped)):
        for url in from_url.get(sid) or []:
            joins.append({"anchor": "madb:" + extract.work_id(sid), "url": url,
                          "work": found[url]["work"], "id": found[url]["id"],
                          "shop": (found[url]["hits"][0].get("series_url") or ""),
                          "query": found[url].get("query") or ""})

    labels = {k: (extract.LABEL_IMPRINT if by_isbn.label_for(vs)[0] == "yuri" else LABEL_SHOP)
              for k, vs in by_series.items()}
    print(f"leads the shop and this database agree about : {len(found)}")
    print(f"  reached a bibliography record              : {len(found) - len(unanswered)} "
          f"({share:.0%})")
    print(f"  no bibliography record agreed              : {len(unanswered)}")
    print(f"volumes in those works                       : {len(whole)}")
    print(f"works                                        : {len(by_series)} new, "
          f"{len(skipped)} already held by another route")
    print(f"  labelled yuri by the publisher's imprint   : "
          f"{sum(1 for v in labels.values() if v[0] == 'yuri')}")
    print(f"joins to a serialisation                     : {len(joins)}")
    only = title_only(a.capture)
    print(f"hits matched on the title alone, NOT joined  : {len(only)}")
    for lead in unanswered[:12]:
        print(f"    NO RECORD {str(lead['work'])[:30]:32} {lead.get('author')}")
    if a.dry_run:
        print("dry run; nothing written")
        return 0

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # Scoped to this route's own files. `extract.py` once cleared a whole output directory and took
    # another route's records with it.
    for f in out.glob("*.yaml"):
        if f"route: {ROUTE}" in f.read_text():
            f.unlink()
    for sid, vs in sorted(by_series.items()):
        url = (from_url.get(sid) or [None])[0]
        (out / f"{extract.work_id(sid)}.yaml").write_text(
            extract.render(sid, vs, series, grouping[sid], a.tag, a.retrieved, ROUTE, labels[sid],
                           identified_by(found[url], a.retrieved) if url else ()))
    print(f"written                                      : {len(by_series)} -> {out}")

    j = pathlib.Path(a.joins)
    j.parent.mkdir(parents=True, exist_ok=True)
    j.write_text(render_joins(joins, a.retrieved))
    print(f"joins                                        : {len(joins)} -> {j}")

    r = pathlib.Path(a.review)
    r.write_text(render_review(only, a.retrieved))
    print(f"title-only candidates                        : {len(only)} -> {r}")
    return 0


JOIN_HEADER = """\
# Which print record belongs to which web serialisation, where the shop was asked and answered.
# adapters/identity.py reads this with --attachments and attaches the C-number to the work that
# already holds the serialisation, so a reader sees one work instead of a web row and a print row
# they have to notice are the same thing.
#
# THE CHAIN. The work's own platform page listed no collected volume, so BOOK☆WALKER was asked what
# it stocks under the work's author. The shop's answer agreed on the title and on a person
# (data/queue/shop-query.yaml, `agreement: creator`), and the national bibliography's record agreed
# on the title and on a person again (adapters/madb/by_title.py). Two agreements by two parties.
#
# WHAT IS NOT HERE. A hit the shop matched on the title alone. Those are in
# data/queue/shop-query-title-only.yaml, with their evidence, and are joined to nothing.
"""


def render_joins(joins, retrieved):
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [JOIN_HEADER.rstrip(), "", "source: shop-query", "role: print-edition-join",
         f"retrieved: {retrieved}", "record_type: shop_query_join",
         f"joins_total: {len(joins)}", "joins:"]
    for j in sorted(joins, key=lambda j: (j["url"], j["anchor"])):
        L.append(f"  - anchor: {js(j['anchor'])}")
        L.append(f"    id: {js(j['id'])}")
        L.append(f"    work: {js(j['work'])}")
        L.append(f"    retrieved: {retrieved}")
        L.append("    basis: >-")
        L.append(f"      {j['work']} lists no collected volume on its own platform page, and "
                 f"bookwalker.jp answers the {j['query']} query with {j['shop']}, whose credit "
                 "shares a person with the credit this database holds. The bibliography's record "
                 "for that title agrees on a person as well, so the serialisation and the book "
                 "run are one work.")
    L.append("")
    return "\n".join(L)


REVIEW_HEADER = """\
# Shop hits whose title agreed and whose credit did not. CANDIDATES, JOINED TO NOTHING.
#
# WHY THEY ARE HERE AND NOT ATTACHED. A title identifies nothing. `トワ・エ・モア` is a 1996 コンパス
# anthology and a 2024 講談社 series at once, and `citrus+` returned an unrelated 2007 book on a
# bare title search. A wrong join attaches one work's volumes to another and is hard to see
# afterwards, so the refusal is stored with what it refused instead of being dropped: a shop and
# this database disagreeing about who drew a book is a lead about one of them
# (STANDING-INSTRUCTIONS §13).
#
# WHAT WOULD SETTLE ONE. A person. Either the shop's credit or ours is wrong or incomplete, or the
# two titles genuinely name different works. Each row carries both credits so the question can be
# answered by looking rather than by fetching again.
"""


def render_review(rows, retrieved):
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [REVIEW_HEADER.rstrip(), "", "source: bookwalker.jp", "role: discovery-candidates",
         f"retrieved: {retrieved}", "record_type: shop_query_title_only",
         f"candidates_total: {len(rows)}", "candidates:"]
    for r in rows:
        L.append(f"  - work_url: {js(r['work_url'])}")
        for k in ("id", "work", "author", "shop_title", "shop_author", "shop_publisher",
                  "series_url"):
            if r.get(k):
                L.append(f"    {k}: {js(r[k])}")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
