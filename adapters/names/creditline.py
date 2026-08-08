#!/usr/bin/env python3
"""How a credit field divides, in the form the interface renders it from.

WHY THIS EXISTS AND WHAT IT REPLACES. kari/app.js held two readers of the same notation. `credit()`
glossed a role inside square brackets against a table of six words and then looked the rest up as a
name, and `creditNames()` split on the slash, took a leading bracket off with `stripRole` and looked
each piece up. Neither knew about a role in round brackets, a doubled bracket, `ほか`, an ampersand
or an interpunct, so `南部くまこ(作) / 東河みそ(絵)` matched nothing in a store holding both people
and came out in Japanese under an English heading. Two of the three roles the corpus states most
often were in neither table.

The rule for dividing a credit field already exists once, in `names.inputs.split_credits_detail`,
and it is the rule the name store is keyed on. So the division is computed HERE, at build time, by
that function, and shipped. The interface renders what it is given and divides nothing
(STANDING-INSTRUCTIONS §3).

WHAT THIS ADDS TO THE SPLITTER, and it is two things, both of which need the name store and so
cannot live inside a splitter that runs before the store exists:

  THE INTERPUNCT, WHICH IS AMBIGUOUS AND CAN BE ASKED. 矢立肇・富野由悠季 is two people and
  るいす・まくられん is one, and nothing in either string says which. `inputs` states the dilemma and
  resolves it by caller: splitting for the store, keeping whole for printing. A third answer is
  available to a caller that can consult the store: split only where EVERY piece is a name the
  store can render. A wrong split then costs nothing a reader can see, because a split that would
  print half of somebody's name never happens.

  THE READING PRINTED BESIDE THE NAME. MADB writes one creator as `紬めめ / ツムギメメ`, the name
  and its own reading, and printing both makes the reading look like a second artist. That rule was
  inside `creditNames` and is here now, because the division is one fact.

WHAT IT DOES NOT DO. It never drops a credit to make the answer tidy. `coverage()` says what of the
field the division does not account for, `build.py` counts it, and the interface falls back to the
field as written where the answer is incomplete. A byline that quietly loses a company is worse
than one a reader can see is in Japanese.
"""
import re

from . import inputs
from . import kana

# What is left over when the names are taken out and is still only notation. Anything else means
# the division has lost something the field said, which `coverage` reports and nobody may hide.
NOTATION = re.compile(r"^[\s　\[\]()（）〔〕【】/／、,，・･&＆:：;；'\"’”ー\-–—]*$")

# `ほか` and `他` close a credit that names some of its contributors and stops. `inputs.NOT_A_NAME`
# holds both for the splitter, and the field means "and others", which is a thing to say in English
# rather than a thing to drop.
OTHERS = re.compile(r"ほか|他")

KATAKANA_ONLY = re.compile(r"^[゠-ヿ・ー\s　]+$")


def _is_a_name_of_its_own(piece, store):
    """Whether the store states a reading for this piece, which is what licenses a split.

    THE TEST IS A SOURCED READING AND NOT "COULD THIS BE SHOWN". The looser test asks for a
    record, or for no Japanese in the piece at all, and it divides `さりい・Ｂ`: Ｂ has a record of
    its own and is Latin, so both halves passed and one artist became two. It is the counter-case `inputs` records beside
    SEPARATORS_WHOLE_NAMES and the reason ・ is not a separator for a caller that prints.

    A romanisation the store holds is a positive statement that somebody looked this name up. Two
    of them either side of an interpunct is 矢立肇・富野由悠季 and 渡辺零・駿馬京; one of them is a
    name with a character in it. `るいす・まくられん` and `ブリリアント・ブラウン` have neither and
    stay whole, which is the answer a reader needs.
    """
    rec = (store or {}).get(inputs_fold(piece)) or {}
    return bool(rec.get("romaji"))


def inputs_fold(name):
    """The key the shipped name map is under: NFKC with the spaces taken out.

    THE BROWSER'S FOLD AND NOT A SECOND ONE. `foldKey` in app.js normalises NFKC and removes every
    space, and a producer that asks a different question from the consumer's lookup is how
    `MFCキューンシリーズ` was recorded as named while nothing could find it.
    """
    import unicodedata
    return unicodedata.normalize("NFKC", str(name or "")).replace(" ", "")


def _by_interpunct(name, store):
    """`name` split on ・ where every piece is a name the store can render, else `[name]`."""
    if "・" not in name and "･" not in name:
        return [name]
    pieces = [p.strip() for p in re.split(r"[・･]", name) if p.strip()]
    if len(pieces) < 2 or not all(_is_a_name_of_its_own(p, store) for p in pieces):
        return [name]
    return pieces


# A filing key folds the kana that sort together, so a stated reading and a printed one differ by
# づ against ず and を against お without disagreeing. `openbd_reading.normalised` says the same
# thing about the same fold; here it decides whether a katakana part is the name beside it.
_FILING = str.maketrans("ヅヲヰヱ", "ズオイエ")


def _fold_kana(s):
    return kana.to_katakana(str(s or "")).translate(_FILING).replace(" ", "").replace("\u3000", "")


# Voicing marks, dropped for a comparison and never for a rendering. A catalogue prints the reading
# of 藤川よつ葉 as フジガワヨツバ and the store holds フジカワヨツバ, which is rendaku and not a
# disagreement about who the artist is. The two strings still have to be the same length and the
# same kana otherwise, so this cannot make two different names look alike.
_VOICED = str.maketrans("ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ",
                        "カキクケコサシスセソタチツテトハヒフヘホハヒフヘホウ")


def _same_reading(a, b):
    return a == b or a.translate(_VOICED) == b.translate(_VOICED)


def _readings_among(parts, store):
    """The parts that are how ANOTHER part is read, rather than people of their own.

    THE ROLES ARE THE FIRST TEST, AND THE OLD RULE DID NOT HAVE THEM. `creditNames` in kari/app.js
    dropped any second part that was katakana throughout where the first was not, on the argument
    that MADB writes one creator as `紬めめ / ツムギメメ`. It does. It also writes
    `[原作]王月よう / [漫画]アジイチ`, two people whose second name happens to be katakana, and the
    tab has been dropping アジイチ, フライ, ヨリフジ and サトウナンキ from those bylines in every
    language. A field that states a job for each half is naming contributors and says so.

    A PAIR IS THE COMMON CASE AND NOT THE ONLY ONE. The catalogue writes a two-person credit as
    `おぎしろ / みかみてれん / オギシロ / ミカミテレン`, and it does not keep the order:
    `夜の羊雲 / 東崎惟子 / アガリザキユイコ / ヨル ノ ヒツジグモ` reverses the second half. Counting
    positions cannot read either, and it cannot read `でかいるか / エリーゼ / エリーゼ / デカイルカ`
    at all, where the splitter has already folded the repeated name away and left an odd number. So
    the question is asked of each part on its own: is this the reading of one of the others.

    MATCHED AGAINST THE SURFACE FIRST AND THE STORE SECOND. A kana pen name is its own reading, so
    おぎしろ answers オギシロ with no lookup; a kanji name needs the store, where 夜の羊雲 is filed
    ヨル ノ ヒツジグモ. Both go through the filing fold, because a stated reading and a printed one
    differ by づ against ず without disagreeing.

    THE COUNTER-CASE, so this is not widened later without it: `きづきあきら / サトウナンキ` is a
    duo and looks exactly like a name beside its reading. The store settles it, since キヅキアキラ
    is not サトウナンキ, and a part matching nothing is kept. That is the direction which costs a
    reader an odd-looking row instead of a missing artist.
    """
    if any(p.get("r") for p in parts) or len(parts) < 2:
        return []
    named = [p for p in parts if p.get("n")]
    # THE PAIR WITH NOTHING TO COMPARE AGAINST, which is the rule this replaces and still the right
    # answer where the store has never met the name. `河上大志郎 / カワカミダイシロウ` states no
    # reading anywhere and is plainly one artist written twice; keeping the katakana would put a
    # second person on the row. Two parts only, because a longer field with an unknown name in it
    # is as likely to be a group as a gloss.
    if (len(named) == 2 and KATAKANA_ONLY.match(named[1]["n"])
            and not KATAKANA_ONLY.match(named[0]["n"])
            and not ((store or {}).get(inputs_fold(named[0]["n"])) or {}).get("reading")):
        return [named[1]]
    out = []
    for cand in parts:
        if not cand.get("n") or not KATAKANA_ONLY.match(cand["n"]):
            continue
        want = _fold_kana(cand["n"])
        for other in parts:
            if other is cand or not other.get("n") or KATAKANA_ONLY.match(other["n"]):
                continue
            if other in out:
                continue
            reading = ((store or {}).get(inputs_fold(other["n"])) or {}).get("reading")
            if (want == _fold_kana(other["n"])
                    or (reading and _same_reading(want, _fold_kana(reading)))):
                out.append(cand)
                break
    # NEVER ALL OF THEM. A field written entirely in katakana would otherwise empty itself.
    return out if len(out) < len([p for p in parts if p.get("n")]) else []


def divide(credit, store=None):
    """The people a credit field names, in order, each with the job the field gave them.

    `[{"n": name, "r": role or absent}, …]`, with a final `{"etc": 1}` where the field said the
    people it names are some of them. `store` is `feed/names.json`'s `authors` map; without one the
    interpunct stays inside a name, which is `inputs`' printing answer and the safe direction.
    """
    return _divide(credit, store)[0]


def _divide(credit, store):
    """`(parts, set aside)`. The second is what the division dropped ON PURPOSE.

    RETURNED RATHER THAN RECOMPUTED, because `coverage` below has to tell a reading the division
    put aside from a name it lost, and those are the same string to anything looking at the field
    afterwards. Asking the reading test a second time from `coverage` would be the same fact
    derived twice, which is the shape this whole module exists to remove.
    """
    raw = str(credit or "").strip()
    if not raw:
        return [], []
    out, aside = [], []
    for name, reading, role in inputs.split_credits_detail(raw, interpunct=False):
        said = _as_written(raw, role) if role else None
        for piece in _by_interpunct(name, store):
            out.append({"n": piece, **({"r": said} if said else {})})
        # THE READING PRINTED IN A BRACKET BESIDE THE NAME. `若（わか）` is one person and the
        # bracket is how the platform states how the kanji is said. `inputs` returns that reading
        # rather than dropping it, which is what tells us the bracket is one; the literal is
        # recovered here so the interface can take it off an English page, where kana beside a
        # romanisation says nothing to the reader it is written for.
        if reading:
            m = _BRACKETED_KANA.search(raw, raw.find(name) + len(name)) if name in raw else None
            if m and m.start() == raw.find(name) + len(name):
                aside.append(m.group(0))

    for part in _readings_among(out, store):
        aside.append(_with_separator(raw, part["n"]))
        out = [x for x in out if x is not part]

    if _says_others(raw, out):
        out.append({"etc": 1})
    return out, aside


# A bracket holding nothing but kana. `inputs._peel_bracket` decides whether one is a reading; this
# only finds the literal it decided about, so there is no second rule here.
_BRACKETED_KANA = re.compile(r"[（(][ぁ-ゖァ-ヿー\s　]+[）)]")


def _with_separator(raw, text):
    """`text` as it sits in `raw`, taking the separator in front of it too.

    A reading removed on its own leaves `紬めめ / `, a field ending in a slash, which reads as a
    credit the page failed to draw.
    """
    at = raw.find(text)
    if at < 0:
        return text
    start = at
    while start and raw[start - 1] in " \u3000/／、,，":
        start -= 1
    return raw[start:at + len(text)]


def _as_written(raw, role):
    """The role as the FIELD spells it, which is not always how the splitter reports it.

    `南瓜かぷちー(表紙/漫画)` states one role joined with a slash and the splitter normalises the
    joiner to ・ so that one compound reads one way wherever it came from. The interface finds the
    role in the field it is drawing, so it needs the spelling that is there: normalised, it found
    nothing and left `(表紙/漫画)` standing in the middle of an English credit line.
    """
    atoms = [a for a in re.split(r"[・･/／\s　]+", role) if a]
    if not atoms:
        return role
    pattern = r"[\s　・･/／]*".join(re.escape(a) for a in atoms)
    m = re.search(pattern, raw)
    return m.group(0) if m else role


def _says_others(raw, parts):
    """Whether the field closes with `ほか`, once the names it does name are taken out.

    DERIVED FROM WHAT THE DIVISION FOUND, not parsed again. Removing each name leaves the notation,
    and `ほか` inside the notation is the field saying there are more contributors than it lists.
    A pen name holding those characters is removed with the name it belongs to, so it cannot be
    mistaken for the word.
    """
    rest = raw
    for p in parts:
        if p.get("n"):
            rest = rest.replace(p["n"], "", 1)
    return bool(OTHERS.search(rest))


def coverage(credit, store=None):
    """What the division does not account for: `''` when it accounts for the whole field.

    THE MEASURE THAT STOPS A TIDY ANSWER FROM BEING A LOSSY ONE. `[[翻訳協力]][BPS株式会社]` came
    back as nothing at all from the splitter until the doubled bracket was normalised, so a company
    credited on two works would have disappeared from a byline rebuilt out of the parts, in every
    language, with no number saying so. A field this cannot account for is rendered as written by
    the interface, and `credit fields the division does not account for` counts them.
    """
    parts, aside = _divide(credit, store)
    rest = str(credit or "")
    # EVERY OCCURRENCE, LONGEST FIRST. A field writes one credit twice
    # (`ホマレ / 大鷹シン / オオタカシン / ホマレ`) and the splitter records it once, so removing one
    # occurrence leaves the other looking like a name that was lost. Longest first because a short
    # name can sit inside a longer one and removing it would cut the longer one in half.
    seen = [x for p in parts for x in (p.get("n"), p.get("r")) if x] + list(aside)

    for text in sorted(set(seen), key=len, reverse=True):
        rest = rest.replace(text, "")
    rest = OTHERS.sub("", rest)
    # A BRACKET THE SPLITTER DROPS ON PURPOSE IS ACCOUNTED FOR. `宮澤伊織(早川書房刊)` carries the
    # imprint that published the light novel, `壇九（TANJIU)` the Latin the artist also goes by and
    # `若（わか）` the reading; none of them is a second contributor, and `inputs` drops each with a
    # reason. What this is looking for is a NAME the division lost, which is why the test is what
    # survives once the notation is gone.
    rest = re.sub(r"[（(〔【\[][^）)〕】\]]*[）)〕】\]]", "", rest)
    if NOTATION.match(rest):
        return ""
    # The separators are trimmed off what is reported, so the answer names the thing the division
    # lost rather than the punctuation that was standing next to it.
    return rest.strip(" \u3000[]()（）〔〕【】/／、,，・･&＆:：")


def roles_stated(credits, store=None):
    """Every role string this corpus's credit fields state, for the gloss table to answer for."""
    seen = set()
    for c in credits or ():
        for p in divide(c, store):
            if p.get("r"):
                seen.add(p["r"])
    return sorted(seen)
