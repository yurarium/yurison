#!/usr/bin/env python3
"""What this fact is checked on, beside the fact.

These ask about turning a credit FIELD into people. The other checks whose names carry the
word credit ask about identity (does an identifier resolve, does a page list the right work)
or about entities (is this a venue), and they stayed where they are.

COVERS is in the test beside this file.
"""
import pathlib
import re                                                              # noqa: F401
import sys
import unicodedata                                                     # noqa: F401

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

from names import inputs                                               # noqa: E402,F401
from facts import credit as interpunct                                 # noqa: E402,F401

ROOT = pathlib.Path(__file__).resolve().parents[3]

def interpunct_credits_nobody_has_ruled_on(ctx):
    """Credits holding a ・ that the corpus points both ways about, so a person is owed the answer.

    THE ・ IS TWO CHARACTERS WEARING ONE SHAPE. It separates people in 矢立肇・富野由悠季 and sits
    inside one name in くろば・Ｕ, and nothing in either string says which. `interpunct.py` settles
    it on evidence: a piece credited somewhere else on its own is a person, and a piece that appears
    nowhere except inside this string is part of a name. Where some pieces are attested and some are
    not, the evidence points both ways and this is what says so. A wrong split invents a person and
    a wrong join erases one, so neither is worth a guess to keep this at zero.

    IT FALLS BY SOMEBODY WRITING A RULING in `data/identity/interpunct-rulings.yaml`, and it can fall no
    other way: the rule already used every piece of evidence in the corpus before reporting here.
    It also rises when somebody puts a key in that file and leaves the answer out, which is how a
    person marks a case as theirs.

    §14b, WHAT IT DOES NOT SHARE WITH ITS SUBJECT. The evidence is read off credit fields holding no
    ・ at all, so nothing under question contributes to the answer about itself. That is the whole
    reason the module exists: `creditline._is_a_name_of_its_own` asked the name store, the store
    holds くろば and Ｕ because the splitter put them there, and every one of the twelve strings read
    as two people while five of them were being published cut in half.

    WHAT IT CANNOT SEE is a string the corpus settles WRONGLY, because two people share a pen name
    or because a source split somebody by mistake. Only a reader who knows the artist can, and the
    ruling file is where that reader's answer goes.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from facts import credit as interpunct
        from names import inputs
    except Exception:                                                       # noqa: BLE001
        return 0
    fields = []
    for rows, field in ((ctx["index"], "c"), (ctx["series"], "author"),
                        (ctx["releases"], "author"), (ctx["works"], "creator")):
        for row in rows or []:
            value = (row or {}).get(field)
            if isinstance(value, str) and value.strip():
                fields.append(value)
    return len(interpunct.unruled(
        fields, lambda f: [n for n, _r in inputs.split_authors(f, interpunct=False)],
        interpunct.load_rulings(ROOT / interpunct.RULINGS)))


def credit_fields_the_division_does_not_account_for(ctx):
    """Credit fields whose shipped division leaves part of the field unexplained.

    THE NUMBER THAT KEEPS A TIDY ANSWER FROM BEING A LOSSY ONE (§13). The 発売 tab rebuilds a
    byline out of the division, so a division that has lost a contributor would drop that
    contributor from the page in every language with nothing saying so. `creditline.coverage` takes
    the names, the roles and the notation out of the field and reports what is left; where anything
    is, the interface renders the field as written instead of rebuilding it, and this counts how
    often that happens.

    It was 23 when the measure was written and is 0 now: the doubled bracket, the Korean pen names
    and the repeated credit each accounted for a share of it. A rise means the splitter has met a
    shape it cannot divide, and the page it affects is showing the catalogue's own string.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    from names import creditline
    shipped = (ctx["names_shipped"] or {}).get("credit_parts") or {}
    return sum(1 for v in shipped.values() if isinstance(v, dict) and v.get("part"))


def credits_carrying_their_own_cataloguing(ctx):
    """Store records the build declines to publish a rendering for.

    COUNTED ON THE OUTPUT, so the filter is observable (STANDING-INSTRUCTIONS §13). A filter that
    silently drops rows looks identical to one that has stopped working, so this compares the store
    against what shipped instead of asking `entities.kind` again. `はいむらきよたか(キャラクター
    デザイン)` is a person with a role welded on and the store holds the person beside it, so the
    lookup is meant to reach the person; the record is kept and its rendering withheld.

    A rise means a route started writing cataloguing into the author position again, which is what
    `pass4_analyser.is_credit_line` is there to stop.

    FOLDED, because the shipped map is keyed the way the interface asks: `build.py` writes it under
    the folded string so a name reaches it under whichever width and spacing a platform used.
    Comparing raw counts 147 records that shipped perfectly well under their folded key.
    """
    shipped = ((ctx["names_shipped"] or {}).get("authors") or {})
    fold = (lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "").replace("　", ""))
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if v.get("reading") and k not in shipped and fold(k) not in shipped)


def credits_matching_a_chapter(ctx):
    """Credits that name a chapter of the same work.

    WHY NOT A REGEX (§14b). The previous measure carried its own copy of `credits.is_a_person`'s
    pattern, so it could only report what that pattern already catches, and the copies had drifted:
    the check recognised fewer forms than the adapter, missing 第3話, so neither number meant
    what it said.

    THE FAULT IS OBSERVABLE WITHOUT A PATTERN. 平良深姉妹はどっちもヤんでる was credited to
    `金子ある / #1(1)` because a route read a page title's middle field as an author, and that same
    string sits in the platform's feed as a chapter of that work. So compare the credits against the
    chapter names this database already holds for the work. A credit naming a chapter is wrong
    whatever it is made of, and no rule about digits is involved.
    """
    chapters = {}
    for rel in ctx["releases"]:
        w, ep = str(rel.get("work") or ""), str(rel.get("ep") or "").strip()
        if w and ep:
            chapters.setdefault(w, set()).add(unicodedata.normalize("NFKC", ep))
    bad = 0
    for r in ctx["series"]:
        eps = chapters.get(str(r.get("work") or ""))
        if not eps:
            continue
        for part in re.split(r"\s*/\s*", str(r.get("author") or "")):
            if part.strip() and unicodedata.normalize("NFKC", part.strip()) in eps:
                bad += 1
    return bad


def credits_that_restate_a_name(ctx):
    """Credits where one part restates another, asked without the name store.

    WHY NOT THE STORE (§14b). The previous measure compared each part against the store's recorded
    reading of the part before it, which is how `credits.dedupe` decides the same question. The
    measure was blind wherever the fix was blind, read 0, and a reader found
    `田口ケンジ / タグチケンジ` on a live page with every gate green.

    THE SIGNAL IS IN THE STRINGS. A name written partly in katakana keeps that katakana in its
    reading: 田口ケンジ reads タグチケンジ and both end ケンジ. A part written wholly in katakana,
    ending in the same katakana run another part ends in, is restating that part. Nothing here
    consults the store, the analyser, or anything that produced the field.

    WHAT IT CANNOT SEE, named because §14b asks for it. A name carrying no katakana, 蓬餅 against
    ヨモギモチ, leaves no shared run to match on. Those need a reading from somewhere, which is the
    fix's job. This counts a population the store cannot reach, so the two are blind in different
    places instead of the same one.
    """
    kata_tail = re.compile(r"[ァ-ヺー]+$")
    has_kanji = re.compile(r"[一-鿿々]")
    all_kata = re.compile(r"^[ァ-ヺー・\s]+$")
    bad = 0
    for r in ctx["series"]:
        parts = [x.strip() for x in re.split(r"\s*/\s*", str(r.get("author") or "")) if x.strip()]
        for n, part in enumerate(parts):
            if not all_kata.match(part):
                continue
            for other in parts[:n] + parts[n + 1:]:
                if not has_kanji.search(other):
                    continue
                tail = kata_tail.search(other)
                if tail and part.endswith(tail.group(0)) and len(part) > len(tail.group(0)):
                    bad += 1
                    break
    return bad

