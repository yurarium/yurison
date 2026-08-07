#!/usr/bin/env python3
"""The book run behind a web serialisation, taken from the national bibliography.

WHY THIS EXISTS. 862 works in this database have a web serialisation and no print edition: no
tankōbon, no volume count, no ISBN. They are not missing because nobody printed them. They are
missing because the print catalogue here is reached by imprint and by a retailer's yuri shelf, and
a work serialised on a general platform is on neither. `adapters/editions/capture.py` asks each
work's own platform page for the shops selling its volumes and keeps the ISBNs. This asks MADB.

HOW IT DIFFERS FROM by_isbn.py, WHICH IT REUSES. That route admits works: an ISBN off a shop's
yuri shelf is a comparator listing a work we did not hold (DEFINITIONS §2), so the record says
which shelf admitted it. Here the work is already in the database and already in scope. Nothing is
being admitted, so nothing carries `admitted_by`; what the record carries is where the edition was
identified, which is the platform's own page for the serialisation.

WHY THE PLATFORM AND NOT THE SHOP IS NAMED. The identifier chain starts at a publisher's own web
magazine stating which volumes its series has. A shop appears in the middle of some chains and
never at the end: コミックシーモア's title id is how カドコミ points at an edition, and cmoa's page
is where the ISBN is written, and both are discovery. What enters the source layer is the
bibliography's answer.

WHAT IS REPORTED RATHER THAN FILTERED. A platform's コミックス block can hold something beside the
volumes: となりのヤングジャンプ lists an illustration book next to 明日ちゃんのセーラー服 16, and
ガンガンONLINE's shop banner has been seen carrying a number that is not the volume beside it. So
every record written is compared with the platform work it came from, and a disagreement is
counted and named rather than dropped. A filter that silently discards rows is unobservable when it
stops working (STANDING-INSTRUCTIONS §13); a count that has to be read is not.
"""
import argparse
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import by_isbn                                                                 # noqa: E402
import extract                                                                 # noqa: E402
import identity                                                                # noqa: E402
import isbn as _isbn                                                           # noqa: E402
import shelfingest                                                             # noqa: E402

ROUTE = "isbn-from-platform"
CAPTURE = "data/queue/platform-editions.yaml"

# A work reached through its own platform's link to the shops selling its volumes. The platform is
# publisher-side, but linking to a shop is not labelling: DEFINITIONS §4 takes a publisher applying
# 百合 to the work, and a コミックス block applies nothing.
LABEL_PLATFORM = ("none",
                  "Identified from the work's own platform page, which links the shops selling\n"
                  "    its collected volumes. A link to a shop is not publisher-side labelling\n"
                  "    (§4), so this axis stays `none`, which says nothing about content.")

# How many of the ISBNs asked for must come back before the answer is worth writing. Lower than
# by_isbn's floor and deliberately so: these ISBNs come off platform pages for works serialising
# NOW, and MADB's 単行本 dataset lags a new release by months. A run answering a third of them is
# the bibliography being behind, which is a different thing from a truncated dataset.
MIN_SHARE = 0.25


def label_for(vs):
    """`extract.LABEL_IMPRINT` where the publisher's own imprint carries it, else `LABEL_PLATFORM`.

    The imprint test is `by_isbn.label_for`'s and is not repeated; what differs is the fallback,
    and it has to differ because the two routes reach a work for different reasons. Taking the
    sibling's fallback wrote "admitted on a licensed retailer's yuri shelf" onto records of works
    that were already in the database and had never been near a shelf.
    """
    value, _note = by_isbn.label_for(vs)
    return extract.LABEL_IMPRINT if value == "yuri" else LABEL_PLATFORM


def wanted_by_work(paths):
    """`{platform_url: {"work", "platform", "isbns": [...]}}` from the queue capture.

    Keyed on the platform URL rather than on the title, because that address is what the database
    already holds for the serialisation and is what makes the join an identifier.
    """
    import yaml

    out = {}
    for p in paths:
        doc = yaml.safe_load(pathlib.Path(p).read_text()) or {}
        for w in (doc.get("works") or []):
            isbns = [i for i in (_isbn.isbn13(v.get("isbn")) for v in (w.get("volumes") or [])) if i]
            if not isbns:
                continue
            out[w["platform_url"]] = {"work": w.get("work"), "platform": w.get("platform"),
                                      "id": w.get("id"), "isbns": isbns}
    return out


def identified_by(source, retrieved):
    """The lines naming where an edition was identified, for one record."""
    return ["identified_by:",
            f"  route: {ROUTE}",
            f"  platform: {extract.yaml_str(source['platform'] or '')}",
            f"  url: {extract.yaml_str(source['url'])}",
            f"  retrieved: {retrieved}",
            "  note: >-",
            "    The work's own platform page links the shops selling its collected volumes, and",
            "    the ISBN was read off that page's links. A shop is discovery only (REQUIREMENTS",
            "    §1); this record is the national bibliography's answer to the ISBN."]


# MADB writes a title in ISBD notation, so one record carries several forms of its own name:
# `白と黒 = Black & White` is a parallel title and `キグナスの乙女たち : 新・魔法科高校の劣等生` is a
# series statement written after the volume's. A platform writes one of them, in either order. So
# the record's title is split on the notation and each part is compared.
ISBD = re.compile(r"\s[=:]\s")

# ○ and 〇 are different characters and are used interchangeably in a censored word: MADB writes
# 異種族女子に○○する話 and pixivコミック writes 異種族女子に〇〇する話, which is the same work.
CIRCLES = str.maketrans({"〇": "○", "◯": "○"})


def _forms(title):
    """The folded forms of a title, including each part of an ISBD notation."""
    t = str(title or "").translate(CIRCLES)
    return {f for f in (identity.fold(p) for p in [t] + ISBD.split(t)) if f}


def agreement(vols, series, sid, platform_work):
    """Whether a MADB work and the platform work it came from name the same thing.

    NOT A JOIN. `identity.py` decides joins. What this answers is narrower and it is a GUARD: does
    the bibliography's title for this record look like the serialisation whose page the ISBN was
    read off. The chain goes wrong in ways that were measured on the run of 2026-08-07:

      くらげバンチ's sidebar on ストロベリークォーツ lists けがわとなかみ, which is the same author's
      other series and not this one's tankōbon.
      ビッコミ's 単行本情報 on the one-shot 人魚姫 lists ベラドンナの恋人, the author's collected
      volume. The platform is stating a relation that is not "this work's volumes".
      コミックシーモア states 9784046804099 for 両片想いな双子姉妹 1 and that ISBN is 百合百景. The
      shop's number belongs to another book, which `cmoa_volumes.py` had already met once.

    `agreed` where a folded form of either title contains the other, `differs` otherwise. A work
    every one of whose leads differs is not written: an unrelated print record entering the
    database is a scope error, and a join made on it would be a wrong merge, which is the kind of
    mistake that is hard to see once made.
    """
    s = vols[0] if sid.startswith("T:") else series.get(sid, {})
    got = _forms(extract.primary(s.get("schema:name", "")))
    want = _forms(platform_work)
    if not got or not want:
        return "unknown"
    for g in got:
        for w in want:
            if g == w or g.startswith(w) or w.startswith(g):
                return "agreed"
    return "differs"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a pinned MADB release directory")
    ap.add_argument("--tag", required=True, help="MADB release tag, recorded in every record")
    ap.add_argument("--retrieved", required=True, help="ISO date the cache was downloaded")
    ap.add_argument("--capture", nargs="+", default=[CAPTURE])
    ap.add_argument("--out", default="data/source/madb")
    ap.add_argument("--joins", default="data/queue/platform-print-joins.yaml",
                    help="where the ISBN-to-record chain is written for adapters/identity.py")
    ap.add_argument("--register", default="data/source/editions/withheld.yaml",
                    help="content-flag register, read by build.py and asserted by check.py")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    by_url = wanted_by_work(a.capture)
    isbns = {i for v in by_url.values() for i in v["isbns"]}
    if not isbns:
        sys.exit("no ISBNs stated by the capture(s) given; nothing to ask")

    books = extract.load(a.cache, "metadata101.json")
    series = {r["schema:identifier"]: r for r in extract.load(a.cache, "metadata104.json")}
    vols = by_isbn.select(books, isbns)

    answered = {by_isbn.isbn13(extract.flat(r.get("schema:isbn", ""))) for r in vols}
    share = len(answered) / len(isbns)
    if share < MIN_SHARE:
        sys.exit(f"HEALTH: {len(answered)} of {len(isbns)} ISBNs answered ({share:.0%}), under the "
                 f"{MIN_SHARE:.0%} floor. Refusing to write.")

    whole = by_isbn.expand(books, vols, series)
    by_series, grouping = extract.group(whole, series)
    by_series = extract.dedupe(by_series)

    # Which platform work each MADB work was reached from. A record reached from two of them is
    # kept once and both addresses are recorded, because a work serialised on two platforms is one
    # work and losing one address would lose a join.
    seed = {by_isbn.isbn13(extract.flat(r.get("schema:isbn", ""))): r for r in vols}
    from_url = collections.defaultdict(list)
    for url, v in by_url.items():
        for i in v["isbns"]:
            r = seed.get(i)
            if r is None:
                continue
            key = extract.key_of(r, series, extract.title_index(series))[0]
            if url not in from_url[key]:
                from_url[key].append(url)

    held = by_isbn.owned_elsewhere(a.out, ROUTE)
    skipped = [k for k in by_series if extract.work_id(k) in held]
    for k in skipped:
        del by_series[k]

    checks = collections.Counter()
    joins = []
    for sid, vs in by_series.items():
        for url in from_url.get(sid) or []:
            how = agreement(vs, series, sid, by_url[url]["work"])
            checks[how] += 1
            joins.append({"platform_url": url, "work": by_url[url]["work"],
                          "madb_work_id": extract.work_id(sid), "agreement": how})

    # A work every one of whose leads disagrees is not written. The ISBN came off a page belonging
    # to a work this database holds, but the bibliography says the number names something else, and
    # writing it would put an unrelated print record into a yuri database and join it to the wrong
    # serialisation. Refused as a whole record and named here, because a count nobody can read is
    # the same as a silent drop (STANDING-INSTRUCTIONS §13).
    agreed = {j["madb_work_id"] for j in joins if j["agreement"] != "differs"}
    refused = sorted({j["madb_work_id"] for j in joins} - agreed)
    for sid in [k for k in by_series if extract.work_id(k) in set(refused)]:
        del by_series[sid]

    labels = {k: label_for(vs) for k, vs in by_series.items()}
    print(f"platform works stating an ISBN : {len(by_url)}")
    print(f"ISBNs asked                    : {len(isbns)}")
    print(f"volumes answered               : {len(vols)}  ({len(answered)} distinct, {share:.0%})")
    print(f"volumes in those works         : {len(whole)}")
    print(f"works                          : {len(by_series)} new, {len(skipped)} already held, "
          f"{len(refused)} refused")
    print(f"  labelled yuri                : {sum(1 for v in labels.values() if v[0] == 'yuri')}")
    print(f"  the bibliography's title agrees with the platform's: {checks['agreed']}, "
          f"differs: {checks['differs']}, unknown: {checks['unknown']}")
    for j in joins:
        if j["agreement"] == "differs" and j["madb_work_id"] in set(refused):
            print(f"    REFUSED {j['madb_work_id']}  the platform page was {j['work']!r}")
    if a.dry_run:
        print("dry run; nothing written")
        return 0

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # Scoped to this route's own files. An earlier version of the sibling module cleared a whole
    # output directory and took another route's records with it.
    for f in out.glob("*.yaml"):
        if f"route: {ROUTE}" in f.read_text():
            f.unlink()
    for sid, vs in sorted(by_series.items()):
        urls = from_url.get(sid) or []
        src = ({"platform": by_url[urls[0]]["platform"], "url": urls[0]} if urls
               else {"platform": "", "url": ""})
        (out / f"{extract.work_id(sid)}.yaml").write_text(
            extract.render(sid, vs, series, grouping[sid], a.tag, a.retrieved, ROUTE, labels[sid],
                           identified_by(src, a.retrieved)))
    print(f"written                        : {len(by_series)} -> {out}")

    j = pathlib.Path(a.joins)
    j.parent.mkdir(parents=True, exist_ok=True)
    j.write_text(render_joins(joins, a.retrieved))
    print(f"joins                          : {len(joins)} -> {j}")

    flags = designations(by_series, series, from_url, by_url)
    reg = pathlib.Path(a.register)
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(render_register(flags, a.retrieved))
    print(f"content flags                  : {len(flags)} recorded, 0 withheld -> {reg}")
    for r in flags:
        print(f"    FLAGGED {r['work_title'][:28]}  {r['reason']}")
    return 0


def designations(by_series, series, from_url, by_url):
    """Works whose print record carries a designation, as rows for a content-flag register.

    WHY THIS EXISTS RATHER THAN A FILTER. The serialisation was already in the database and already
    published: what this pass adds is the book run, and with it the publisher's imprint, which is
    the first time a designation has been visible on these works at all. STANDING-INSTRUCTIONS §14
    is the policy and it does not withhold: every platform here is a commercial publisher's own web
    arm. So the flag is recorded and reported, `withhold` is false, and `check.py`'s `content flags
    are accounted for` makes the register and the published report agree.

    The alternative was to say nothing, which is what a register with no consumer amounts to, and
    §13 records what that cost the last time.
    """
    out = []
    for sid, vs in by_series.items():
        s = vs[0] if sid.startswith("T:") else series.get(sid, {})
        fields = {"genre": "",
                  "imprint": extract.split_reading(extract.primary(s.get("schema:brand", ""))),
                  "publisher": extract.split_reading(extract.primary(s.get("schema:publisher", ""))),
                  "title": extract.primary(s.get("schema:name", ""))}
        why = shelfingest.designated(fields)
        if not why:
            continue
        urls = from_url.get(sid) or []
        out.append({"work_title": by_url[urls[0]]["work"] if urls else fields["title"],
                    "url": urls[0] if urls else "",
                    "work_id": extract.work_id(sid),
                    "reason": why})
    return sorted(out, key=lambda r: r["work_id"])


REGISTER_HEADER = """\
# Works whose print record carries a designation (DEFINITIONS §7), found when this pass attached
# the book run to a serialisation the database already held and published.
#
# RECORDED AND REPORTED, NOT WITHHELD. STANDING-INSTRUCTIONS §14 is the policy: every platform in
# this database is a commercial publisher's own web arm, so a designation on the imprint does not
# withhold the serialisation by itself. `withhold` is false on every row and setting it is a
# reviewed decision taken by hand.
#
# THIS FILE HAS A CONSUMER, in the commit that created it. build.py's `content_flags` reads it,
# run.json reports it, status.html shows the count, and check.py's `content flags are accounted
# for` fails if the register and the report disagree. A register nothing consumes reads as a
# control that is working, which is what §13 is written about.
"""


def render_register(rows, retrieved):
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [REGISTER_HEADER.rstrip(), "", "source: editions", f"retrieved: {retrieved}",
         "record_type: withheld", f"flagged_total: {len(rows)}", "works:"]
    for r in rows:
        L.append(f"  - work_title: {js(r['work_title'])}")
        L.append(f"    url: {js(r['url'])}")
        L.append(f"    work_id: {js(r['work_id'])}")
        L.append(f"    reason: {js(r['reason'])}")
        L.append("    withhold: false")
    L.append("")
    return "\n".join(L)


JOIN_HEADER = """\
# Which print record belongs to which web serialisation, established by identifier and not by
# title. The chain is: the work's own platform page -> the shop link on it -> the ISBN -> the MADB
# record holding that ISBN. adapters/identity.py reads this and attaches the record's C-number to
# the web work's identity, which is a stronger claim than the title-and-author proposal it makes
# on its own.
#
# `agreement` is what the bibliography's title for the record looks like against the platform's
# title for the serialisation. It is reported, not enforced: `differs` is how a コミックス block
# carrying an illustration book or somebody else's number becomes visible.
"""


def render_joins(joins, retrieved):
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [JOIN_HEADER.rstrip(), "", "source: platform-retail-links", "role: print-edition-join",
         f"retrieved: {retrieved}", "record_type: platform_print_join",
         f"joins_total: {len(joins)}", "joins:"]
    for j in sorted(joins, key=lambda j: (j["platform_url"], j["madb_work_id"])):
        L.append(f"  - platform_url: {js(j['platform_url'])}")
        L.append(f"    madb_work_id: {js(j['madb_work_id'])}")
        L.append(f"    work: {js(j['work'])}")
        L.append(f"    agreement: {js(j['agreement'])}")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
