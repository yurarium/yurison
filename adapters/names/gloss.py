#!/usr/bin/env python3
"""A reading printed inside a title, and the two facts it states.

WHAT A READING GLOSS IS. A Japanese title sometimes prints how a word in it is said, in brackets,
straight after the word: `恋する小惑星（アステロイド）`. The work is 恋する小惑星 and アステロイド
is how 小惑星 is read there, so the brackets are furigana set down on the line because a title has
no ruby. Stored whole, the string states neither fact correctly. It is not the work's name, so a
cleaner source writing the plain form opens a second row for one work, and it is not read as
written, so an analyser takes the bracketed kana for words of their own and reports a title several
syllables longer than anybody says.

So one string carries two facts and this module separates them. `plain` is the name; `compose` is
the reading, with the gloss standing for the run it follows and the analyser reading the rest.

THE GLOSS BINDS TO THE RUN IT FOLLOWS AND TO NOTHING ELSE. This is the whole of the rule and it has
already been got wrong here. `結婚(らぶらぶ)したい竜宮さんは上陸しました` glosses 結婚 as ラブラブ
and says nothing whatever about 竜宮, which is リュウグウ, the undersea palace of the 浦島太郎 tale
that the work's own synopsis is about. The national bibliography's yomi for that record reads
タツノミヤ, a surname, and a round of ours recorded the same value as a case of the gloss correcting
the name beside it. It corrected 結婚. `竜宮城へようこそ` shows the same wrong split on a work with
no gloss anywhere near it, which is what identifies the culprit as the analyser cutting 竜|宮城.
`compose` therefore reads the title in pieces, and the piece a gloss covers is exactly the kanji run
written before the bracket.

ROUND BRACKETS ONLY. `【】` marks a format or an edition in this corpus, never a reading:
`リリーズ【タテスク】` is the vertical-scroll edition and `超深宇宙より愛をこめて【読み切り版】` is a
one-shot beside its own serialisation. Every title of that shape here happens to put a kana letter
before the bracket, so a rule reading any bracket would survive today and would strip the format
marker off the first such title that ends in a kanji.

WHITESPACE IS ALLOWED BEFORE THE BRACKET, on two rows that need it: `監獄街 (プリズンタウン)
へようこそ!` and the national bibliography's `恋する小惑星 (アステロイド)`, which is the same work
COMIC FUZ writes without the space. Nothing in this corpus puts a space, a kanji and a bracketed
kana run together for any other reason.

THE SOURCE RECORD KEEPS THE GLOSS (REQUIREMENTS §5). `data/source/` holds what the catalogue said,
and `adapters/bwingest.strip_imprint` deliberately leaves `白き乙女の人狼（ウェアウルフ）` intact
because the bracket is not the shop's edition label. The separation happens on the way to the
reader, in `build.work_alias`, which both the web path and the print path reach.

WHAT THIS REPLACED. `data/work-aliases.yaml` carried `念願の悪役令嬢(ラスボス)の身体を手に入れたぞ!`
as a curated alias of the plain form, because マガポケ prints the gloss and コミックDAYS does not and
one work stood as two rows of 111 and 87 chapters. That entry was the whole of this class, decided
one title at a time; the rule reaches all of them and the entry is gone.

RULES CONSIDERED AND NOT TAKEN.

  Reading the plain title whole and splicing the gloss into its furigana spans. It needs the
  spliced span to line up with a run the aligner happened to cut at the same place, and it hands
  the analyser the string with the glossed word still in it, which is the input whose reading the
  gloss exists to overrule. Reading in pieces gives the same answer for every fragment outside the
  gloss on all thirteen titles in this corpus, measured before this was written.

  A Latin head. `SHWD(シュード)` is a gloss by every argument above and is left alone, because a
  bracketed kana run after Latin is also how this corpus writes a platform name and an imprint,
  and the two cannot be told apart in the string.
"""
import pathlib
import re

from . import kana

# The kanji run a gloss can cover, the bracket, and what may be inside it. `・` is deliberately
# outside the kana class: `（トワ・エ・モア）` is a list of names and not one word's reading.
KANJI = r"[一-鿿々]"
KANA_RUN = r"[ぁ-ゖゝゞァ-ヺーヽヾ]"
GLOSS = re.compile(r"(%s+)(\s?)[（(](%s+)[）)]" % (KANJI, KANA_RUN))

# Kana-only bracket contents that name a format or an edition. Neither has yet appeared in round
# brackets in this corpus, where both are written inside `【】`, and both would be taken as a
# reading by everything above the moment one did. `コミック` is attested twice as a bracketed
# format label (`あなたの未来を許さない（コミック）`), and `タテスク` labels five works.
NOT_A_READING = {"コミック", "タテスク", "ヨコスク"}


def _is_reading(inner):
    """Whether what a bracket holds says how the words before it are read."""
    return kana.to_katakana(str(inner or "")) not in NOT_A_READING


def parts(title):
    """A title split into `("text", s)` and `("gloss", kanji run, katakana)` pieces, in order.

    ONE TRAVERSAL FOR BOTH FACTS. The name and the reading are the same split read two ways, and
    deriving them separately is the shape STANDING-INSTRUCTIONS §3 counts seven shipped bugs from.

    WHERE THE SPACING GOES. `監獄街 (プリズンタウン) へようこそ!` sets the bracket off with a space
    on each side, so taking the bracket and its left-hand space alone leaves 監獄街 へようこそ! with
    a space nobody wrote. One space on the right goes with it, and only when the left one was
    there: `抱かれたい女(ひと) : JDだけど…` is not spaced on the left, and eating the space on the
    right would run the work's name into the ISBD mark that separates its subtitle.
    """
    s = str(title or "")
    out, last = [], 0
    for m in GLOSS.finditer(s):
        if not _is_reading(m.group(3)) or m.start() < last:
            continue
        out.append(("text", s[last:m.start()]))
        out.append(("gloss", m.group(1), kana.to_katakana(m.group(3))))
        last = m.end()
        if m.group(2) and last < len(s) and s[last].isspace():
            last += 1
    out.append(("text", s[last:]))
    return out


def glosses(title):
    """`[(kanji run, the katakana it is glossed with)]`, in the order the title writes them."""
    return [(p[1], p[2]) for p in parts(title) if p[0] == "gloss"]


def plain(title):
    """The work's name: the title with every reading gloss taken out of it.

    Everything else is copied through untouched, including a subtitle, an edition statement and
    whatever else the catalogue's punctuation marked. `adapters/isbd.py` answers those and this
    answers one question only.
    """
    return "".join(p[1] for p in parts(title)).strip()


def _covers(spans, surface):
    """Whether a span set's base text reconstructs the fragment it was cut from.

    The same arithmetic `check.py`'s `ruby covers its surface` does on the finished row, asked here
    so a set that does not add up is dropped instead of being carried to a reader. A fragment whose
    analyser gave no spans at all is the ordinary case for a run of kana and is not a fault; it
    simply means this title gets a reading and no ruby.
    """
    if not spans:
        return False
    return "".join(str((s or [""])[0] or "") for s in spans) == surface


def compose(title, read):
    """`(reading, furigana spans)` for the plain form of a glossed title, or `(None, None)`.

    `read` is a callable taking one fragment of plain Japanese and returning
    `(reading, furigana spans)` for it. `pass4_analyser.segment_reader` supplies one; a test
    supplies its own, which is what keeps this module offline.

    THE FRAGMENTS ARE READ SEPARATELY BECAUSE THAT IS THE RULE. A gloss states the reading of the
    run written before it, so that run is answered by the gloss and never sent to the analyser, and
    everything else is answered by the analyser and never by the gloss. See the module docstring
    for the title that was read wrong in the other direction.

    Spans come back only where every fragment produced a set that reconstructs it. Where one did
    not, the reading stands on its own and the title carries no ruby, which is what the interface
    already falls back to for anything the aligner cannot cover.
    """
    pieces = parts(title)
    if not any(p[0] == "gloss" for p in pieces):
        return None, None
    reading, ruby = [], []
    for piece in pieces:
        if piece[0] == "gloss":
            reading.append(piece[2])
            if ruby is not None:
                ruby.append([piece[1], kana.to_hiragana(piece[2])])
            continue
        text = piece[1]
        if not text:
            continue
        got, spans = read(text)
        if not got:
            return None, None
        reading.append(got)
        if ruby is not None:
            # COPIED, BECAUSE THE READER CACHES. `pass4_analyser.segment_reader` answers the same
            # fragment with the same list object, so two titles sharing ` : お` shared one span and
            # yaml.safe_dump wrote the store full of `&id001` anchors pointing records at each
            # other's ruby. A span belongs to the record it is stored on.
            ruby = ruby + [list(x) for x in spans] if _covers(spans, text) else None
    return re.sub(r"\s+", " ", " ".join(reading)).strip(), ruby or None


# A reading a stated gloss may replace. Machine work, all of it: the analyser's guess is what the
# gloss exists to overrule, and the other three are derivations from a string somebody else read.
# `surface` and `researched` are left exactly as they are, so a reviewer's decision and a name's own
# kana both outlive this pass whatever they say.
#
# `title-furigana` IS THIS PASS'S OWN OUTPUT AND IT IS ADMITTED FOR THAT REASON. A composed reading
# is the gloss for the glossed run and the ANALYSER for everything else, so it goes stale exactly
# when the analyser does: 抱かれたい女(ひと) was composed イダカレタイ ヒト, the ひと came from the
# publisher and the イダカレタイ came from SudachiDict, and a register correction to the second half
# could not reach a record filed under `stated`. One producer owns what it wrote (§3), and a
# `stated` reading from anywhere else is still untouchable below.
REPLACEABLE = ("analyser", "aligned", "back-converted", "guessed")
OURS = "title-furigana"

STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "titles.yaml"


def fill(names, glossed, read, today):
    """Record what each glossed title says about its own reading. `(written, disagreed, left)`.

    `glossed` maps a plain title to the string a source wrote it as, which is the only place the
    gloss survives: `build.work_alias` takes it out on the way in and hands the pair over here.

    ADDITIVE, AND IT NEVER ARGUES WITH A PERSON. A record already holding a reading somebody stated
    or settled is compared and not written. Where that reading disagrees with the gloss the record
    stands and the disagreement is counted, because two answers to one question is a thing to look
    at rather than a thing for a build to decide at four in the morning.
    """
    written, disagreed, left = {}, [], 0
    for title, source_form in sorted((glossed or {}).items()):
        reading, spans = compose(source_form, read)
        if not reading:
            left += 1
            continue
        rec = (names or {}).get(title) or {}
        held, basis = rec.get("reading"), rec.get("reading_basis")
        if held and basis not in REPLACEABLE and rec.get("reading_source") != OURS:
            if not _same(held, reading):
                disagreed.append((title, held, reading))
            continue
        if held and _same(held, reading):
            left += 1
            continue
        rec = names.setdefault(title, {})
        for stale in ("reading_conflicts", "reading_uncertain", "furigana_spans", "note"):
            rec.pop(stale, None)
        rec.update({
            "reading": reading,
            "reading_basis": "stated",
            # WHERE THE KANA WERE PRINTED, which is inside the title itself. There is no separate
            # page to cite and `provenance.SELF_SOURCED` is where that is recorded, next to the
            # kana surface, which owes no document for the same reason: the string states it.
            "reading_source": "title-furigana",
            "reading_at": today,
            "reading_note": f"the source writes this title {source_form}, "
                            f"which prints the reading of the run before each bracket",
            "verified": True,
        })
        if spans:
            rec["furigana_spans"] = spans
        # WHAT THE ENGLISH IS DERIVED FROM IS A SEPARATE QUESTION and pass 1 leaves it open for a
        # title on purpose. A record with a reading and no answer to it renders nothing at all,
        # so the default `pass4_analyser` uses for the same situation is used here.
        rec.setdefault("basis", "romaji")
        written[title] = reading
    return written, disagreed, left


def _same(a, b):
    """Two readings agreeing except about where the word boundary falls. `store.same_reading`."""
    return str(a).replace(" ", "").replace("　", "") == str(b).replace(" ", "").replace("　", "")


def self_glossed(names):
    """`{key: key}` for every stored record whose OWN key prints a reading gloss.

    THE HALF THE PIPELINE WAS MISSING. `build.work_alias` takes a gloss out of a title on the way in
    and `glossed_titles` hands the pair over, so the PLAIN name is answered by its own brackets. The
    glossed string also enters the store in its own right, off the bibliographic records, and those
    keys were read by the analyser with the brackets still in them: 恋する小惑星 (アステロイド) was
    stored コイ スル ショウワクセイ ( アステロイド ), which is the title's characters plus its own
    furigana said aloud as a second word. 永久（とこしえ） was read エイキュウ, which is the reading
    the gloss exists to overrule, and 抱かれたい女(ひと) was read オンナ where the publisher printed
    ひと. 17 keys carry a gloss and 9 of them were read past it.

    The record is its own source, which is why the key is both halves of the pair: there is no
    plainer form to attribute it to, and `provenance.SELF_SOURCED` already covers a reading the
    string itself states.
    """
    return {k: k for k in (names or {}) if glosses(k)}


def fill_store(glossed, read, path=None, today=None):
    """`fill`, against the store on disk. `(written, disagreed, left)`, and the file is written.

    THE AUTOPILOT CALLS THIS, ahead of the analyser, so a title arriving overnight with its reading
    printed in it is read the way it is printed instead of the way it is spelled. It writes the
    YAML directly, as `boundary.fill_store` and `pass4_analyser.fill_missing` do, because all three
    run inside a build that has not opened a NameStore.

    A missing store is the documented fallback and not an error.
    """
    import datetime

    import yaml
    path = pathlib.Path(path or STORE)
    if not path.exists() or not read:
        return {}, [], 0
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.setdefault("names", {})
    # THE BUILD'S PAIRS AND THE STORE'S OWN KEYS, in one call, because they are one rule asked of
    # two populations. A caller passing nothing still gets the store's own, so a run that ingested
    # no glossed title does not leave the glossed keys already on disk unread.
    glossed = dict(self_glossed(names), **(glossed or {}))
    written, disagreed, left = fill(names, glossed, read, today or str(datetime.date.today()))
    if written:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
    return written, disagreed, left
