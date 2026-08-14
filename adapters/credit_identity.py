#!/usr/bin/env python3
"""Stable identifiers for the credits a work names, and the edge from a work to each of them.

WHY THIS EXISTS. A work names its author in a STRING. `series.json` carries
`原作／宮澤伊織　作画／水野英多` in one field, the interface splits it at render time, and nothing
anywhere is the artist. So there is no edge from a work to the person who drew it, and 2,293 distinct
credit strings sit in the corpus with no way to ask what else any of them made. An author page is a
URL-holding object that links all of one credit's works, so the credit has to become a reference
first, and it has to become the SAME reference the renderer resolves or the page and the store will
disagree about who wrote what.

WHAT AN IDENTIFIER PROMISES, and it is the promise adapters/identity.py already makes for works:
that it never moves and never disappears. Assignment is append-only, lives in
`data/identity/credits.yaml`, and a credit whose two spellings turn out to be one credit does not
lose an id. The retired one gains `merged_into`, still resolves, and lends its anchors to the
survivor, so a link published once keeps working.

WHY OPAQUE AND NOT A NAME SLUG. 華葉 was read ハナハ, then カヨウ, then カバ, all on 2026-08-07.
A romanised slug would have broken twice in a day, and retiring an address is not reversible for
anyone holding a link. Four work identifiers were retired on the same day, each with a stated basis.
An identifier has to survive a renaming and a merge, and a name survives neither.

WHAT AN ANCHOR IS. The credit as filed, folded the way the shipped name map folds it: NFKC, spaces
removed. That fold is the whole of it, deliberately. `identity.fold` also strips brackets, punctuation
and case, which is right for a title arriving from a shop and a library and wrong here, because
`4ka エンピツ` and `4kaエンピツ` are one artist while `2C=がろあ` and `2C＝がろあ` differ by a character
NFKC already settles. The anchor and the interface's lookup key have to be the same string or a page
will hold an identifier the name map cannot answer for.

WHY THE CREDIT AND NOT THE PERSON. The project owner's ruling: the credit is the name, and any
information linking credits is ancillary. A pen name is the object. So this mints an identifier per
credit as filed, including for the 20 credits that are not people at all, and anything later found to
link two credits as one person is recorded beside them rather than replacing one with the other.
`kind` is what stops a company getting a person-shaped page.

WHAT A MERGE IS FOR HERE, and it is the narrow case. Two spellings that are one credit RECORDED
TWICE: MADB writes `かやこ / 海野アロイ / ウミノアロイ / カヤコ`, a name and its reading in the field
where the slash also separates two people, so the store holds four records for two credits. That is
duplication in our data and it merges. Two credits a source filed differently on different works are
two objects, and `homophones` records that the question was asked and answered instead of leaving it
to be re-derived. See `relation` for the test and `data/identity/credit-rulings.yaml` for the calls.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import population  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))

from facts import identity                                                             # noqa: E402
from names import entities                                                  # noqa: E402
from names.inputs import split_credits_detail                               # noqa: E402

PREFIX = "c"
ANCHOR = "credit:"

# The directory a credit's record will live under, once the page exists. Opaque identifier, so the
# word carries no claim about what kind of credit it is: `author/c00301/` would be wrong for
# 円谷プロダクション and for 電撃G'sマガジン, and 20 of these credits are one of those.
ROOT = "credit"

HIRAGANA = re.compile(r"[ぁ-ゖ]")
KATAKANA = re.compile(r"[ァ-ヶ]")
NAMEISH = re.compile(r"[0-9A-Za-zぁ-ヿ㐀-鿿]{2,}")


def credit_key(surface):
    """The comparison key for a credit, which is also the key the shipped name map is written under.

    ONE FOLD, SHARED ON PURPOSE. `build.py` writes `feed/names.json` under NFKC with spaces removed,
    so an anchor folded any other way would give a page an identifier the name map cannot answer for.
    That is STANDING-INSTRUCTIONS §3 with the two producers one commit apart instead of two, and the
    invariant `every shipped credit has an identifier` is what holds them together afterwards.
    """
    return unicodedata.normalize("NFKC", str(surface or "")).replace(" ", "").strip()


def anchor(surface):
    key = credit_key(surface)
    return f"{ANCHOR}{key}" if key else None


def kata(s):
    """Hiragana to katakana, so two spellings of one sound can be compared in one script."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def full_script_flip(a, b):
    """Whether one spelling is the other with its kana converted wholesale between the two scripts.

    THIS IS THE TEST THAT SEPARATES A SOURCE'S HABIT FROM AN ARTIST'S CHOICE, and it is the whole of
    the ruling on 15 of the 82 pairs. A transcriber converting a name converts all of it, so one side
    keeps no hiragana at all: ばったん against バッタン, 4kaえんぴつ against 4kaエンピツ,
    蛙田あめこ against 蛙田アメコ.

    かぼちゃ against カボちゃ fails it, and that is the reason it is written this way. Those two agree
    on the sound and differ in WHICH characters are katakana, leaving ちゃ in hiragana behind カボ,
    which no transcription rule produces and a stylised pen name does deliberately. A shared reading
    is evidence and never proof, so the pair stays two credits.
    """
    a, b = str(a or ""), str(b or "")
    if a == b or kata(a) != kata(b) or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y:
            continue
        if not ((HIRAGANA.match(x) and KATAKANA.match(y))
                or (KATAKANA.match(x) and HIRAGANA.match(y))):
            return False
    # One side has to be clean of hiragana. Both holding some is the partial flip above.
    return not HIRAGANA.search(a) or not HIRAGANA.search(b)


def kana_reading_of(a, b, reading):
    """Whether one spelling is the whole of the other's reading, written in kana.

    THE SHAPE MADB PRODUCES, and 61 of the 82 pairs are it. `schema:creator` states a name and its
    reading in one field with a slash between them, so 秋山はる arrives beside アキヤマハル and the
    store keeps both. `credits.dedupe` already collapses this where the credit is PRESENTED; what is
    left is two records in the store, two entries in the shipped name map, and two identifiers unless
    something says they are one credit.
    """
    ka = kata(credit_key(reading))
    for x, y in ((a, b), (b, a)):
        x, y = credit_key(x), credit_key(y)
        if not x or x == y:
            continue
        if HIRAGANA.search(x) or KATAKANA.search(x):
            if not re.search(r"[㐀-鿿]", x) and kata(x) == ka and x != y:
                # `y` has to be spelt some other way, or this is one string beside itself.
                if re.search(r"[㐀-鿿0-9A-Za-z]", credit_key(y)) or kata(y) != ka:
                    return True
    return False


def relation(a, b, reading):
    """How two spellings sharing one reading are related, as one of four words.

    `full-script-flip` and `kana-reading` are things a SOURCE does to a name, so they propose that one
    credit was recorded twice. `partial-script-flip` and `unrelated` are not, so they propose nothing
    and the pair is left as two credits.

    NOTHING HERE DECIDES. A shape proposes and the ruling document disposes, because the shape cannot
    see what the works and the publishers around a pair say, and on the four pairs where both
    spellings credit works of their own that is what the call turns on.
    """
    if full_script_flip(a, b):
        return "full-script-flip"
    if kata(credit_key(a)) == kata(credit_key(b)):
        return "partial-script-flip"
    if kana_reading_of(a, b, reading):
        return "kana-reading"
    return "unrelated"


def shared_readings(shipped):
    """{reading: [surface]} over every reading the shipped name map gives to more than one credit.

    READ OFF THE FILE A READER IS SERVED, not off the store. The store holds `reading` and only the
    build spells it, folds the key and decides what ships, so asking the store would count records
    rather than the renderings a reader can see two of. 82 readings answer for 164 credits today.
    """
    by = {}
    for key, rec in (shipped or {}).items():
        rd = kata(credit_key((rec or {}).get("reading")))
        if rd:
            by.setdefault(rd, []).append(key)
    return {rd: sorted(v) for rd, v in by.items() if len(v) > 1}


def kind_of(surface):
    """What this credit is, where anything says it is not a person. None is silence, not a person.

    `names.entities` OWNS THE VOCABULARY and this asks it. That module already reads every credit in
    the store for exactly this question and records why each word is in its list, so a second table
    here would be the fourth copy of the role vocabulary its own docstring warns about.
    """
    got = entities.kind(surface)
    return None if got == entities.NOTATION else got


# WHAT SHAPE OF PAGE A KIND MAY HAVE. `person` is the default and the commonest; `venue` exists
# because DEFINITIONS treats a magazine as a place where yuri is published rather than as a party to
# a work, and 電撃G'sマガジン sits in a byline on 剣道娘は異世界でも斬り結ぶ【タテスク】 because the
# platform put it there. A magazine carried as though it were an author is the category error the
# appendix names.
VENUE_KINDS = ("magazine", "desk")
SHAPES = {None: "person", "magazine": "venue", "desk": "venue"}


def shape_of(kind):
    return SHAPES.get(kind, "organisation")


def credits_on(rows):
    """[(surface, work_id, role)] for every credit every row names, in the order they were written.

    `split_credits_detail` IS THE SPLITTER, not a copy of it. The same traversal that feeds the name
    store yields the name, so an identifier is minted for the string the store is keyed on and the
    renderer looks up. A second splitter here is how the page and the store would come to disagree
    about who wrote what.

    THE ROW'S `credits` SUPPLIES THE ROLE AND NEVER THE NAME, and the distinction is the whole of
    the correctness here. A row's `author` is REBUILT from its parts, so the role notation has come
    off by the time this string exists: 3,076 of 3,077 rows named nobody's job and the splitter
    could only ever agree with them. `build.py` records the roles beside the names as it rebuilds,
    which is where the missing half comes from.

    Taking the NAMES from that field as well was tried and it minted nine wrong identifiers in one
    run. The two producers divide the field differently on purpose: the row's copy is built for
    PRINTING, so it keeps ・ inside a name and 渡辺零・駿馬京 stays one string, while a print row's
    copy splits on the slash alone and left `七坂なな, 桜木晶, 河合朗` as a single credit and
    `原案SukeraSparo` with the label welded on. Which way to be wrong differs by what the answer is
    for, which `inputs.SEPARATORS_WHOLE_NAMES` already states; an identifier is not the printing
    caller and must not take the printing caller's answer.

    SO THE ROLE IS MATCHED BY CONTAINMENT. A part the store splits further sits inside the part the
    row recorded, so `[著]七坂なな, 桜木晶` gives all three names the 著 the bracket stated, and
    `原作／宮澤伊織` matches its own name exactly. A name in no recorded part simply keeps whatever
    the splitter found, which is what every release row does.
    """
    out = []
    for r in rows or ():
        wid = r.get("id") if str(r.get("id") or "").startswith("w") else r.get("wid")
        wid = str(wid) if wid else None
        stated = [(str(c.get("name") or ""), c.get("role"))
                  for c in (r.get("credits") or ()) if c.get("role")]
        for name, _reading, role in split_credits_detail(r.get("author") or ""):
            if not role:
                role = next((rl for nm, rl in stated if nm == name), None) or next(
                    (rl for nm, rl in stated if name and name in nm), None)
            out.append((name, wid, role))
    return out


def population(rows, also=None):
    """(wanted, edges): what to mint, and which works each credit is named on with what role.

    `wanted` is in `identity.assign`'s shape so that the minting is that function and not a second
    one. Ordered by first appearance, so a re-run over unchanged data mints nothing and a growing
    corpus appends.

    MINTED FROM THE WORKS LIST AND ONLY FROM IT. `also` holds the release rows, which contribute
    edges and never identifiers, and that asymmetry is deliberate twice over. DEFINITIONS separates a
    work from a release, and a page for a credit links works. More concretely, a release row's credit
    field has not been through the collapse `build.py` runs over the works list, and the eight credits
    the release rows name that the works list does not are mostly damage: `&nbsp;フォローする` is a
    Follow button a page capture handed over as a byline, and `羽田遼亮 中島零 潮一葉 赤衣丸歩郎` is
    four people with nothing but spaces between them, all four of whom already hold an identifier from
    the works row that spells the same field with slashes. Minting there would have published an
    address for a button and an address for nobody.

    The release rows still earn their place: they carry 3 edges the works list does not, among them
    矢立肇 and 富野由悠季 on w00032.
    """
    wanted, seen, edges = [], set(), {}
    for rows_in, minting in ((rows, True), (also or [], False)):
        for surface, wid, role in credits_on(rows_in):
            a = anchor(surface)
            if not a:
                continue
            if a not in seen:
                if not minting:
                    continue
                seen.add(a)
                wanted.append((a, [], surface))
            if wid:
                slot = edges.setdefault(a, [])
                if (wid, role) not in slot:
                    slot.append((wid, role))
    return wanted, edges


def assign(entries, wanted):
    """Mint what is unminted, keeping every existing assignment. `identity.assign` with `c` ids.

    `relabel=False` because a credit's label is the spelling the identifier was minted for. See the
    shared function for the run that proved it.
    """
    return identity.assign(entries, wanted, PREFIX, relabel=False)


def _withdraw(entries, r, retrieved):
    """One `withdraw` ruling applied. `(entries, error)`.

    WHAT A WITHDRAWAL IS FOR. A page title reading `作品 - 作者 | プラットフォーム` is read for its
    middle field, and where a platform puts the newest chapter there instead the chapter arrives as
    a byline. `credits.is_a_person` stops that at the splitter now, which stops the next one; it
    cannot stop the one already minted, because c00268 was published at `credit/c00268/` with a
    person's page around a chapter of 新刊100億冊ください.

    `to` IS NOT THE SAME CLAIM A MERGE MAKES. It says where a reader who followed the dead address
    should end up, and for a chapter mistaken for a byline that is the credit the same field really
    named. Saying the two are one credit would be false, so nothing here lends the withdrawn
    spelling to anybody: `identity.withdraw` detaches the anchor instead.

    AND SOMETIMES THERE IS NOBODY TO SEND THEM TO. `to` was required, which made this unable to
    express the case it is most obviously for. BOOK☆WALKER and GigaViewer write `アンソロジー` in the
    creator field of an anthology, being the format of the book and not a byline at all; c01868 was
    minted and `credit/c01868/` published, headed アンソロジー and telling a reader these are the
    works that name this person. The chapter-title precedent had a successor because the same field
    really did name somebody beside the chapter. This field named nobody, and inventing a successor
    to satisfy the shape would file nine anthologies under whoever was chosen.

    So a withdrawal with no `to` detaches the anchor and retires the identifier with no successor.
    The address goes on resolving, to an identifier that now names nobody, which is what
    `credit identifiers naming nobody` already counts. What a reader sees there is the page for a
    credit with no works, which is true of it.
    """
    surfaces = [s for s in (r.get("surfaces") or []) if s]
    if len(surfaces) != 1:
        return entries, (f"a withdrawal naming {len(surfaces)} spelling(s): {surfaces}. It settles "
                         "one string that is not a credit, so there is no second spelling.")
    if not r.get("basis"):
        return entries, (f"a withdrawal with no basis: {surfaces}. Retiring a published identifier "
                         "is not reversible for anyone holding a link.")
    a = anchor(surfaces[0])
    idx = identity.index(entries)
    wid = idx.get(a)
    if not wid:
        # ALREADY WITHDRAWN, WHICH IS THE ORDINARY CASE AFTER THE FIRST RUN. The anchor is out of
        # the index on purpose, so a re-runnable pass has to look where it went instead of
        # reporting its own last run as a failure.
        if any(e.get("merged_into") and any(d.get("anchor") == a for d in e.get("detached") or [])
               for e in entries):
            return entries, None
        return entries, (f"{surfaces[0]} holds no identifier, so nothing was published for it and "
                         "there is nothing to withdraw. A string the corpus never minted for is "
                         "settled by the splitter alone.")
    if not r.get("to"):
        # NO SUCCESSOR NAMED, which is a statement and not an omission: the string was never a
        # credit, so there is no live credit it belongs to. The anchor is detached so nothing
        # resolves to the identifier again, and the identifier stays retired and empty.
        return identity.detach(entries, anchor(surfaces[0]), r["basis"], retrieved), None
    target = idx.get(anchor(r["to"]))
    if not target:
        return entries, (f"a withdrawal of {surfaces[0]} sending its readers to {r.get('to')!r}, "
                         f"which is not a live credit. Leave `to` out to withdraw with no "
                         f"successor, which is a different statement and is allowed.")
    if target == wid:
        return entries, f"a withdrawal of {surfaces[0]} into itself"
    return identity.withdraw(entries, wid, target, r["basis"], retrieved), None


def apply_rulings(entries, doc, retrieved=None):
    """(entries, retired, attached, kept, refused) for every pair a ruling document has settled.

    RE-RUNNABLE, like `identity.attach_all` and for the same reason: the ruling document is the
    record and this registry is derived from it, so a second run must be a no-op rather than a second
    set of evidence lines. A pair already settled the right way round is left alone.

    A MERGE AND AN ATTACH ARE BOTH HERE, and which one a ruling gets is decided by whether the losing
    spelling holds an identifier. `identity.attach` states the distinction and the cost of getting it
    the wrong way round, and a credit pair meets both halves of it in one document:

      おこさまランチ and お子様ランチ each credit works of their own, so each holds an identifier and
      one of them has to be RETIRED. It keeps resolving and lends its anchors to the survivor.

      カヤコ credits nothing. It reached the store from MADB's creator field for 猫魔法…, which writes
      a name beside its own reading, and `credits.dedupe` had already taken it out of the credit a
      reader sees. So nothing was ever minted for it and nothing can be retired: かやこ's record
      ATTACHES the second spelling, with the basis beside it, and any later run that meets カヤコ in
      a credit field resolves it to the identifier かやこ already holds instead of minting a second.

    Getting those the wrong way round would either retire an identifier nobody published or leave two
    records for one credit with one of them keeping its own id.
    """
    retired_n, attached_n, kept, refused = 0, 0, [], []
    for r in (doc or {}).get("rulings") or []:
        surfaces = [s for s in (r.get("surfaces") or []) if s]
        # A WITHDRAWAL NAMES ONE SPELLING, WHICH IS WHY IT IS TESTED BEFORE THE PAIR RULE. Every
        # other decision here settles two spellings that share a reading. This one settles a string
        # that is not a credit at all and that holds a published identifier, so there is no second
        # spelling to name and `keep` would be a lie: the reader is being sent to a different
        # credit, not to another way of writing the same one.
        if r.get("decision") == "withdraw":
            entries, err = _withdraw(entries, r, retrieved)
            if err:
                refused.append(err)
            else:
                retired_n += 1
            continue
        if len(surfaces) < 2:
            refused.append(f"a ruling naming fewer than two spellings: {r}")
            continue
        ids = {s: identity.index(entries).get(anchor(s)) for s in surfaces}
        if r.get("decision") == "keep":
            kept.append(dict(r, ids=ids))
            continue
        # NEITHER SPELLING IS A CREDIT. `ほか` and `他` share a reading and are the cataloguing word
        # a bibliography closes an anthology credit with: `[著]仲谷鳰 ほか` names one contributor and
        # says there are more. `inputs.NOT_A_NAME` drops both, so no identifier exists for either and
        # there is nothing to merge or to relate. The pair is settled here so it stops being counted
        # as a question nobody has answered.
        if r.get("decision") == "not-a-credit":
            if any(ids.values()):
                refused.append(f"{surfaces} is filed as not a credit and yet holds an identifier: "
                               f"{ {k: v for k, v in ids.items() if v} }")
            continue
        if r.get("decision") != "merge":
            refused.append(f"a ruling with no decision on it: {surfaces}")
            continue
        if not r.get("basis"):
            refused.append(f"a merge with no basis: {surfaces}. Saying that two spellings are one "
                           "credit is a claim, and where it retires an identifier it is not "
                           "reversible for anyone holding a link.")
            continue
        keep = r.get("keep")
        if keep not in surfaces:
            refused.append(f"a merge whose surviving spelling is not one of its own: {surfaces}")
            continue
        winner = ids.get(keep)
        if not winner:
            refused.append(f"{keep} holds no identifier, so nothing can be merged into it. The "
                           "surviving spelling has to be one the corpus credits.")
            continue
        for s in surfaces:
            if s == keep:
                continue
            loser = ids.get(s)
            if loser == winner:
                continue
            if loser:
                entries = identity.merge(entries, loser, winner, r["basis"])
                retired_n += 1
                continue
            before = len(identity.index(entries))
            entries, err = identity.attach(entries, anchor(s), winner, r["basis"], retrieved)
            if err:
                refused.append(err)
            elif len(identity.index(entries)) > before:
                attached_n += 1
    return entries, retired_n, attached_n, kept, refused


def unruled(shipped, doc):
    """Readings the shipped map gives to several credits that no ruling has settled.

    THE BUDGET'S SUBJECT, and it is at zero once the 82 are ruled on. A reading newly sourced can put
    two credits together that nobody has looked at, and this is what makes that arrive as a number
    that has risen rather than as one artist quietly holding two addresses.
    """
    ruled = {frozenset(credit_key(s) for s in (r.get("surfaces") or []))
             for r in (doc or {}).get("rulings") or []}
    out = []
    for rd, surfaces in sorted(shared_readings(shipped).items()):
        if frozenset(credit_key(s) for s in surfaces) not in ruled:
            out.append((rd, surfaces))
    return out


def uncovered(field, surfaces):
    """The name-shaped runs of a credit field that no registered spelling accounts for.

    THE MEASURE THAT DOES NOT SHARE THE ASSIGNER'S BLIND SPOT (§14b). Everything above finds a credit
    with `split_credits_detail`, so a count that asked the same splitter could only ever report what
    the splitter already handles: the fault that reached a reader on w01478 survived because the
    measure and the fix asked the same question. This asks a different one. It deletes every
    registered spelling from the field AS SHIPPED and reports what is left that still looks like a
    name, which is arithmetic on the string and owes nothing to the splitter, the fold, the store or
    the registry lookup.

    IT COUNTS CANDIDATES AND NOT FAULTS. A role label is name-shaped and legitimately unregistered,
    so 原作 and 著者 land in the residue and the number is not zero. That is the honest reading of
    what it measures, and excluding them would mean holding a copy of the role vocabulary here, which
    is the third shape §14b names.

    WHAT IT CANNOT SEE: a field covered by registered spellings that are the wrong people. No count
    can see that; only a reader following the credit to the work will.
    """
    rest = credit_key(field)
    if not rest:
        return []
    # Longest first, so 田口囁一 is not left half-deleted by 田口.
    for s in sorted((x for x in surfaces if x), key=len, reverse=True):
        if s in rest:
            rest = rest.replace(s, "\n")
    return [m.group(0) for m in NAMEISH.finditer(rest)]


def load(path):
    """(entries, doc) from a credits registry, or ([], {}) where there is none.

    `credit` is the file's word for what `identity.assign` calls `title`, and the two are mapped here
    rather than in nine places. The shared function labels the object it is minting for and a credit
    is not a title, so the file says `credit` and the boundary translates.
    """
    import yaml

    f = pathlib.Path(path or "")
    if not f.exists():
        return [], {}
    doc = yaml.safe_load(f.read_text()) or {}
    entries = []
    for e in doc.get("credits") or []:
        e = dict(e)
        e["title"] = e.pop("credit", None)
        entries.append(e)
    return entries, doc


def save(path, entries, kept, generated):
    """Write the registry whole. Append-only in content: nothing here drops an entry."""
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Credit identifiers. Append-only: an id is never reassigned and never withdrawn.",
         "#",
         "# A credit is what a source wrote in the author field, and it is the object: the project",
         "# owner's ruling is that the credit is the name and that anything linking two credits is",
         "# ancillary. `kind` is absent for a person and names what the credit is otherwise, so that",
         "# a company or a magazine does not get a person-shaped page.",
         "#",
         "# An anchor is the credit folded the way feed/names.json folds it, NFKC with spaces",
         "# removed. A merged entry keeps `merged_into`, stays resolvable, and lends its anchors to",
         "# the survivor, because an address published once has to keep working.",
         "#",
         "# See adapters/credit_identity.py and data/identity/credit-rulings.yaml.",
         f"generated: {generated}", "credits:"]
    for e in sorted(entries, key=lambda x: x.get("id") or ""):
        L.append(f"  - id: {e['id']}")
        L.append(f"    credit: {js(e.get('title'))}")
        if e.get("kind"):
            L.append(f"    kind: {js(e['kind'])}")
        if e.get("merged_into"):
            L.append(f"    merged_into: {e['merged_into']}")
            L.append(f"    merge_basis: {js(e.get('merge_basis'))}")
        # `[]` RATHER THAN A BARE KEY, because a withdrawal leaves an entry with no anchors at all
        # and `anchors:` on its own parses as null. Two spellings of empty in one file is how a
        # reader stops being able to tell an absence from a hole.
        L.append("    anchors:" if e.get("anchors") else "    anchors: []")
        for x in e.get("anchors") or []:
            L.append(f"      - {js(x)}")
        # An anchor the pass derived is re-derived from the corpus on every run and is checkable
        # against it. An anchor a ruling attached is not, so its evidence is written beside it or the
        # second spelling becomes an assertion nobody can weigh. Same rule as the works registry.
        if e.get("attached"):
            L.append("    attached:")
        for at in e.get("attached") or []:
            L.append(f"      - anchor: {js(at.get('anchor'))}")
            L.append(f"        basis: {js(at.get('basis'))}")
            L.append(f"        retrieved: {at.get('retrieved')}")
        # THE SPELLING AN IDENTIFIER WAS MINTED FOR, WHERE IT TURNED OUT NOT TO BE A CREDIT. A
        # withdrawal takes the anchor out of the index rather than lending it to the survivor, so
        # this is the only remaining record of what the address was published as, and losing it
        # would make the withdrawal unreadable and let the string be minted for a second time.
        if e.get("detached"):
            L.append("    detached:")
        for dt in e.get("detached") or []:
            L.append(f"      - anchor: {js(dt.get('anchor'))}")
            L.append(f"        basis: {js(dt.get('basis'))}")
            L.append(f"        retrieved: {dt.get('retrieved')}")
    L.append("")
    L.append("# Credits sharing one reading that were examined and KEPT APART. Recorded so the")
    L.append("# question is not re-derived at every capture and so the reasoning is not lost each")
    L.append("# time, which is what DEFINITIONS §9 does for a work a rebuttal examined and upheld.")
    L.append("# A relation is not a merge: two credits a source filed differently on different works")
    L.append("# are two objects, and saying they may be one person is information hung beside them.")
    L.append("homophones:")
    for r in sorted(kept, key=lambda x: str(x.get("reading"))):
        ids = r.get("ids") or {}
        L.append(f"  - reading: {js(r.get('reading'))}")
        L.append("    credits:")
        for s in r.get("surfaces") or []:
            L.append(f"      - id: {ids.get(s) or 'null'}")
            L.append(f"        credit: {js(s)}")
        L.append(f"    shape: {js(r.get('shape'))}")
        L.append(f"    basis: {js(r.get('basis'))}")
    L.append("")
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))


def save_edges(path, entries, edges, generated):
    """The work-to-credit edge, derived and rewritten whole on every run.

    KEPT OUT OF THE REGISTRY BECAUSE IT IS NOT A DECISION. The registry is append-only and holds
    identifiers and the merges somebody ruled on; this is re-derived from the corpus every run and is
    checkable against it. Mixing the two would put several thousand lines of derived churn through a
    file whose value is that a line in it never changes.

    THE ROLE IS ON THE EDGE. One person is 原作 on one work and 作画 on another, so it is a fact
    about the pairing and not about either end.

    ONE LINE PER PAIRING, whatever the corpus states about it. The works list writes a credit field
    with the role notation already taken off and the release rows keep it, so the same credit reaches
    the same work twice, once bare and once labelled. Emitting both put `w01225` under c00024 twice
    and would have read on a page as somebody working on one book two separate times.
    """
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    live = identity.index(entries)
    by_id = {}
    for a, pairs in edges.items():
        cid = live.get(a)
        if not cid:
            continue
        for wid, role in pairs:
            slot = by_id.setdefault(cid, {}).setdefault(wid, [])
            if role and role not in slot:
                slot.append(role)
    L = ["# Which works each credit is named on, and in what role.",
         "#",
         "# DERIVED. Rewritten whole on every run from the corpus, so nothing here is a decision and",
         "# nothing here is worth editing. The identifiers come from data/identity/credits.yaml and",
         "# resolve through a merge, so a credit recorded twice reports its works once.",
         "#",
         "# `roles` is absent far more often than it is present, and that is the corpus rather than",
         "# this pass: the works list carries credit fields with the notation already taken off, so",
         "# 3,076 of its 3,077 rows name nobody's job. The labels come from the release rows, which",
         "# keep the field as the platform wrote it. See docs/GAPS.md.",
         f"generated: {generated}", f"count: {len(by_id)}", "credits:"]
    for cid in sorted(by_id):
        L.append(f"  - id: {cid}")
        L.append("    works:")
        for wid in sorted(by_id[cid], key=lambda w: w or ""):
            L.append(f"      - id: {wid}")
            if by_id[cid][wid]:
                L.append(f"        roles: [{', '.join(js(r) for r in sorted(by_id[cid][wid]))}]")
    L.append("")
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))
    return by_id


def retired(entries):
    """{retired id: the id it became}, for the forwarders a merge has to leave behind."""
    return {str(e["id"]): str(e["merged_into"]) for e in entries or ()
            if e.get("merged_into") and e.get("id")}


# `forwarders` MOVED WITH THE RENDERING IT DID, §11. It returned HTML for every retired credit id,
# which is a page rather than a fact about identity, and the repository that renders pages is the
# one that should decide what a forwarder says. `retired` above is what it needed from here and is
# what stayed: which identifier became which is this repository's answer.

def rows_from(build):
    """(works rows, release rows). Both carry a credit field and only the first mints one."""
    import json

    b = pathlib.Path(build)
    works = list(population.series())
    releases = []
    for f in [b / "feed" / "current.json"] + sorted((b / "feed").glob("[0-9]*.json")):
        if f.exists():
            releases += json.loads(f.read_text()).get("releases") or []
    return works, releases


def main(argv=None):
    import argparse, collections, datetime, json                            # noqa: E401

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--registry", default="data/identity/credits.yaml")
    ap.add_argument("--edges", default="data/identity/credit-works.yaml")
    ap.add_argument("--rulings", default="data/identity/credit-rulings.yaml",
                    help="what was decided about each pair of credits sharing a reading. A merge "
                         "needs a basis, and the pair it does not settle is counted rather than "
                         "assumed.")
    ap.add_argument("--propose", action="store_true",
                    help="print a draft ruling for every unruled pair, with the shape and the "
                         "counts the call turns on. It states what was measured and decides "
                         "nothing: the decision is written into the rulings file by a person.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    today = datetime.date.today().isoformat()
    works, releases = rows_from(a.build)
    shipped = (population.names(pathlib.Path(a.build) / "feed" / "names.json"
                               if (pathlib.Path(a.build) / "feed" / "names.json").exists()
                               else None)
               .get("authors") or {})
    rdoc = {}
    rp = pathlib.Path(a.rulings)
    if rp.exists():
        rdoc = yaml.safe_load(rp.read_text()) or {}

    entries, _doc = load(a.registry)
    before = len(entries)
    wanted, edges = population(works, releases)
    entries, conflicts = assign(entries, wanted)

    # The kind is re-derived every run, because the vocabulary in `names.entities` grows and a credit
    # marked before it grew would keep an answer nobody would give now.
    for e in entries:
        got = kind_of(e.get("title"))
        if got:
            e["kind"] = got
        else:
            e.pop("kind", None)

    entries, retired_n, attached_n, kept, refused = apply_rulings(entries, rdoc, today)

    if a.propose:
        for rd, surfaces in unruled(shipped, rdoc):
            print(yaml.safe_dump([{
                "reading": rd, "surfaces": surfaces,
                "shape": relation(surfaces[0], surfaces[1], rd) if len(surfaces) == 2 else "several",
                "decision": None, "keep": None, "basis": None,
                "works": {s: sorted({w for a2, ps in edges.items() if a2 == anchor(s)
                                     for w, _r in ps}) for s in surfaces},
            }], allow_unicode=True, sort_keys=False, width=100), end="")

    live = [e for e in entries if not e.get("merged_into")]
    shapes = collections.Counter(shape_of(e.get("kind")) for e in live)
    kinds = collections.Counter(e["kind"] for e in live if e.get("kind"))
    left = unruled(shipped, rdoc)
    print(f"{len(entries)} credit identifier(s), {len(entries) - before} new; "
          f"{len(live)} live, {len(entries) - len(live)} retired into another; "
          f"{dict(shapes)}")
    if kinds:
        print("  not a person: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    print(f"  rulings applied: {retired_n} identifier(s) retired into another, {attached_n} second "
          f"spelling(s) attached to a credit that had one, {len(kept)} pair(s) kept apart")
    print(f"  readings shared by several credits with no ruling: {len(left)}")
    for rd, surfaces in left:
        print(f"    UNRULED {rd}: {' | '.join(surfaces)}")
    for r in refused:
        print(f"    REFUSED {r}")
    for c in conflicts:
        print(f"    CONTESTED {c['anchor']}: held by {c['held_by']}, claimed by {c['wanted_by']}")

    if a.dry_run:
        return 0

    save(a.registry, entries, kept, today)
    by_id = save_edges(a.edges, entries, edges, today)
    roled = sum(1 for v in by_id.values() for r in v.values() if r)
    print(f"  -> {a.registry}  and  {a.edges}  "
          f"({sum(len(v) for v in by_id.values())} edge(s) over {len(by_id)} credit(s), "
          f"{roled} of them naming a role)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
