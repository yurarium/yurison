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

SPLIT = re.compile(r"\s*/\s*")


def kata(s):
    """Hiragana to katakana, so a name and its reading can be compared in one script."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def flat(s):
    """The comparison form: one script, no spaces, no interpuncts.

    A reading is written word-separated and a name is not, so `焼肉定食` reads `ヤキニク テイショク`
    and the space is the only difference between them.
    """
    return re.sub(r"[\s　・]", "", kata(s))


def is_reading_of(part, name, store=None):
    """Whether `part` is the reading of `name` and not a second person.

    Two ways, because two things are being caught. A part that folds to the name is the same string
    in two scripts, おにぎりパクパク against オニギリ パクパク. A part matching the name's STORED
    reading catches the kanji case, 蓬餅 against ヨモギモチ, which no fold can reach.
    """
    if not part or not name or part == name:
        return False
    if flat(part) == flat(name):
        return True
    rec = (store or {}).get(name) or {}
    return bool(rec.get("reading")) and flat(rec["reading"]) == flat(part)


def dedupe(author, store=None):
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
        if part in out or any(is_reading_of(part, kept, store) for kept in out):
            continue
        out.append(part)
    return " / ".join(out)


def doubled(author, store=None):
    """How many parts of this field restate a part before it. The measure behind the budget."""
    parts = [p.strip() for p in SPLIT.split(str(author or "")) if p.strip()]
    return max(0, len(parts) - len(SPLIT.split(dedupe(author, store))) if parts else 0)


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
