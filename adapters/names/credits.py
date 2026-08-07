#!/usr/bin/env python3
"""One credit field, with a name and its own reading counted once.

WHY THIS EXISTS. MADB states a name and its reading in one `schema:creator` field with a slash
between them, and the slash is the same character that separates two people. So 蓬餅 / ヨモギモチ is
one person written twice, and 運命のヤマダダダダダダダダダダ was credited to
`おにぎりパクパク / オニギリ パクパク`. 18 rows carried a credit that is the reading of the credit
beside it.

WHY THE SCRIPT IS NOT THE TEST. `adapters/madb/extract.people` drops any part written wholly in
katakana, which is right often enough to pass its own use and wrong as a general rule: サブロウタ,
コダマナオコ, アキリ and ヨルモ are people, and a rule keyed on script deletes them. The question is
not what script a part is in. It is whether that part is the reading OF THE PART BEFORE IT, which
takes either the store's recorded reading or a kana fold, and never a guess about the alphabet.

WHY NOT AT INGEST. The source record says what the source said, which REQUIREMENTS §4 requires and
which is what makes a claim re-checkable later. MADB really does put both forms in that field.
Removing one there would edit the evidence, so the duplicate is collapsed where the credit is
PRESENTED and the record keeps the field intact.
"""
import re
import unicodedata

SPLIT = re.compile(r"\s*/\s*")

# THE SEPARATORS A CREDIT FIELD PUNCTUATES WITH. A series row writes ` / ` and a releases row
# writes `, `, as in `おだまさる, 佐島勤, 石田可奈, 森夕`, so a composer that knew one of them left
# 49 of 191 release rows rendering their authors in Japanese on an English page.
#
# `split_credits` no longer splits on this. It asks inputs.split_authors, which knows the role
# notation as well as the punctuation. What is left here is the MEASURE, `candidate_doubles`, and
# it keeps its own crude split ON PURPOSE (§14b): a measure that splits the way the fix splits can
# only ever report what the fix already handles.
SEPARATORS = re.compile(r"\s*[/／,，、]\s*")

JAPANESE = re.compile(r"[぀-ヿ一-鿿々]")
ROMAJI_STYLES = ("macron", "double", "plain")

RUBY_KANJI = re.compile(r"[一-鿿々]")
RUBY_KANA = re.compile(r"[ぁ-ゖァ-ヿ]")


def kata(s):
    """Hiragana to katakana, so a name and its reading can be compared in one script."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def flat(s):
    """The comparison form: one script, no spaces, no interpuncts.

    A reading is written word-separated and a name is not, so `焼肉定食` reads `ヤキニク テイショク`
    and the space is the only difference between them.
    """
    return re.sub(r"[\s　・]", "", kata(s))


def is_reading_of(part, name, store=None, read=None):
    """Whether `part` is the reading of `name` and not a second person.

    A part that folds to the name is the same string in two scripts, おにぎりパクパク against
    オニギリ パクパク. A part matching the name's STORED reading catches the kanji case, 蓬餅
    against ヨモギモチ, which no fold can reach.

    `read` catches the case both of those miss, and it reached a reader: w01478 shipped its author
    as 田口ケンジ / タグチケンジ. The fold fails because 田口ケンジ holds a kanji and folds to
    itself, and the store fails because a credit line is never fed to the naming pass, so neither
    half of that field is in the store to be looked up. Given a callable that can read a name, the
    duplicate collapses. It arrives as a parameter, which keeps this module pure and lets its test
    run offline with a stub.

    THE COMPARISON IS EXACT, WHICH IS WHAT MAKES THE ANALYSER SAFE HERE. An analyser is at its
    weakest on pen names, and a wrong reading simply fails to equal the part beside it and both
    credits are kept. It can only collapse a pair it read exactly onto its neighbour.
    """
    if not part or not name or part == name:
        return False
    if flat(part) == flat(name):
        return True
    rec = (store or {}).get(name) or {}
    if rec.get("reading") and flat(rec["reading"]) == flat(part):
        return True
    if read is None:
        return False
    got = read(name)
    return bool(got) and flat(got) == flat(part)


def dedupe(author, store=None, read=None):
    """The credit field with any part that merely reads a part before it removed.

    ORDER IS KEPT AND NOTHING IS REWRITTEN. A credit list is a list of people in the order the
    source gave them, so this only ever drops; it never reorders, respells, or merges two names
    into one. A field naming one person comes back unchanged.

    Only a LATER part can be dropped. `一迅社 / 田口囁一 / イチジンシャ / タグチショウイチ` is two
    credits written four times, and the two that go are the two that restate what came before.
    """
    parts = [p.strip() for p in SPLIT.split(str(author or "")) if p.strip()]
    if len(parts) < 2:
        return str(author or "")
    out = []
    for part in parts:
        # An exact repeat is one person too. `is_reading_of` says no to it deliberately, because a
        # string is not a READING of itself, so the plain repeat is caught here instead.
        if part in out or any(is_reading_of(part, kept, store, read) for kept in out):
            continue
        out.append(part)
    return " / ".join(out)


def doubled(author, store=None, read=None):
    """How many parts of this field restate a part before it. The measure behind the budget."""
    parts = [p.strip() for p in SPLIT.split(str(author or "")) if p.strip()]
    return max(0, len(parts) - len(SPLIT.split(dedupe(author, store, read))) if parts else 0)


def candidate_doubles(author):
    """Fields where a part MIGHT be the reading of another, judged without a store or a reader.

    THE MEASURE HAS TO SEE PAST THE FIX'S BLIND SPOT. `doubled` above asks the store, and the
    budget built on it read zero while 田口ケンジ / タグチケンジ was live on the site, because the
    store holds neither half. A check that assumes what its subject assumes cannot report the
    subject's failures.

    So this asks a question neither the store nor an analyser can duck: does the field hold a part
    written wholly in katakana beside a part holding a kanji. That is the SHAPE of a name written
    twice. It counts candidates and not faults, because two people can be written that way, and
    the candidates a fix leaves behind are the honest residue.
    """
    parts = [p.strip() for p in SEPARATORS.split(str(author or "")) if p.strip()]
    if len(parts) < 2:
        return 0
    kana_only = [p for p in parts if re.fullmatch(r"[ァ-ヿ\s　・ー]+", p)]
    has_kanji = [p for p in parts if re.search(r"[一-鿿々]", p)]
    return min(len(kana_only), len(has_kanji)) if kana_only and has_kanji else 0


def readable_ruby(spans):
    """The furigana spans, or None where one of them could not be read aloud.

    A run of N kanji needs at least N kana over it. That is arithmetic, so this catches only the
    impossible ones and leaves the surprising alone: 承る is one kanji under four kana.

    WHY IT IS HERE. Composing a field publishes spans the store has held all along and nothing ever
    printed. 電撃G'sマガジン is stored with で over 電撃G and んげきじーず over s, which is one
    misalignment in an entry for a magazine sitting in an author field. The reading and the
    romanisation of that part are fine; the furigana is not, so the part keeps them and loses its
    ruby instead of blocking the whole field.
    """
    if not spans:
        return None
    for span in spans:
        if not isinstance(span, (list, tuple)):
            return None
        base, rt = (list(span) + [None, None])[:2]
        if not rt:
            continue
        if len(RUBY_KANJI.findall(str(base or ""))) > len(RUBY_KANA.findall(str(rt))):
            return None
    return list(spans)


def split_credits(raw):
    """The people a credit field names, and the separator to put back between them.

    THE SPLITTING IS `inputs.split_authors`, NOT A SECOND COPY OF IT. This file grew its own
    separator list and its own notation stripping, and the two drifted exactly the way §3 says
    they will. Three shapes were live on the site because of it, and every one of them was already
    handled by the splitter that feeds the name store:

      `原作/大鷹シン 漫画/ホマレ`  the slash separates a ROLE from a NAME, so 原作 became a person
      `冬眠結(漫画) 橙々(原作)`    two credits with nothing but a space between them
      `石田可奈(キャラクターデザイン)`  a role welded to a name matches nothing in the store

    The one place the two callers genuinely disagree is ・, which the store may split and a printed
    line may not, and that is an argument now rather than a fork. See inputs.SEPARATORS_WHOLE_NAMES.

    The separator is returned rather than fixed because a composed rendering has to read the way
    the field it replaces read. A releases row that arrived comma-separated must not come back
    slash-separated: the reader would see one row punctuated unlike every row around it.
    """
    s = str(raw or "")
    from names.inputs import split_authors
    parts = [n for n, _reading in split_authors(s, interpunct=False) if n]
    joiner = " / " if re.search(r"[/／]", s) else ("、" if "、" in s else ", ")
    return parts, joiner


def spliced_ruby(raw, parts, got):
    """Furigana over the credit field AS WRITTEN, with each name annotated where it stands.

    THE RUBY HAS TO COVER THE SURFACE, which is what `ruby covers its surface` asserts. Composing
    the spans by joining the people together with a separator worked only while the splitter's
    parts added up to the whole field. They no longer do: the notation comes off now, so a joined
    set covered `大鷹シン / ホマレ` where the field reads `原作/大鷹シン 漫画/ホマレ`, and the
    Japanese page would have printed the credit with its roles deleted. Annotating is not the same
    as rewriting, and in Japanese mode the reader is owed the string the source wrote.

    Where a name cannot be found in the field the whole set collapses to one bare span. That is the
    same fallback `readable_ruby` takes and for the same reason: furigana over the wrong characters
    is worse than none, and a set that does not cover its surface is exactly that.
    """
    out, rest = [], raw
    for p, e in zip(parts, got):
        at = rest.find(p)
        if at < 0:
            return [[raw, None]]
        if at:
            out.append([rest[:at], None])
        out.extend(readable_ruby(e.get("ruby")) or [[p, None]])
        rest = rest[at + len(p):]
    if rest:
        out.append([rest, None])
    return out


def already_latin(p, e=None):
    """A rendering for a credit that needs no romanising, or None where it does need one.

    A CREDIT ALREADY IN LATIN IS ITS OWN ROMANISATION and needs no store record. The commonest are
    the full-width names on BOOK☆WALKER's translated editions, Ｍａｇｐｉｅ and Ｎｉｍｒｏｄ and
    ＩｃｅＦａｉｒｙ, which NFKC folds to ordinary Latin. Demanding a reading for them held back
    every field they appear in. They take no ruby, which is what `no ruby over bare Latin` already
    requires.

    BEING IN THE STORE IS NOT BEING RESOLVED, and reading it as such shipped 35 rows with a
    Japanese author line in English-only mode. `Akeo` is stored with `script: latin` and no reading
    and no romanisation, correctly, and the field it appears in then intersected romanisation
    styles across its credits, came out empty, and rendered nothing at all for all three names.
    This is asked whenever a credit yields no romanisation, whether or not the store holds the name.

    THE SURFACE DECIDES, NOT THE STORE'S `en`. A Japanese name with an English rendering has a
    translation, and a translation is not a romanisation: taking it here would put a licensor's
    wording where the sound of the name belongs. `en` is preferred only once the surface has shown
    it needs no romanising.
    """
    flat = unicodedata.normalize("NFKC", p)
    if JAPANESE.search(flat):
        return None
    stated = str((e or {}).get("en") or "").strip()
    if stated and not JAPANESE.search(unicodedata.normalize("NFKC", stated)):
        flat = stated
    return {"reading": flat, "ruby": [[p, None]],
            "romaji": {s: flat for s in ROMAJI_STYLES},
            "reading_basis": (e or {}).get("reading_basis") or "stated",
            **({"unverified": True} if (e or {}).get("unverified") else {})}


def compose(raw, lookup):
    """One rendering for a credit field naming several people, or None.

    WHY THIS EXISTS. The name store holds one record per PERSON, and the views asked it for the
    whole field. `原田重光 / 蘇募ロウ` matched nothing, so 373 series rows shipped with no author
    rendering, and 49 of 191 release rows did the same with a comma between the names. Both views
    call this now, because solving it once per view is how the two got different answers.

    `lookup(name)` returns that person's rendering, or None. Everything else is here.

    THE SEPARATOR IS PART OF THE ANSWER. A composed rendering keeps it between the credits in the
    reading, in the ruby and in each romanisation, because it is a list of people and running them
    together would invent a single name nobody has.

    ALL OF THEM OR NONE. A field composes only when every credit in it resolves. A partial
    composition puts an unresolved Japanese name into `romaji` and into English-only mode, and it
    is worse than composing nothing: the interface prefers a rendering where one exists, so a
    half-made one SUPPRESSES the fallback to the Japanese the reader would otherwise have seen.
    """
    parts, joiner = split_credits(raw)
    if not parts:
        return None
    if len(parts) == 1:
        # ONE PERSON IS NOT A COMPOSITION, AND STILL NEEDS FINDING. 126 of the 192 series rows
        # showing a Japanese author in English mode named ONE person, 96 of them with `(著者)`
        # after the name. The caller looks the whole field up, `はちこ(著者)` matches nothing, and
        # the composer declined to look at a field with a single credit in it, so the notation had
        # nowhere to come off.
        #
        # The store's record is returned AS IT STANDS. Nothing is being joined, so there is no
        # composed name to describe, and rewriting the basis here would relabel a translation as a
        # romanisation.
        #
        # Only where the notation changed the string: where it did not, the caller has already run
        # this exact lookup and got nothing back.
        p = parts[0]
        if p == str(raw or "").strip():
            return None
        e = lookup(p)
        if not ((e or {}).get("romaji") or (e or {}).get("en")):
            e = already_latin(p, e)
        if not e:
            return None
        # THE RUBY STILL HAS TO COVER THE FIELD, notation and all. The record's own spans cover the
        # person's name, and the field around it is `はちこ(著者)`.
        return {**e, "ruby": spliced_ruby(str(raw or ""), [p], [e])}
    got = []
    for p in parts:
        e = lookup(p)
        if not (e or {}).get("romaji"):
            e = already_latin(p, e)
            if e is None:
                return None
        got.append(e)

    out = {"reading": joiner.join(str(e.get("reading") or "") for e in got)}
    out["ruby"] = spliced_ruby(str(raw or ""), parts, got)
    styles = set(got[0].get("romaji") or {})
    for e in got[1:]:
        styles &= set(e.get("romaji") or {})
    if not styles:
        return None
    out["romaji"] = {s: joiner.join((e.get("romaji") or {})[s] for e in got) for s in styles}
    # The weakest part decides. A composed name is only as attested as its least attested credit,
    # and saying otherwise would let one stated reading vouch for a guessed one beside it.
    out["reading_basis"] = ("analyser" if any(e.get("reading_basis") == "analyser" for e in got)
                            else (got[0].get("reading_basis") or "stated"))
    out["basis"] = "romaji"
    if any(e.get("unverified") for e in got):
        out["unverified"] = True
    return out


# A credit made only of digits, markup and punctuation. `#1(1)`, `７`, `第3話`.
NOT_A_PERSON = re.compile(r"^(?:[#＃]?\d+[(（]?\d*[)）]?|第?\s*[\d０-９]+\s*[話回章巻]?|[\d\W_]+)$")


def is_a_person(name):
    """Whether a captured credit could be somebody's name.

    WHAT THIS IS FOR. A page title reading `作品 - 作者 | プラットフォーム` is read for its middle
    field, and where a platform puts the newest chapter there instead the chapter becomes the
    author: 平良深姉妹はどっちもヤんでる was credited to `金子ある / #1(1)`, and the same string sits
    in that platform's own feed as a chapter. BOOK☆WALKER gave `７` as the creator of a book whose
    publisher is ななつぼし.

    A WHOLE credit of digits and punctuation is the test, so a person whose name merely contains
    one survives: タイザン5 and 帯屋ミドリ2 are pen names.
    """
    s = str(name or "").strip()
    return bool(s) and not NOT_A_PERSON.match(s)
