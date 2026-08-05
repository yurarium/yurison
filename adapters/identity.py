#!/usr/bin/env python3
"""Stable identifiers for works, and the join between a serialisation and its book run.

WHY THIS EXISTS. `series.json` rows are keyed on the title string and `index.json` rows on a MADB
C-number, so the two populations cannot be linked and neither can be addressed. Titles are corrected
often here, several on 2026-08-04 alone, so a title-derived identifier breaks exactly when the
database improves. INTERFACE-PLAN §2 turns the record into an authority record: an identifier we
mint, with the external ones hanging off it.

WHAT AN IDENTIFIER PROMISES. That it never moves and never disappears. A work whose two halves turn
out to be one work does not lose an id: the retired one gains `merged_into` and still resolves, so
an address that was published once keeps working. Assignment is append-only and lives in
`data/identity/works.yaml`, which is read before every run and written back whole.

WHAT AN ANCHOR IS. The thing we re-find a work by, chosen because it survives what titles do not.
For a web work it is the platform URL. That is unique across 985 of 993 works; the exceptions are
anthology stories sharing a container, which the data already marks with `collection`, so those
carry the folded story title alongside the URL. For a print work it is the MADB C-number.

THE JOIN IS A CLAIM (DEFINITIONS §5). Saying that a serialisation and a book run are one work can
be wrong in the way `citrus+` was wrong, where NDL returned an unrelated 2007 book on a title match
alone. So a title match alone proposes and does not decide: agreement on at least one person's name
is required before anything is recorded, and the rest go to a review file with their evidence.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from names.inputs import split_authors  # noqa: E402

ID = re.compile(r"^w(\d+)$")
WIDTH = 5
BRACKETED = re.compile(r"[【\[（(][^】\]）)]*[】\]）)]")
NOISE = re.compile(r"[\s　・!！?？。、,，~〜ー―\-–—:：;；'\"“”‘’]+")


def fold(s):
    """A comparison key for a title or a name.

    Width, spacing and decorative punctuation differ between a shop, a library and a platform
    without meaning anything, so they are removed. Bracketed matter goes too, because it carries
    edition and bonus notes rather than the name of the work.
    """
    s = unicodedata.normalize("NFKC", str(s or ""))
    for _ in range(3):
        s = BRACKETED.sub("", s)
    return NOISE.sub("", s).lower()


def people(credit):
    """The set of folded person-names in a credit line.

    One producer of this fact: `names.inputs.split_authors` already reads both the print form
    `[作画]A / [原作]B` and the platform form `漫画：A,原作：B`. A second parser here would be the
    two-paths-one-fact shape that has already produced a wrong answer in this project.
    """
    return {fold(n) for n, _role in split_authors(credit or "") if fold(n)}


def web_anchor(url, title=None, shared=False):
    """`web:<url>`, with the story title where a URL serves more than one work.

    A collection's container URL is the same for every story in it, so the URL alone would give
    five stories one identity. `shared` is decided by the caller from the whole population, not
    guessed from the row.
    """
    url = (url or "").strip()
    if not url:
        return None
    return f"web:{url}#{fold(title)}" if shared else f"web:{url}"


def print_anchor(work_id):
    wid = (work_id or "").strip()
    return f"madb:{wid}" if wid else None


def mint(taken):
    """The next free identifier. Sequential so that assignment order is auditable."""
    n = 0
    for i in taken:
        m = ID.match(str(i or ""))
        if m:
            n = max(n, int(m.group(1)))
    return f"w{n + 1:0{WIDTH}d}"


def index(entries):
    """{anchor: id} over live entries. A merged entry lends its anchors to its successor."""
    out = {}
    for e in entries:
        target = e.get("merged_into") or e.get("id")
        for a in e.get("anchors") or []:
            out[a] = target
    return out


def assign(entries, wanted):
    """Give every work in `wanted` an id, keeping every existing assignment.

    `wanted` is [(identifying_anchor, attached_anchors, title)]. **A work is looked up only by the
    anchor that identifies it**, which is its own URL or its own C-number. Attached anchors are
    what a join adds, and they are deliberately not used to find a work.

    That distinction is the whole of the correctness here, and the corpus supplies the reason.
    超深宇宙より愛をこめて exists as a 15-chapter serialisation and as a 1-chapter 読み切り版, two
    rows with two URLs, and one MADB record matches both titles. Looking a work up by any anchor
    would let the shared C-number pull the two into one identity, which is a merge, and merging is
    a decision with a basis. So an attached anchor already held by another work is reported and
    left alone.

    Entries not mentioned by this run are carried over untouched: a pass must not delete what it is
    not looking at, and this file is the one place where losing a row loses a published address.
    """
    entries = [dict(e) for e in entries]
    owner = index(entries)
    by_id = {e["id"]: e for e in entries}
    out = []
    for ident_anchor, attached, title in wanted:
        if not ident_anchor:
            continue
        wid = owner.get(ident_anchor)
        if not wid:
            wid = mint(by_id)
            e = {"id": wid, "title": title, "anchors": [ident_anchor]}
            by_id[wid] = e
            entries.append(e)
            owner[ident_anchor] = wid
        else:
            by_id[wid]["title"] = title or by_id[wid].get("title")
        e = by_id[wid]
        for a in attached or []:
            if not a:
                continue
            held = owner.get(a)
            if held and held != wid:
                out.append({"anchor": a, "wanted_by": wid, "held_by": held, "title": title})
                continue
            if a not in e["anchors"]:
                e["anchors"].append(a)
                owner[a] = wid
    return entries, out


def merge(entries, loser, winner, basis):
    """Retire `loser` into `winner`, keeping it resolvable.

    An identifier that has been published cannot be withdrawn, so the retired entry stays in the
    file with `merged_into` and its anchors keep pointing somewhere.
    """
    entries = [dict(e) for e in entries]
    by_id = {e["id"]: e for e in entries}
    if loser not in by_id or winner not in by_id or loser == winner:
        return entries
    lo, wi = by_id[loser], by_id[winner]
    for a in lo.get("anchors") or []:
        if a not in (wi.get("anchors") or []):
            wi.setdefault("anchors", []).append(a)
    lo["merged_into"] = winner
    lo["merge_basis"] = basis
    return entries


VARIANT = re.compile(r"[／/｜|]*(?:読み?切り?版?|ぱいろっと版?|出張版|試し読み版?)$")


def variant_base(title):
    """The base title where this one names itself a separate edition, otherwise None.

    `白妙様、秘密ですよ／読切版` says what it is in its own title. `fold` has already removed a
    bracketed marker, so `超深宇宙より愛をこめて【読み切り版】` folds equal to its serialisation and
    needs no rule here.
    """
    f = fold(title)
    m = VARIANT.search(f)
    return (f[:m.start()] or None) if m else None


def siblings(web):
    """[(a, b, note)] for web works that are the same story published twice.

    Two shapes reach it. A one-shot whose title folds equal to a serialisation's, and one that
    names itself a separate edition. Both require agreement on a person, because a shared title is
    the evidence that has already produced a wrong join in this project.

    **This proposes a relation and never a merge.** Whether a pilot one-shot is a distinct work, an
    instalment the serialisation absorbed, or a story a later chapter retells, differs case by case,
    and the corpus holds two examples with entirely different evidence behind them. Relating them
    says what can be said; merging them would assert what cannot.
    """
    out = []
    by_fold = {}
    for w in web:
        by_fold.setdefault(fold(w.get("work")), []).append(w)
    for key, group in by_fold.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if people(a.get("author")) & people(b.get("author")):
                    out.append((a, b, "same title and a shared author on one platform"))
    for w in web:
        base = variant_base(w.get("work"))
        for other in by_fold.get(base or "\0", []):
            if other is not w and people(w.get("author")) & people(other.get("author")):
                out.append((w, other, "titled as a separate edition of the same work"))
    return out


def propose(web, prints):
    """[(web_row, print_row, evidence)] for every title match between the two populations.

    Evidence is `agreed` where at least one person is named on both sides. Nothing else is decided
    here: a title match with no agreement is a lead and is returned as one.
    """
    idx = {}
    for w in web:
        idx.setdefault(fold(w.get("work")), []).append(w)
    out = []
    for p in prints:
        for w in idx.get(fold(p.get("t") or p.get("title")), []):
            shared = people(p.get("c") or p.get("creator")) & people(w.get("author"))
            out.append((w, p, {"agreed": sorted(shared), "basis": "title-and-author" if shared
                               else "title-only"}))
    return out


def main(argv=None):
    """Assign identifiers over both populations and record the joins that carry evidence."""
    import argparse, collections, datetime, json                            # noqa: E401
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--index", default="data/build/index.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    ap.add_argument("--review", default="data/queue/identity-review.yaml")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--merge", nargs=2, metavar=("RETIRED", "SURVIVING"),
                    help="retire one identifier into another. A decision, so it is taken by hand "
                         "and needs --basis; the retired id keeps resolving.")
    ap.add_argument("--basis", help="why the two are one work")
    a = ap.parse_args(argv)

    web = json.loads(pathlib.Path(a.series).read_text())["series"]
    prints = json.loads(pathlib.Path(a.index).read_text())

    reg = pathlib.Path(a.registry)
    doc = yaml.safe_load(reg.read_text()) if reg.exists() else None
    entries = (doc or {}).get("works") or []
    before = len(entries)

    if a.merge:
        if not a.basis:
            raise SystemExit("--merge needs --basis: retiring an identifier is a claim that two "
                             "works are one, and it is not reversible for anyone holding a link.")
        entries = merge(entries, a.merge[0], a.merge[1], a.basis)
        doc = dict(doc or {}, works=entries)

    # A URL is shared only where the whole population says so, which is why this is counted here
    # and not inferred per row.
    seen = collections.Counter(w.get("url") for w in web if w.get("url"))
    joined = {}
    for w, p, ev in propose(web, prints):
        if ev["basis"] == "title-and-author":
            joined.setdefault(w["work"], []).append((p, ev))

    wanted, leads = [], []
    for w in web:
        me = web_anchor(w.get("url"), w.get("work"), seen[w.get("url")] > 1)
        attached = [print_anchor(p.get("id")) for p, _ev in joined.get(w["work"], [])]
        wanted.append((me, attached, w.get("work")))
    # Every print record identifies itself, joined or not, so a C-number always resolves. Where it
    # is already attached to a web work it lands on that work rather than minting a second id, and
    # it passes no title, because the serialisation's title is the one the reader was shown.
    done = {p.get("id") for ps in joined.values() for p, _ in ps}
    for p in prints:
        wanted.append((print_anchor(p.get("id")), [],
                       None if p.get("id") in done else p.get("t")))

    entries, conflicts = assign(entries, wanted)
    for w, p, ev in propose(web, prints):
        if ev["basis"] == "title-only":
            leads.append({"web": w["work"], "print_id": p.get("id"), "print_title": p.get("t"),
                          "web_author": w.get("author"), "print_creator": p.get("c")})

    # Relations, carried over rather than rebuilt, for the same reason identifiers are: a pass must
    # not delete what it is not looking at. A pair is stored once and read in both directions.
    known = index(entries)
    rel = {(r["a"], r["b"]): r for r in (doc or {}).get("related") or []}
    for left, right, note in siblings(web):
        ia = known.get(web_anchor(left.get("url"), left.get("work"), seen[left.get("url")] > 1))
        ib = known.get(web_anchor(right.get("url"), right.get("work"), seen[right.get("url")] > 1))
        if ia and ib and ia != ib:
            key = tuple(sorted((ia, ib)))
            rel.setdefault(key, {"a": key[0], "b": key[1], "note": note,
                                 "retrieved": datetime.date.today().isoformat()})
    # A contested print record is itself evidence that two works are versions of one story.
    for c in conflicts:
        key = tuple(sorted((c["held_by"], c["wanted_by"])))
        rel.setdefault(key, {"a": key[0], "b": key[1],
                             "note": "one print record matches both titles and a shared author",
                             "retrieved": datetime.date.today().isoformat()})

    live = [e for e in entries if not e.get("merged_into")]
    both = sum(1 for e in live if any(x.startswith("web:") for x in e.get("anchors") or [])
               and any(x.startswith("madb:") for x in e.get("anchors") or []))
    print(f"{len(entries)} identifier(s), {len(entries) - before} new; {both} work(s) joined "
          f"across both populations; {len(rel)} related pair(s); {len(leads)} title-only lead(s); "
          f"{len(conflicts)} contested anchor(s)")
    for c in conflicts:
        print(f"  CONTESTED {c['anchor']}: held by {c['held_by']}, also claimed by {c['wanted_by']}"
              f" ({c['title']}). Attaching it to both would merge two works, which is a decision"
              f" with a basis.")

    if a.dry_run:
        return 0

    reg.parent.mkdir(parents=True, exist_ok=True)
    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Work identifiers. Append-only: an id is never reassigned and never withdrawn.",
         "#",
         "# An anchor is what a work is re-found by. `web:` is the platform URL, with the folded",
         "# story title appended where a container URL serves several works. `madb:` is the",
         "# C-number. An entry holding both is a serialisation joined to its book run, and the",
         "# join rests on agreement about a person's name as well as the title (DEFINITIONS §5).",
         "#",
         "# A merged entry keeps `merged_into` and stays resolvable, because an address published",
         "# once has to keep working. See adapters/identity.py.",
         f"generated: {datetime.date.today().isoformat()}", "works:"]
    for e in sorted(entries, key=lambda x: x.get("id") or ""):
        L.append(f"  - id: {e['id']}")
        L.append(f"    title: {js(e.get('title'))}")
        if e.get("merged_into"):
            L.append(f"    merged_into: {e['merged_into']}")
            L.append(f"    merge_basis: {js(e.get('merge_basis'))}")
        L.append("    anchors:")
        for x in e.get("anchors") or []:
            L.append(f"      - {js(x)}")
    L.append("")
    L.append("# Related works. A relation and not a merge: whether a one-shot beside a")
    L.append("# serialisation is a distinct work, an instalment the run absorbed, or a story a")
    L.append("# later chapter retells differs case by case, and relating them says what the")
    L.append("# evidence supports. Continuations belong here too, citrus and citrus+ among them.")
    L.append("#")
    L.append("# `precedes` is optional and is set by hand. It is NOT derived from the dates we")
    L.append("# hold, because those carry import stamps in exactly the cases where order matters:")
    L.append("# 超深宇宙より愛をこめて's 読み切り版 has one date, 2025-08-08, which is the day")
    L.append("# 一迅プラス imported its catalogue, while the serialisation's real start of")
    L.append("# 2025-03-08 comes from pixivコミック. Ordering those by first date would put the")
    L.append("# one-shot after the run it came before.")
    L.append("related:")
    # A pair whose two sides now resolve to one identifier is a work related to itself, which says
    # nothing. That happens when a merge follows a relation, as it did when 念願の悪役令嬢 turned
    # out to be one work written two ways. Dropping it removes a statement that has become vacuous.
    settled = {e["id"]: e.get("merged_into") or e["id"] for e in entries}
    rel = {k: v for k, v in rel.items()
           if settled.get(v["a"], v["a"]) != settled.get(v["b"], v["b"])}
    for r in sorted(rel.values(), key=lambda x: (x["a"], x["b"])):
        L.append(f"  - a: {r['a']}")
        L.append(f"    b: {r['b']}")
        if r.get("precedes"):
            L.append(f"    precedes: {js(r['precedes'])}")
        L.append(f"    note: {js(r['note'])}")
        L.append(f"    retrieved: {r['retrieved']}")
    L.append("")
    reg.write_text("\n".join(L))

    rv = pathlib.Path(a.review)
    rv.parent.mkdir(parents=True, exist_ok=True)
    R = ["# Title matches between the web and print populations with NO agreement on any person.",
         "# Not a record and not read by anything. A title alone joined citrus+ to an unrelated",
         "# 2007 book, so these are leads for a human and nothing here is applied.",
         f"generated: {datetime.date.today().isoformat()}", f"count: {len(leads)}", "leads:"]
    for x in sorted(leads, key=lambda y: y["web"]):
        R.append(f"  - web: {js(x['web'])}")
        R.append(f"    web_author: {js(x['web_author'])}")
        R.append(f"    print_id: {js(x['print_id'])}")
        R.append(f"    print_title: {js(x['print_title'])}")
        R.append(f"    print_creator: {js(x['print_creator'])}")
    R.append("")
    rv.write_text("\n".join(R))
    print(f"  -> {reg}  and  {rv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
