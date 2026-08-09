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

# THE PREFIX IS A PARAMETER BECAUSE A SECOND KIND OF OBJECT NEEDS THE SAME PROMISE. A work is `w`
# and a credit is `c` (adapters/credit_identity.py). Everything below the minting is already blind to
# which kind it is holding: `index`, `assign`, `attach` and `merge` read `id`, `anchors` and
# `merged_into` and never look at the letter, so generalising meant parameterising one function
# rather than writing a second scheme that would drift from this one's rules about a contested anchor.
WIDTH = 5
PREFIX = "w"


def id_re(prefix=PREFIX):
    return re.compile(r"^%s(\d+)$" % re.escape(prefix))


ID = id_re()
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


# A chapter address that carries its work's address in front of it: /title/03056/episode/441581.
CHAPTER_UNDER_TITLE = re.compile(r"^(https?://[^/]+/title/[^/]+)/episode/\d+/?$")

# ヤンマガWeb writes a chapter as /comics/<work>/<32 hex digits>, so the work is the prefix. The
# hexadecimal test is what separates a chapter from the work's own /comics/<work>, and from any
# other second segment the site might grow.
CHAPTER_UNDER_COMICS = re.compile(r"^(https?://[^/]+/comics/[^/]+)/[0-9a-f]{32}/?$")

# マンガワン writes a chapter as /manga/<work id>/chapter/<chapter id> and serves the work itself at
# /title/<work id>. The segment is RENAMED, so this one is a rewrite and not a truncation, and it
# rests on a fact about one platform's routing: all three addresses in the corpus were fetched on
# 2026-08-07 and each answered 200 with the work's own title. COMIC FUZ is why the /chapter/ part
# is required rather than optional, since comic-fuz.com/manga/2474 is already a work address and
# a rule matching /manga/<n> alone would rewrite 78 rows into addresses that do not exist.
MANGA_ONE_CHAPTER = re.compile(r"^(https?://manga-one\.com)/manga/(\d+)/chapter/\d+/?$")


def stable_url(url):
    """The work-level address of a chapter address, or the address unchanged.

    WHY AN ANCHOR MUST NOT BE A CHAPTER. build.py gives a row the address of its newest chapter, so
    on a GigaViewer platform the address changes every time the work publishes. This function is
    what the anchor is built from, so without this a new chapter looks like a new work: five of them
    minted a second identifier on 2026-08-07 and had to be repaired by hand.

    ONLY WHERE THE WORK'S OWN ADDRESS IS ALREADY IN THE STRING. `pocket.shonenmagazine.com/title/
    03056/episode/441581` carries it, `yanmaga.jp/comics/TANGO/0887c82c…` carries it, and
    `manga-one.com/manga/28129/chapter/355684` carries the work's id under a segment name the
    platform spells differently. 48 rows are reduced here.

    `comic-days.com/episode/12207421983997344603` carries nothing: the chapter id is the whole path
    and the work's address is only on the page. Guessing one would invent an address, so those come
    back unchanged and their work-level addresses are captured instead, by
    adapters/gigaviewer/workaddress.py. See docs/GAPS.md §21.
    """
    s = str(url or "")
    for pattern in (CHAPTER_UNDER_TITLE, CHAPTER_UNDER_COMICS):
        m = pattern.match(s)
        if m:
            return m.group(1)
    m = MANGA_ONE_CHAPTER.match(s)
    return f"{m.group(1)}/title/{m.group(2)}" if m else url


def web_anchor(url, title=None, shared=False):
    """`web:<url>`, with the story title where a URL serves more than one work.

    A collection's container URL is the same for every story in it, so the URL alone would give
    five stories one identity. `shared` is decided by the caller from the whole population, not
    guessed from the row.

    A chapter address is reduced to its work's address first, so publishing does not move it.
    """
    url = stable_url(url)
    url = (url or "").strip()
    if not url:
        return None
    return f"web:{url}#{fold(title)}" if shared else f"web:{url}"


def print_anchor(work_id):
    wid = (work_id or "").strip()
    return f"madb:{wid}" if wid else None


def mint(taken, prefix=PREFIX, width=WIDTH):
    """The next free identifier. Sequential so that assignment order is auditable.

    HIGHEST TAKEN PLUS ONE, and never the count of what is taken. A retired entry stays in the file
    for ever, so the two numbers part company the moment anything merges, and counting would hand
    out an identifier somebody already holds a link to.
    """
    pat = ID if prefix == PREFIX else id_re(prefix)
    n = 0
    for i in taken:
        m = pat.match(str(i or ""))
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:0{width}d}"


def index(entries):
    """{anchor: id} over live entries. A merged entry lends its anchors to its successor."""
    out = {}
    for e in entries:
        target = e.get("merged_into") or e.get("id")
        for a in e.get("anchors") or []:
            out[a] = target
    return out


def assign(entries, wanted, prefix=PREFIX, relabel=True):
    """Give every work in `wanted` an id, keeping every existing assignment.

    `wanted` is [(identifying_anchor, attached_anchors, title)]. **A work is looked up only by the
    anchor that identifies it**, which is its own URL or its own C-number. Attached anchors are
    what a join adds, and they are deliberately not used to find a work.

    `relabel` IS TRUE FOR A WORK AND FALSE FOR A CREDIT, and the difference is not cosmetic. Titles
    are corrected here often, several on 2026-08-04 alone, so a work's entry follows its row and the
    registry shows the current title. A credit's label is the spelling the identifier was minted for,
    and a merge lends the retired spelling's anchor to the survivor, so following the row lets the
    losing spelling become the survivor's label: 獅尾's entry came back reading `ししお` on the run
    after ししお was retired into it, and its own `merge_basis` then named a spelling the entry no
    longer showed.

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
    # A JOIN SOMEBODY UNDID STAYS UNDONE. `propose` re-derives its joins from the two populations on
    # every run, so a wrong one removed by hand comes straight back unless this pass knows the
    # decision. See `detach`.
    no = refused(entries)
    out = []
    for ident_anchor, attached, title in wanted:
        if not ident_anchor:
            continue
        wid = owner.get(ident_anchor)
        if not wid:
            wid = mint(by_id, prefix)
            e = {"id": wid, "title": title, "anchors": [ident_anchor]}
            by_id[wid] = e
            entries.append(e)
            owner[ident_anchor] = wid
        elif relabel or not by_id[wid].get("title"):
            by_id[wid]["title"] = title or by_id[wid].get("title")
        e = by_id[wid]
        for a in attached or []:
            if not a:
                continue
            if wid in no.get(a, []):
                continue
            held = owner.get(a)
            if held and held != wid:
                out.append({"anchor": a, "wanted_by": wid, "held_by": held, "title": title})
                continue
            if a not in e["anchors"]:
                e["anchors"].append(a)
                owner[a] = wid
    return entries, out


def attach(entries, anchor, wid, basis, retrieved=None):
    """Give an existing work a second address, keeping what says it is the same work.

    WHY THIS IS NOT A MERGE. A merge retires an identifier, and it is the right operation when two
    records the database already holds turn out to be one work. This is the other case: a work we
    hold only as a printed book, whose serialisation was found on a platform that had never been
    read for it. Nothing is being retired, because the serialisation was never a record. The work
    gains the address it was always published at.

    Getting the two the wrong way round is expensive in different directions. Merging where an
    attach was called for retires an identifier that nobody had published; attaching where a merge
    was called for leaves two rows for one work and one of them keeps its own id.

    THE BASIS IS STORED, unlike the anchors `assign` derives. Those are re-derived from the data on
    every run and are checkable against it; this one is a decision taken once by hand, so the
    evidence has to travel with it or it becomes an assertion nobody can weigh.

    Returns `(entries, error)`. An anchor another live work already holds is refused rather than
    moved: that is a claim that two works are one, and it is a merge.

    AN ANCHOR SOMEBODY DETACHED IS REFUSED TOO, and that is what makes a detachment stick. The
    joins files are re-applied on every run, so a wrong join removed by hand would come back the
    next morning. See `detach`.
    """
    entries = [dict(e) for e in entries]
    by_id = {e["id"]: e for e in entries}
    if wid not in by_id:
        return entries, f"{wid} is not in the registry"
    if wid in refused(entries).get(anchor, []):
        return entries, (f"{anchor} was detached from {wid} by hand and is not re-joined. The "
                         f"reason is in the registry beside {wid}.")
    held = index(entries).get(anchor)
    if held and held != wid:
        return entries, (f"{anchor} is already held by {held}. Attaching it to {wid} as well would "
                         f"say the two are one work, which is a merge and needs --merge.")
    e = by_id[wid]
    if anchor in (e.get("anchors") or []):
        return entries, None
    e.setdefault("anchors", []).append(anchor)
    e.setdefault("attached", []).append({"anchor": anchor, "basis": basis,
                                         "retrieved": retrieved or _today()})
    return entries, None


def attach_all(entries, doc):
    """`(entries, applied, refused)` for every join in a joins document.

    Re-runnable on purpose. The joins file is the record and this registry is derived from it, so
    running the pass twice must be a no-op rather than a second set of evidence lines. A join whose
    anchor another work already holds is refused with its reason rather than being forced, because
    that is the merge case and a merge retires an identifier.
    """
    applied, refused = 0, []
    for j in (doc or {}).get("joins") or []:
        anchor, wid = j.get("anchor"), j.get("id")
        if not anchor or not wid:
            refused.append(f"a join naming no anchor or no identifier: {j}")
            continue
        before = len(index(entries))
        entries, err = attach(entries, anchor, wid, j.get("basis") or "", j.get("retrieved"))
        if err:
            refused.append(err)
        elif len(index(entries)) > before:
            applied += 1
    return entries, applied, refused


def _today():
    import datetime
    return datetime.date.today().isoformat()


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


def withdraw(entries, wid, target, basis, retrieved=None):
    """Retire an identifier minted for something that was never the object, sending it to `target`.

    NOT A MERGE, AND THE ANCHOR IS THE DIFFERENCE. `merge` says two spellings are one thing, so the
    retired spelling lends its anchor to the survivor and goes on resolving to it. That is exactly
    what must not happen here. `１冊目：叔母さんは神絵師` is the first chapter of 新刊100億冊ください,
    put where the byline goes by a page capture and minted as c00268; lending its anchor to
    破賀ミチル would file a chapter under a person permanently, and any later run meeting the string
    would resolve it to them without anybody noticing.

    So the anchor is DETACHED rather than lent. `refused` then holds it, which is the same
    machinery that makes a wrong join stay undone, and the basis travels with it.

    THE ADDRESS STILL RESOLVES, because it was published. `merged_into` is where a reader who
    followed the dead link should land, and for a chapter mistaken for a byline that is the credit
    the same field really named.
    """
    entries = [dict(e) for e in entries]
    by_id = {e["id"]: e for e in entries}
    if wid not in by_id or target not in by_id or wid == target:
        return entries
    e = by_id[wid]
    for a in list(e.get("anchors") or []):
        e.setdefault("detached", []).append(
            {"anchor": a, "basis": basis, "retrieved": retrieved or _today()})
    e["anchors"] = []
    e["merged_into"] = target
    e["merge_basis"] = basis
    return entries


def detach(entries, anchor, basis, retrieved=None):
    """Take an anchor off the work holding it, and record that it must not come back.

    THE OPPOSITE OF `attach`, AND NOT THE OPPOSITE OF `merge`. A merge says two works are one and
    retires an identifier, which is why it is irreversible for anyone holding a link. This says a
    join was wrong: the record belongs to some other work, so the anchor leaves and the next
    assignment mints an identifier for it. No published address breaks, because what gets published
    is the `w` identifier and that one keeps every anchor it is entitled to.

    WHY THE REFUSAL IS STORED. The join came from a capture file that is re-applied on every run,
    so removing the anchor alone would last exactly until the next `--attachments`. The capture is
    left alone, because it is the record of what the shop answered and deleting it would lose the
    evidence; the DECISION lives here, once, and `attach` consults it.

    THE CASE IT WAS WRITTEN FOR. BOOK☆WALKER was asked what it stocks by AUTHOR, and a prolific
    author's shelf answers with their other books. Three joins came back agreeing on the person and
    on nothing else: けいおん! onto けいおん！Ｓｈｕｆｆｌｅ, 百合百景 onto 両片想いな双子姉妹, and a
    colour art book onto サタノファニ. The second is the one to remember, because it left no
    duplicate row to notice: the work simply displayed another work's volumes as its own.
    """
    entries = [dict(e) for e in entries]
    for e in entries:
        if anchor not in (e.get("anchors") or []):
            continue
        e["anchors"] = [a for a in e["anchors"] if a != anchor]
        e["attached"] = [a for a in (e.get("attached") or []) if a.get("anchor") != anchor]
        if not e["attached"]:
            e.pop("attached")
        e.setdefault("detached", []).append(
            {"anchor": anchor, "basis": basis, "retrieved": retrieved or _today()})
        return entries
    return entries


def refused(entries):
    """{anchor: [id]} for every anchor a work has been detached from, so it is not re-joined."""
    out = {}
    for e in entries:
        for d in e.get("detached") or []:
            out.setdefault(d["anchor"], []).append(e["id"])
    return out


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


def chain_joins(doc, web, shared):
    """`{web_anchor: [madb work_id]}` from a capture that joined by identifier.

    THE CHAIN, AND WHY IT NEEDS NO AUTHOR TEST. `propose` above matches two titles and then asks
    for agreement on a person's name, because a title is all the two populations share and a title
    alone has already produced a wrong join here. The platform route shares an address instead: the
    work's own serialisation page named the shop selling its collected volumes, the shop stated the
    ISBN, and the ISBN found the record. No step in that is a string comparison, so requiring a
    name to agree would reject correct joins for no gain.

    Keyed on EVERY address a row holds rather than on its primary one. A work serialising on two
    platforms has one `url` and the join may have been found through the other, and dropping it
    would silently lose the print edition for exactly the works with the most evidence.
    """
    by_url = {}
    for w in web:
        anchor = web_anchor(w.get("url"), w.get("work"), shared[w.get("url")] > 1)
        if not anchor:
            continue
        for s in (w.get("sources") or []):
            if s.get("url"):
                by_url.setdefault(s["url"], anchor)
        by_url.setdefault(w.get("url"), anchor)
    out = {}
    for j in (doc.get("joins") or []):
        # A lead the capture itself marked as disagreeing is not a join. The bibliography's title
        # for the record names something other than the serialisation the ISBN was found on, and
        # three of those were measured on the first run: a platform advertising the author's other
        # series, a one-shot's page carrying the author's collected volume, and a shop printing an
        # ISBN belonging to another book.
        if j.get("agreement") == "differs":
            continue
        anchor = by_url.get(j.get("platform_url"))
        wid = j.get("madb_work_id")
        if anchor and wid and wid not in out.setdefault(anchor, []):
            out[anchor].append(wid)
    return out


def by_chain(path, web, shared):
    """`chain_joins` over a capture file, or `{}` where the file is not there."""
    import yaml

    f = pathlib.Path(path or "")
    if not f.exists():
        return {}
    return chain_joins(yaml.safe_load(f.read_text()) or {}, web, shared)


def main(argv=None):
    """Assign identifiers over both populations and record the joins that carry evidence."""
    import argparse, collections, datetime, json                            # noqa: E401
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--index", default="data/build/index.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    ap.add_argument("--review", default="data/queue/identity-review.yaml")
    ap.add_argument("--joins", default="data/queue/platform-print-joins.yaml",
                    help="joins established by identifier: the work's own platform page named the "
                         "shop, the shop named the ISBN, and the ISBN named the record")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--merge", nargs=2, metavar=("RETIRED", "SURVIVING"),
                    help="retire one identifier into another. A decision, so it is taken by hand "
                         "and needs --basis; the retired id keeps resolving.")
    ap.add_argument("--attach", nargs=2, metavar=("ANCHOR", "ID"),
                    help="give a work we already hold a second address, for a serialisation the "
                         "database had never seen. Needs --basis. Refuses an anchor another work "
                         "holds, because that would be a merge.")
    ap.add_argument("--attachments", metavar="FILE", nargs="+",
                    help="apply every join in one or more joins files, each carrying its own "
                         "basis. Same operation as --attach and re-runnable: an anchor already on "
                         "its work is left alone, and one held by another work is refused and "
                         "reported. Several files are taken in one call because the assignment "
                         "that follows mints an identifier for any address still unclaimed, and a "
                         "second invocation would be too late for the file it had not read yet.")
    ap.add_argument("--detach", metavar="ANCHOR",
                    help="take an anchor off the work holding it, for a join that was wrong. Needs "
                         "--basis. The reason is stored, so the joins files cannot re-apply it, and "
                         "the record gets an identifier of its own on the next assignment.")
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

    if a.detach:
        if not a.basis:
            raise SystemExit("--detach needs --basis: undoing a join is a finding about the two "
                             "records, and the next run has to be able to read why.")
        held = index(entries).get(a.detach)
        if not held:
            raise SystemExit(f"{a.detach} is held by no work; there is nothing to detach.")
        entries = detach(entries, a.detach, a.basis)
        doc = dict(doc or {}, works=entries)
        print(f"{a.detach} detached from {held}")

    if a.attach:
        if not a.basis:
            raise SystemExit("--attach needs --basis: saying that a serialisation and a book run "
                             "are one work is a claim, and RUNBOOK §11 asks for a field that is "
                             "not the title.")
        entries, err = attach(entries, a.attach[0], a.attach[1], a.basis)
        if err:
            raise SystemExit(err)
        doc = dict(doc or {}, works=entries)

    for _f in a.attachments or []:
        entries, applied, refused = attach_all(
            entries, yaml.safe_load(pathlib.Path(_f).read_text()) or {})
        doc = dict(doc or {}, works=entries)
        print(f"{applied} address(es) attached from {_f}")
        for r in refused:
            print(f"  REFUSED {r}")

    # A URL is shared only where the whole population says so, which is why this is counted here
    # and not inferred per row.
    seen = collections.Counter(w.get("url") for w in web if w.get("url"))
    joined = {}
    for w, p, ev in propose(web, prints):
        if ev["basis"] == "title-and-author":
            joined.setdefault(w["work"], []).append((p, ev))

    # A JOIN ESTABLISHED BY IDENTIFIER, WHICH IS STRONGER THAN THE ONE THIS FILE PROPOSES.
    # `propose` matches a title and then asks for agreement on a person, which is the best that can
    # be done when the two populations share nothing but text. The platform route shares more: the
    # work's own serialisation page names the shop selling its volumes, the shop names the ISBN,
    # and the ISBN names the record. Nothing in that chain is a string comparison, so these are
    # taken without the author test.
    #
    # Keyed on every address the row holds and not only its primary one: a work serialising on two
    # platforms has one primary URL and the join may have been found through the other.
    chain = by_chain(a.joins, web, seen)

    wanted, leads = [], []
    for w in web:
        me = web_anchor(w.get("url"), w.get("work"), seen[w.get("url")] > 1)
        attached = [print_anchor(p.get("id")) for p, _ev in joined.get(w["work"], [])]
        attached += [print_anchor(i) for i in chain.get(me, [])]
        wanted.append((me, attached, w.get("work")))
    # Every print record identifies itself, joined or not, so a C-number always resolves. Where it
    # is already attached to a web work it lands on that work rather than minting a second id, and
    # it passes no title, because the serialisation's title is the one the reader was shown.
    done = ({p.get("id") for ps in joined.values() for p, _ in ps}
            | {i for ids in chain.values() for i in ids})
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
    if chain:
        print(f"  of the joins, {sum(len(v) for v in chain.values())} on "
              f"{len(chain)} work(s) came by identifier rather than by title and author")
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
        # An anchor `assign` derived is re-derived from the data on every run. An anchor somebody
        # attached by hand is not, so its evidence is written beside it or the join becomes an
        # assertion nobody can weigh. Emitted here so that a rewrite of this file keeps it.
        if e.get("attached"):
            L.append("    attached:")
        for at in e.get("attached") or []:
            L.append(f"      - anchor: {js(at.get('anchor'))}")
            L.append(f"        basis: {js(at.get('basis'))}")
            L.append(f"        retrieved: {at.get('retrieved')}")
        # A JOIN THAT WAS UNDONE, AND WHY. Emitted for the same reason as `attached` and with one
        # more: this is what stops the joins files putting it back, so losing it in a rewrite would
        # silently restore the wrong join.
        if e.get("detached"):
            L.append("    detached:")
        for dt in e.get("detached") or []:
            L.append(f"      - anchor: {js(dt.get('anchor'))}")
            L.append(f"        basis: {js(dt.get('basis'))}")
            L.append(f"        retrieved: {dt.get('retrieved')}")
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
