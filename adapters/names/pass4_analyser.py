#!/usr/bin/env python3
"""Best-guess readings for everything the sourced passes could not reach — labelled as guesses.

WHY THIS EXISTS. Passes 0-2 resolve a name only when a source states its reading. That is the right
bar for a claim, and it left 733 works and 461 authors with no English at all: a database where two
thirds of the rows are Japanese-only whatever the language toggle says.

NAMES-PLAN §5d is what makes this pass legitimate. An acknowledged guess is a different speech act
from an assertion — it does not misname anyone, it offers a reading and says it is a reading — so
the choice is no longer "publish a possible error or show nothing". Everything here is written
`verified: false` and the interface marks it.

WHAT IT IS NOT. A morphological analyser is not a source. UniDic and SudachiDict are trained on
running text and are weakest on exactly what this project is full of: pen names, coinages, and
titles that are wordplay. So an analyser reading is never `stated`, never overwrites a sourced
reading, and never clears the unverified flag. If pass 2 or a future pass 3 later finds a real
source, it wins and this record is replaced.

THE ASYMMETRY IS DELIBERATE (§1 vs §5c). A mis-read title is a small correctable error about a
book. A mis-read author name misnames a real person under their own work. Both are guessed here —
because the alternative is no English at all — but the author side is where the unverified mark is
doing the real work, and it must never be quietly dropped from the interface.

Licence: SudachiPy and SudachiDict-core are Apache-2.0 (§5c). KANJIDIC2 is deliberately not used.

Usage:  pass4_analyser.py [--limit N] [--dry-run]
"""
import pathlib as _pl0
import sys as _sys0

_sys0.path.insert(0, str(_pl0.Path(__file__).resolve().parents[1]))

import population as _population  # noqa: E402

import argparse, datetime, functools, pathlib, re, sys, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import yaml  # noqa: E402
import kana as _kana_tables  # noqa: E402

STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names"
KATA = {chr(c) for c in range(0x30A0, 0x3100)}


# Readings that are correct in a dictionary and wrong in ordinary use. SudachiDict gives 私 the
# formal ワタクシ, which is defensible for the lemma and simply not how the word is read in a manga
# title — 彼氏の女友達がぐいぐい来る（私に）is "watashi ni", not "watakushi ni". An analyser cannot know
# register from a title fragment, so this is the one place a small human-curated table earns its
# keep. Keyed on the exact SURFACE of a token, applied only where the analyser is guessing anyway.
#
# Keep it short and keep it justified. It is not a place to fix individual titles: anything here
# changes every work containing that token, which is the point and also the risk.
# The Japanese names of the Latin letters, which now live in kana.py because `align` needs the same
# rule and had its own answer. Re-exported so every reference to p4.LETTER_NAME still resolves.
LETTER_NAME = _kana_tables.LETTER_NAME

# PARTICLES ARE SPELLED ONE WAY AND SAID ANOTHER. は as a topic particle is pronounced wa, へ as a
# direction particle is pronounced e — and Sudachi's reading_form gives the KANA (ハ, ヘ), which is
# what is written rather than what is said. Romanising the written form produced "Ha" all over
# titles where every reader says "wa": 運命は役に立たない is "Unmei wa", not "Unmei ha".
#
# Keyed on part of speech, not on the character, so the 葉 of 葉っぱ and the interjection ハハハ are
# untouched — only a token that IS the particle is changed.
PARTICLE_SOUND = {"は": "ワ", "へ": "エ"}

READING_OVERRIDE = {
    "私": "ワタシ",
    "俺": "オレ",
    "僕": "ボク",
    # 抱く HAS TWO SENSES AND THE DICTIONARY ORDERS THEM THE WRONG WAY ROUND FOR THIS CORPUS.
    # だく is holding a person; いだく is harbouring a feeling, and is the literary form besides.
    # SudachiDict returns イダク for every inflection, so 抱かれたい女 was read イダカレタイ, which
    # is the wrong word for a title about being held, and the project owner reported it on
    # 2026-08-10. The corpus already disagreed with itself: タダでは抱かれません carries
    # ダカレマセン, back-converted from a romanisation, beside five records reading イダカレ.
    #
    # THE 未然形 ALONE, WHICH IS THE COUNTER-CASE DOING THE WORK. 抱か takes れる, せる or ない and
    # nothing else, and the passive and causative of the harbouring sense are vanishingly rare while
    # the passive of the holding sense is ordinary. Every one of the seven occurrences here is
    # 抱かれ. The citation form 抱く is deliberately NOT in this table, because 元カノに幻想を抱くな
    # is in this corpus three times and is げんそうをいだく, exactly the sense this entry is not
    # about, and a lemma-wide rule would have broken it.
    #
    # 抱い AND 抱き ARE LEFT ALONE AND THE RESIDUE IS REPORTED RATHER THAN GUESSED (NAMES-PLAN §1).
    # 「私の彼女を抱いてくれ！」と言われた実録百合漫画 is a person as the object and so is だいて,
    # and 春にして君を抱き is probably だき, but the surface says neither: 疑問を抱いて is いだいて
    # and 抱き is also the noun of 抱き枕. Settling those wants a source for each title.
    "抱か": "ダカ",
}

#: Coinages the dictionary has no entry for, whose reading belongs to the WHOLE WORD and not to its
#: characters. Keyed on the surface, matched across as many morphemes as the analyser split it into.
#:
#: WHY A SECOND TABLE AND NOT MORE ROWS IN THE FIRST. `READING_OVERRIDE` is consulted per morpheme,
#: and 陰キャ is never one: Sudachi returns 陰 as カゲ, an ordinary in-dictionary word, then キャ as
#: out-of-vocabulary. So the only key that could fix it there is 陰, and 陰 alone IS かげ: 陰で,
#: 陰口, 陰ながら. A per-morpheme entry would have to be wrong somewhere to be right here.
#:
#: THE PROJECT OWNER REPORTED IT ON 2026-08-12 as `Tsuiteru Gyaru to Mieteru Kage Kya`, from
#: ツイてるギャルとミエてる陰キャ. 陰キャ is いんキャ, clipped from 陰キャラ, 陰気なキャラクター,
#: and four other works in this corpus carry it: 陰キャ除霊師とギャルJK, 陰キャギャルでもイキがりたい！,
#: 陰キャの私が何故かギャルにモテている, and the reported one.
#:
#: ATTESTED WORDS ONLY. 陽キャ is here because the corpus states it once, in a page describing
#: 下部七花はかく語りき. Its ら forms are not, because nothing here writes them, and a table of words
#: nobody uses is a table nobody can check.
COMPOUND_READING = {
    "陰キャ": "インキャ",
    "陽キャ": "ヨウキャ",
}

#: Longest first, so a longer word wins over a shorter one that prefixes it.
COMPOUND_KEYS = sorted(COMPOUND_READING, key=len, reverse=True)

#: Alternation in length order, so the longest word that starts at a position wins: Python's `re`
#: takes the first alternative that matches, not the longest.
COMPOUND_RE = re.compile("|".join(re.escape(k) for k in COMPOUND_KEYS)) if COMPOUND_KEYS else None


def _compound_segments(s):
    """`[(text, is_compound), ...]` splitting a string on the words in `COMPOUND_READING`."""
    if not COMPOUND_RE:
        return [(s, False)]
    out, i = [], 0
    for m in COMPOUND_RE.finditer(s):
        if m.start() > i:
            out.append((s[i:m.start()], False))
        out.append((m.group(0), True))
        i = m.end()
    if i < len(s):
        out.append((s[i:], False))
    return out or [(s, False)]


def analyser_version():
    """Which analyser produced a reading, as the string stored beside it.

    AN ANALYSER HAS NO ADDRESS AND IT DOES HAVE AN IDENTITY. Every other route to a reading records
    the page it was read from, and this one recorded the word `sudachi`, which names a program and
    not the thing that decided the answer. The dictionary is what decides it: SudachiDict ships a
    dated release, entries are added and readings change between them, so two runs of identical
    code give different readings and the record could not say which release it had.

    That is the whole of what can honestly be reconstructed for these 837 readings. There is no
    document to cite because no document states them, and inventing a URL here would be worse than
    the silence it replaced.

    Falls back to the bare name where the metadata is unreadable, because a pass must not stop over
    its own bookkeeping.
    """
    import importlib.metadata as md
    parts = []
    for dist in ("SudachiPy", "SudachiDict-core"):
        try:
            parts.append(f"{dist} {md.version(dist)}")
        except Exception:                                                   # noqa: BLE001
            pass
    return ", ".join(parts) if parts else "sudachi"


# Read once. It cannot change under a running process, and a reading is stamped with it per name.
ANALYSER = analyser_version()

#: WHAT THIS PASS SAYS ABOUT A READING, AND IT GOES IN `reading_note`. It used to be assigned to
#: `note`, which is the slot that says why the ENGLISH is what it is, and it overwrote whatever was
#: already there. 196 titles held a curated English name with this sentence where its argument
#: should have been: `#We're the Strongest`, `A 14-Gram Escape` and `4:30, at the Laundromat` were
#: all translated by somebody who wrote down why, and the store said none of it.
#:
#: `adapters/names/curate.py` explains why the two fields exist apart, and it is the same reason:
#: one entry can carry two decisions, and 55 of 60 reading corrections landed on titles that
#: already had a curated translation with its own argument.
#:
#: `setdefault` RATHER THAN ASSIGNMENT. A reading somebody has already reasoned about in
#: `reading_note` outranks a sentence about SudachiDict, and this pass is the weakest voice in the
#: store: NAMES-PLAN §5d admits it precisely because it labels itself a guess.
#:
#: `facts/reading/vocabulary` quotes this sentence as the justification for the unverified mark, so
#: it is load-bearing where it belongs and was only ever misfiled.
ANALYSER_CAVEAT = ("reading guessed by a morphological analyser, not stated by any source; "
                   "analysers are weakest on pen names and coinages")


def is_kana_ch(c):
    return "\u3040" <= c <= "\u30ff"


def kata(s):
    """Readings are stored in katakana, matching every other pass."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def has_kanji(s):
    return any("\u4e00" <= c <= "\u9fff" for c in s)


_UNIHAN = None


def unihan_on(ch, prefer_kun=False):
    """On-yomi from the Unicode Han Database, or None.

    ON AND KUN MIXING IS A WARNING, NOT AN ANSWER. 濡鴉 comes out ジュ + カラス — the ON reading of
    one character beside the KUN of the next. Japanese does form such compounds (重箱読み, 湯桶読み)
    but they are the exception, so a reading assembled that way is more likely wrong than one that
    is consistently on or consistently kun. It does not tell us the right reading: 濡鴉 is probably
    ぬれがらす, a nanori reading this data does not carry at all. Everything from here is marked
    uncertain regardless, which is why that mark is doing the real work.

    THE LAST RESORT AND THE WEAKEST. SudachiDict — core and full — has no standalone entry for 濡,
    激, 痲, 犠 or 滅, so a title containing one could never be rendered at all. Unihan has all of
    them. But on-yomi is the Chinese-derived reading, and a Japanese title is usually a native word
    taking kun-yomi: 濡鴉 is almost certainly nuregarasu, not ju-a. So this is used only when
    everything else has failed, and everything built on it is marked uncertain.
    """
    global _UNIHAN
    if _UNIHAN is None:
        import json
        f = STORE / "unihan-on.json"
        _UNIHAN = json.loads(f.read_text())["readings"] if f.exists() else {}
    got = _UNIHAN.get(ch)
    if not got:
        return None
    if isinstance(got, str):                      # older single-reading file
        return got
    on, kun = (got + ["", ""])[:2]
    # TESTED AND REJECTED: preferring kun-yomi for personal names. It sounds right — names do take
    # kun far more often than on — but Unihan's kJapaneseKun is the reading of the character AS A
    # WORD, not its nanori. 採 gives トル ("to take"), so 伊藤玄採 became "Itō Gen Toru"; 阿 gives
    # クマ, so 茉離阿 became "Matsurikuma". Names use nanori readings, which this data does not
    # carry, and the verb reading is a worse guess than the on reading. The parameter is kept so
    # the rejection is visible rather than re-derived.
    return on or kun


def _kanji_adjacent(whole, token):
    """Is this token touching another kanji in the original string?"""
    i = whole.find(token)
    if i < 0:
        return False
    before = whole[i - 1] if i > 0 else ""
    after = whole[i + len(token)] if i + len(token) < len(whole) else ""
    return any("\u4e00" <= c <= "\u9fff" for c in (before, after) if c)


def per_char(tokenizer, modes, ch, prefer_kun=False):
    """A reading for one character in isolation, or None. Analyser first, Unihan after.

    THE ANALYSER SOMETIMES NAMES A CHARACTER INSTEAD OF READING IT. Asked for 々 or 彡 it answers
    `キゴウ`, which is its word for the category 補助記号 and not a sound anybody makes. That reached
    readers as `Esutorēya★Kigō` for エストレーヤ★彡 and `Ikigō Renren` for 依々恋々, a name and a
    title carrying the analyser's own vocabulary. A symbol that reads as itself is different and
    stays: ー is 補助記号 too and answers `ー`, which is the character, so it passes.
    """
    for m in modes:
        toks = list(tokenizer.tokenize(ch, m))
        r = [t.reading_form() for t in toks]
        named = r and kata(r[0]) == CATEGORY_WORD
        if r and r[0] and r[0] != "*" and not has_kanji(r[0]) and not named:
            return kata(r[0])
    return unihan_on(ch, prefer_kun)


def analyse_best(tokenizer, s, modes, prefer_kun=False):
    """Try each split mode in turn. Mode C keeps compounds whole, which reads better when it works;
    mode A is finer and sometimes reads a kanji that C gave up on, because a rare compound is not in
    the dictionary while its parts are. First success wins."""
    for m in modes:
        got, guessed = analyse(tokenizer, s, m, want_flag=True, prefer_kun=prefer_kun)
        if got:
            return got, guessed
    # Whole-string character-by-character reading, kept only for a string the tokeniser cannot
    # segment at all. Per-TOKEN fallback inside analyse() handles the ordinary case — one unreadable
    # kanji in an otherwise clean parse — and is far better, because it keeps the segmentation. — 抱き寝ーター defeats every split mode but 寝 alone is ネ. This is a genuinely worse
    # answer: a character read in isolation gives its dictionary reading, and Japanese titles
    # overwhelmingly use kun-yomi in compounds where the isolated form may be on-yomi. It is
    # returned flagged so the interface can say so, and it is all-or-nothing — a reading with a
    # hole in it is not a reading.
    out, any_kanji = [], False
    for ch in s:
        # ASCII passes through as itself. Asking a Japanese reader for the reading of "L" gets
        # リットル — litre — and of "R" gets アール, so "Fallin' Jail" came back as
        # "Fārurittorurittoruainorumaru' Jāruairittoru". A Latin word is already readable; the
        # character reader is for kanji and must never be pointed at anything else.
        if ch.isascii() or is_kana_ch(ch) or not (ch.isalnum() or "\u4e00" <= ch <= "\u9fff"):
            out.append(ch)
            continue
        r = per_char(tokenizer, modes, ch)
        if not r:
            return None, False
        any_kanji = True
        out.append(r)
    got = "".join(out).strip()
    return (got, True) if got and any_kanji and not has_kanji(got) else (None, False)


# An inflected verb is ONE word, and Sudachi hands back its morphemes: 食べ + たい, つい + て,
# なり + まし + た. Joining every morpheme with a space and capitalising each produced "Tabe Tai",
# "Tsui Te", "Nari Mashi Ta" — which is not how any of those are written in romaji.
#
# The part of speech says which pieces are not words in their own right: an auxiliary verb (助動詞),
# a conjunctive particle (接続助詞, the て of ついて), and a suffix (接尾辞) all attach to what
# precedes them. A CASE particle — の, を, は — is a separate word and keeps its space.
# Intensifier prefixes bind to the word AFTER them: 激カワ is gekikawa, one word, not "Geki
# Kawa". Sudachi tokenises 激 separately because 激カワ is slang and not in the dictionary. Small
# closed set, and each of these is a prefix in every use — none is a word standing alone.
PREFIX_GLUE = ("激", "超", "爆", "鬼", "極", "神")

ATTACHES = ("助動詞", "接尾辞")
ATTACH_SUB = ("接続助詞",)


def attaches_left(pos):
    return pos and (pos[0] in ATTACHES or (len(pos) > 1 and pos[1] in ATTACH_SUB))


# Characters that stand for themselves however they are catalogued. 〇 is U+3007 IDEOGRAPHIC NUMBER
# ZERO, category Nl, so it is a letter as far as Unicode is concerned and slips a guard written
# around punctuation, symbols and separators. Sudachi then reads 〇〇 as the numeral 零記号, and
# 限界OLと女子大生が〇〇する話 got レイキゴウ in the middle of its reading. The visually identical
# ○ (U+25CB) and ◯ (U+25EF) are So and never had the problem, which is why the same work under the
# other spelling came out right. 々 is deliberately absent: it repeats the character before it and
# is read, not passed through.
SELF_STANDING = "〇"

# THE ANALYSER'S NAME FOR A CATEGORY, WHICH IS NOT A SOUND. Sudachi answers `キゴウ` when asked to
# read 々 or 彡 alone, because its dictionary carries the category 補助記号 in the reading field.
# Matched exactly, so a name that genuinely contains these mora is untouched: 記号 as a word reads
# the same and is a real reading of real characters.
CATEGORY_WORD = "\u30ad\u30b4\u30a6"


#: Marks that take no space in front of them, in both the widths a title reaches this in. A title
#: is stored full-width and `chapter_en` folds it, so both forms occur and only one was listed.
CLOSES = "、。，．！？」』）】〉》・…" + ",.!?;:)]}\u2019\u201d"
#: Marks that take no space after them, same rule.
OPENS = "「『（【〈《" + "([{\u2018\u201c"


def _stands_for_itself(c):
    return unicodedata.category(c)[0] in "PZS" or c.isascii() or c in SELF_STANDING


def latin_reading(surface):
    """A token that is Latin, read as itself, or None where it is not Latin.

    Sudachi lowercases: it returns `jk` for `ＪＫ`, so `ＪＫすぷらっしゅ！` was stored with a reading
    of `jk ス プラッ シュ！`. A reading carries the letters a title actually contains, and the case
    is the title's rather than the analyser's. Full-width letters fold to the same letters, which is
    why `2人はS×S` was always right: its `S` was already half-width and never went through this.
    """
    folded = unicodedata.normalize("NFKC", surface or "")
    return folded if folded.isascii() and any(c.isalpha() for c in folded) else None


def _reading_kind(c, r):
    """`on`, `kun`, or None for how this reading of this character is catalogued by Unihan."""
    import kana as _k
    on, kun = (_k._unihan().get(c) or ["", ""])[:2]

    def variants(x):
        x = _k.to_katakana((x or "").strip())
        if not x:
            return set()
        out = {x}
        if len(x) > 1:
            out.add(x[:-1] + "ッ")                     # 促音便
        head = _k.RENDAKU.get(x[0])
        for v in ([head] if isinstance(head, str) else head or []):
            out.add(v + x[1:])                         # 連濁
        return out

    r = _k.to_katakana(r or "")
    if r in variants(on):
        return "on"
    if r in variants(kun):
        return "kun"
    return None


def unrecognised_compound(tokenizer, s, mode=None):
    """Did the analyser read a compound one character at a time, mixing an on and a kun reading?

    The failure `fell_back` cannot see. Sudachi only reports trouble when it has no reading at all;
    where it has no entry for a COMPOUND it quietly reads each character as its own token, and each
    reading is defensible on its own. 葬焔 came back ソウ ホノオ, an on reading beside a kun one,
    and the record carried no flag because nothing had failed.

    Both halves of the test are needed. Adjacent single-character tokens are ordinary: 100日後 is
    日 + 後 and reads ニチ ゴ correctly, and there are 43 such pairs against 4 that mix kinds. A
    Sino-Japanese compound takes on readings throughout, so a compound the analyser split AND read
    with one of each is the shape worth a person's attention. 職場 and お嬢様 are 重箱 and 湯桶
    readings and cannot be caught this way, which is correct: the analyser knows them, so they
    arrive as one token and are right.
    """
    import kana as _k
    toks = [(m.surface(), m.reading_form()) for m in tokenizer.tokenize(s, mode)]
    for (sa, ra), (sb, rb) in zip(toks, toks[1:]):
        if len(sa) == 1 and len(sb) == 1 and _k.has_kanji(sa) and _k.has_kanji(sb):
            if {_reading_kind(sa, ra), _reading_kind(sb, rb)} == {"on", "kun"}:
                return True
    return False


def analyse(tokenizer, s, mode=None, want_flag=False, prefer_kun=False):
    """A reading for the whole string, or None if any part of it comes back unreadable.

    Partial is not useful here: a title half in kana and half in raw kanji reads worse than the
    Japanese did, so it is all or nothing. Sudachi returns the SURFACE when it has no reading for a
    token rather than a marker, so `田口囁一` came back as `タグチ 囁一` and passed a naive check —
    the test that matters is whether kanji survive into the output, not whether the field is empty.

    SplitMode.C keeps named entities and compounds whole. Mode A is morphemes, which split 食べたい
    into 食べ/たい and rendered "Tabe Tai"; the coarser mode is closer to words, which is what a
    romanised title needs.
    """
    out, fell_back = [], False
    # A WORD THE DICTIONARY DOES NOT HOLD IS SPLIT OUT BEFORE THE ANALYSER SEES IT, rather than
    # matched in its output afterwards. Matching afterwards fails on 陰キャギャルでもイキがりたい！,
    # where Sudachi returns 陰 and then キャギャル: no run of whole tokens joins to 陰キャ, so a
    # lookahead over the token stream cannot find the word that is plainly there. Cutting the string
    # first also gives the rest of the title a better parse, since ギャル is then a token of its own.
    items = []
    for text, is_compound in _compound_segments(s):
        if is_compound:
            items.append(text)                      # a bare str marks a compound
        else:
            items.extend(tokenizer.tokenize(text, mode))
    for m in items:
        if isinstance(m, str):
            out.append(("\x00" if (out and out[-1].endswith("\x02")) else "") + COMPOUND_READING[m])
            continue
        surf = m.surface()
        r = m.reading_form()
        glue = attaches_left(m.part_of_speech()) or (out and out[-1].endswith("\x02"))
        # SURFACE FIRST. Sudachi does not decline to read a symbol — it returns キゴウ, the reading
        # of 記号, the WORD "symbol". So a space, ～, ×, ♡ or ◎ each came back as a legitimate-looking
        # kana reading and sailed past a check for empty or unreadable output: 森島 明子 became
        # "Morishima Kigō Akiko" and 100日後に×××する女社長 grew three of them. Punctuation, symbols
        # and separators pass through as themselves whatever the analyser says about them.
        # A MORPHEME WITH NO SURFACE HAS NOTHING TO READ. Sudachi splits `…` into three morphemes:
        # the first carries the character and a reading of `．`, and the next two carry an EMPTY
        # surface and a `．` each, which is the analyser spelling out the three dots of the one
        # character it was given. The surface-first rule below is written `if surf and …`, so the
        # two empty ones fell past it to the reading branch and each contributed a full-width dot:
        # `そして…` was read `ソシテ…．．` and romanised `Soshite.....`. 16 phrases shipped with a
        # trailing `.....` or ` . . .` where the title has an ellipsis. There is no text at a
        # zero-width span, so there is nothing for it to contribute.
        if not surf:
            continue
        if all(_stands_for_itself(c) for c in surf):
            out.append(surf)
            continue
        # LATIN IS READ AS ITSELF, and Sudachi lowercases it. `ＪＫすぷらっしゅ！` came back with a
        # reading of `jk ス プラッ シュ！`, and a reading is stored as kana with the Latin a title
        # actually contains, not with a case the analyser invented: `2人はS×S` keeps its `S` because
        # the surface was already half-width. Full-width letters fold to the same letters, so the
        # folded surface is the reading and the analyser's opinion of it is not consulted.
        r = latin_reading(surf) or r
        if not r or r == "*" or has_kanji(r):
            # PER-TOKEN, not per-string. ガイド役の天使を殴り倒したら、死霊術師になりました～激カワ…
            # parses perfectly except for ONE character: 激, which SudachiDict has no standalone
            # entry for. Failing the whole string sent all forty characters to the character-level
            # reader, which glued them together and mis-read the rest — Gaidoyakunotenshiōuritōshitara
            # — destroying a tokenisation that was almost entirely correct to salvage one kanji.
            #
            # So the fallback is applied to the token that failed and nothing else. The word before
            # it keeps the analyser's reading; 激 alone gets the per-character one.
            sub = "".join(c if c.isascii() else (per_char(tokenizer, [mode], c, prefer_kun) or "")
                          for c in surf)
            if not sub or has_kanji(sub) or len(sub) < len(surf):
                return (None, False) if want_flag else None
            # A per-character reading is a guess — see per_char. Recorded so the interface can mark
            # it, because 濡鴉 -> ジュカラス is the on-yomi of two characters read separately and is
            # very likely not how anyone says it.
            # Consecutive characters the analyser could not read are ONE word, not several:
            # 玄採 came out "Gen Sai" because Sudachi split it and each half was read alone. A
            # fallback token glues to a fallback token before it.
            # SUSPECT ONLY IF IT IS INSIDE A KANJI COMPOUND.
            #
            # A fallback character standing alone between kana, Latin or punctuation is read
            # exactly as a reader without context would read it, and Unihan's on reading is usually
            # right there: 激 in 激カワ is ゲキ, the standard intensifier, and the rendering is as
            # correct as a context-free reading can be. Warning about it is noise.
            #
            # A fallback character sitting NEXT TO another kanji is different. The two form a
            # compound whose reading is a property of the compound, not of its characters — and
            # since one half came from a dictionary and the other from the analyser, the result
            # mixes on and kun, which Japanese does only exceptionally (重箱読み, 湯桶読み). 濡鴉
            # comes out ジュ + カラス and is really ぬれがらす. That is worth a mark.
            if len(surf) > 1 or _kanji_adjacent(s, surf):
                fell_back = True
            if surf in PREFIX_GLUE:
                sub += "\x02"
            out.append(("\x00" if (glue or (out and out[-1].startswith("\x01"))) else "")
                       + "\x01" + sub)
            continue
        # ー lengthens the sound before it. Standing as its own token it rendered as a literal
        # "ー" in the middle of the romaji: 抱き寝ーター came out "Daki Ne ー Tā".
        _pos = m.part_of_speech()
        _sound = PARTICLE_SOUND.get(surf) if _pos and _pos[0] == "助詞" else None
        # THE SAME REFUSAL per_char MAKES, in the loop that reaches these two first. 々 and 彡 arrive
        # here as whole tokens carrying `キゴウ`, the analyser's word for 補助記号, so the fallback
        # below was never consulted and エストレーヤ★彡 shipped as `Esutorēya★Kigō`. A symbol whose
        # reading IS the character passes untouched, which is how ー keeps working.
        if _pos and _pos[0] == "\u88dc\u52a9\u8a18\u53f7" and kata(r) == CATEGORY_WORD:
            sub = per_char(tokenizer, [mode], surf, prefer_kun) or ""
            if not sub:
                return (None, False) if want_flag else None
            fell_back = True
            out.append("\x01" + sub)
            continue
        # A LONE SOKUON BELONGS TO THE WORD IN FRONT OF IT, the way a lone ー does. Sudachi hands
        # back the っ of あやの浮気者っ! as a morpheme of its own, so the reading was `ウワキモノ ッ!`
        # and the romaniser dropped the ッ, having no consonant to double, and left the space it had
        # been given behind: `Aya no Uwakimono !`. 14 phrases end that way. It is a mark on a
        # pronunciation and never a word.
        out.append(("\x00" if (glue or surf in ("\u30fc", "\u3063", "\u30c3")) else "")
                   + (_sound or READING_OVERRIDE.get(surf) or kata(r))
                   + ("\x02" if surf in PREFIX_GLUE else ""))
    # No space before closing punctuation, and none after an opening one — " , " is not spacing,
    # it is damage.
    #
    # THE ASCII FORMS TOO, AND THEY WERE THE ONES THAT MATTERED. The sets below were written with
    # the full-width marks alone, and `chapter_en` NFKC-folds its input before it gets here, so by
    # the time a chapter subtitle reached this loop every ！ was a `!` and matched nothing: 526 of
    # 9,018 phrases shipped with a space in front of a closing mark. `我慢しなくて…いいですか!?` came
    # out `Gaman Shinakute ... Iidesu Ka ! ?` and `シャネルが勝ったら…` came out `Kattara . . .`,
    # because NFKC had already turned the ellipsis into three separate full stops.
    got = ""
    for tokn in out:
        if not tokn:
            continue
        glue = tokn.startswith("\x00")
        tokn = tokn.lstrip("\x00").lstrip("\x01").rstrip("\x02")
        if not tokn:
            continue
        if got and not glue and not (tokn[0] in CLOSES or got[-1] in OPENS):
            got += " "
        got += tokn
    got = got.strip()
    ok = got if got and not has_kanji(got) else None
    return (ok, fell_back and ok is not None) if want_flag else ok


# A credit line is not a name. 原作／宮澤伊織(早川書房刊) 作画／水野英多 went through the analyser as
# one string and came back "Gensaku Kigō Miyazawa Iori Kigō …" — it romanised the ROLE LABELS and
# read ／ as 記号, the word "symbol". An analyser will always try; the guard has to be ours.
#
# THE ROLE VOCABULARY IS `inputs.ROLES`, NOT A THIRD COPY OF IT. This file carried eleven words of
# its own while the splitter that feeds the store knew forty, and the eleven were missing
# キャラクターデザイン, カバーイラスト, 校正, 編纂, 表紙 and ネーム. So
# はいむらきよたか(キャラクターデザイン) was not recognised as a credit line, entered the store as a
# person, and shipped in names.json romanised with the role label inside the name. Twelve records
# were in that state, and STANDING-INSTRUCTIONS §3 says the drift will happen in exactly this way.
#
# THE SINGLE-CHARACTER ROLES ARE LEFT OUT, which is the counter-case `inputs.ROLE_HEAD` already
# records from the other direction: 作, 画, 絵, 文, 著 and 編 are ordinary characters that pen names
# are built from, and a substring test on them would call 作田ハジメ a credit line.
SEP = "／/・、,＆&+"


@functools.lru_cache(maxsize=1)
def _roles():
    """The multi-character roles, from the one list that holds them (adapters/names/inputs.py).

    CACHED BECAUSE `is_credit_line` ASKS FOR EVERY CREDIT FIELD. The list cannot change inside a
    run, and resolving the import each time put 366,000 `find_spec` calls into a single
    `check.py --runtime`. The one list is still the only producer; this remembers its answer.
    """
    from names.inputs import ROLES
    return tuple(r for r in ROLES if len(r) > 1)


@functools.lru_cache(maxsize=1)
def _interpunct():
    """`(interpunct module, fold)`, imported the way `_split_authors` imports the splitter.

    CACHED FOR THE REASON `_roles` IS. `Path(__file__).resolve()` on every call was most of 699,000
    stat calls in one runtime check, and the module it returns is the same module every time.

    THE SAME IMPORT DANCE AND FOR THE SAME REASON. This file runs as a script from the repository
    root, where `adapters` is not on the path, and as an import from the suite, where the package is
    already loaded. `_roles`' plain `from names.inputs import ROLES` works only in the second case
    and this call site is reached in both. The fold comes back beside the module because it has to
    be the one `interpunct.settled` keyed its map with.
    """
    import importlib, pathlib as _pl, sys as _sys                           # noqa: PLC0415,E401
    root = str(_pl.Path(__file__).resolve().parents[1])   # noqa: E501  (cached by the decorator)
    if root not in _sys.path:
        _sys.path.insert(0, root)
    # `facts.credit.interpunct` SINCE 93469a1 MOVED IT, and this line still said `names.interpunct`.
    # The import raised, `is_credit_line` raised with it, and build.py's naming block catches
    # everything and prints one line, so the second half of the autopilot had stopped running: no
    # author reading, no division, no publisher name, and a build that said `automatic reading pass
    # skipped`. STANDING-INSTRUCTIONS §4, failing by returning a plausible sentence.
    mod = importlib.import_module("facts.credit.interpunct")
    return mod, mod.key.fold


def _bracketed_role(s):
    """Whether a bracket in this string holds nothing but a credit role.

    THE ONE CONTEXT WHERE A SINGLE CHARACTER IS UNAMBIGUOUS, and `inputs.BRACKET_ROLES` already
    states the argument: 著, 作, 画 and 編 are ordinary characters pen names are built from, so
    `_roles` leaves them out and 作田ハジメ keeps its first character. Inside a bracket the word is
    the whole content and cannot be the start of anything.

    WHAT WENT WRONG WITHOUT IT. `index[].c` reached this pass for the first time on 2026-08-09, and
    the bibliography writes a print credit as `[著]KENTO OKAYAMA`. `is_credit_line` saw a short
    string with no separator and no multi-character role, so the field entered the store as a
    person, the analyser read 著 as チョ, and `[チョ]KENTOOKAYAMA` was recorded as somebody's
    reading. Three records, caught by `readings are stored as kana`.

    A DOUBLED DELIMITER IS STILL ONE DELIMITER, and this is the third place that has had to learn
    it. MADB writes `[[著]]椿木とりか`, where the outer bracket pair encloses `[著`, which is not a
    role, so the first version of this walked past it and the field went into the store as a person
    called `[[Cho]]Tsubaki Torika`. `a person is spelled one way` caught it, against the phrase map's
    `[ [ Cho ] ] Tsubaki Tori Ka`. `inputs.split_credits_detail` and `inputs._peel_bracket` both
    normalise this at the top and neither could be asked from here, so the normalisation is repeated
    and named after the fault it prevents.

    `inputs.ROLE_ONLY` and `inputs.BRACKETED` are asked rather than copied. A second role vocabulary
    in this file is what put twelve records in the store with a role label inside the name.
    """
    from names.inputs import BRACKETED, ROLE_ONLY
    s = re.sub(r"\[+", "[", re.sub(r"\]+", "]", str(s)))
    return any(ROLE_ONLY.match(m.group(1).strip()) for m in BRACKETED.finditer(s))


def has_japanese(s):
    return any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in s)


def is_credit_line(s, ruled=None):
    """Whether this string is a list of people rather than one person's name.

    THE INTERPUNCT WAS THE WHOLE OF `SEP` THAT COULD BE WRONG, and it was wrong for 13 credit
    fields. `くろば・Ｕ` is one artist, this said the field named several, and pass 4 skips a credit
    line, so that person could never enter the store and was romanised on the mechanical floor for
    as long as the corpus has held them. `ruled` is `interpunct.settled`'s map, and a string it
    calls one person is a name here whatever the ・ in it looks like.

    NOTHING ELSE IN `SEP` IS IN QUESTION. `inputs.py` measured the ampersand across the whole corpus
    before admitting it and found four fields, all of them two people; a slash, a comma and a
    Japanese comma are punctuation nobody's pen name contains. The ・ is the one character that is
    both, which is why it is the one with a module behind it.
    """
    if len(s) > 24:
        return True                       # a name that long is a sentence about several people
    if any(r in s for r in _roles()) or _bracketed_role(s):
        return True
    if any(c in s for c in SEP if c not in "・･"):
        return True
    if "・" not in s and "･" not in s:
        return False
    ipunct, fold = _interpunct()
    # An unsettled ・ still means a credit line, so a string nobody has ruled on is treated exactly
    # as it was and the change reaches only the names the evidence settled.
    return (ruled or {}).get(fold(s)) != ipunct.ONE


def credit_fields_built(root="data/build"):
    """Every credit field the built collections carry, for the evidence an interpunct is settled on.

    THE WIDEST SET REACHABLE FROM HERE, AND ASKING FOR IT MATTERS (STANDING-INSTRUCTIONS §14c).
    This pass reads `series.json` for its own queue, and against that file alone 渡辺零・駿馬京 and
    矢立肇・富野由悠季 have no evidence either way: the source that writes each pair apart is the
    bibliography's `creator` field, on the same two works, in `works.json`. Two people would have
    been held for a human on the strength of the first file anybody opened.

    An absent file is an absent file and not an error. A pass that runs before the build has written
    one gets a smaller evidence set, so it settles less and holds more, which is the safe direction.
    """
    import json, pathlib as _pl                                             # noqa: PLC0415,E401
    out, base = [], _pl.Path(root)
    # THE STORE WHERE THE BUILD HAS NOTHING, §13. Each of these was read if present and skipped
    # otherwise, so with the corpus JSON no longer written the loop found nothing and this queue
    # silently emptied. Absence is a state, and here it is the state of having a store instead.
    _from_store = {"index.json": lambda: {"works": _population.index()},
                   "works.json": lambda: {"works": _population.records()},
                   "series.json": lambda: {"series": _population.series()},
                   "feed/current.json": lambda: {"releases": _population.feed_window()}}
    for name, rows_at, field in (("index.json", "works", "c"), ("works.json", "works", "creator"),
                                 ("series.json", "series", "author"),
                                 ("feed/current.json", "releases", "author")):
        f = base / name
        if not f.exists():
            doc = _from_store[name]()
            got = doc.get(rows_at) or []
            for r in got:
                if isinstance(r, dict) and r.get(field):
                    out.append((r.get(field), r.get("url")))
            continue
        try:
            doc = json.loads(f.read_text())
        except ValueError:
            continue
        rows = doc.get(rows_at) if isinstance(doc, dict) else doc
        for row in rows or []:
            value = (row or {}).get(field) if isinstance(row, dict) else None
            if isinstance(value, str) and value.strip():
                out.append(value.strip())
    return out


def _split_authors():
    """inputs.split_authors, imported however this file happens to be run.

    inputs.py imports kana relatively, so it loads as part of the package and not as a bare module,
    and this file is run both ways: as a script from the repository root and as an import from the
    suite.
    """
    import importlib, pathlib as _pl, sys as _sys
    root = str(_pl.Path(__file__).resolve().parents[1])
    if root not in _sys.path:
        _sys.path.insert(0, root)
    return importlib.import_module("names.inputs").split_authors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    # RE-DERIVE WHAT THIS PASS ITSELF PRODUCED. Normally it only fills in a missing reading, so a
    # fix to how it reads never reaches the records it already wrote. Only `analyser` readings are
    # refreshed: a stated or researched one outranks this pass anyway, and the store would refuse
    # the overwrite, so offering it would be noise.
    ap.add_argument("--refresh", action="store_true",
                    help="re-derive readings this pass produced, so a fix to it reaches them")
    a = ap.parse_args()
    refresh = a.refresh

    try:
        from sudachipy import Dictionary
    except ImportError:
        sys.exit("SudachiPy not installed: pip install sudachipy sudachidict-core")
    from sudachipy import SplitMode
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    today = str(datetime.date.today())

    for kind in ("titles", "authors"):
        f = STORE / f"{kind}.yaml"
        doc = yaml.safe_load(f.read_text())
        names = doc["names"]

        # Everything the pipeline has seen, not just what already has a record.
        import json
        seen = set()
        series = _population.series()
        # WHERE AN INTERPUNCT SEPARATES PEOPLE AND WHERE IT DOES NOT, settled once off the fields
        # themselves before any of them is split. `adapters/names/interpunct.py` reads the evidence
        # only from credit fields holding no ・, which is what stops the answer being read out of a
        # store this pass filled by splitting on ・ in the first place.
        _ip, _ = _interpunct()
        _whole = lambda f: [n for n, _rd in _split_authors()(f, interpunct=False)]   # noqa: E731
        _fields = credit_fields_built()
        ruled = _ip.settled(_fields, _whole, _ip.load_rulings())
        held = _ip.unruled(_fields, _whole, _ip.load_rulings())
        if kind == "authors":
            print(f"authors: {len(ruled)} interpunct credit(s) settled, "
                  f"{len(held)} waiting on a person{': ' + ', '.join(held) if held else ''}")
        for r in series:
            if kind == "titles":
                seen.add(r["work"])
            elif r.get("author"):
                # THE PEOPLE INSIDE A CREDIT LINE ARE PEOPLE. Only the whole string was added, so
                # anyone who never appears alone got no record of their own, was never researched,
                # and was romanised as part of a run the analyser mis-segmented: 柚原もけ came out
                # "Yuhara mo Ke" and 猫屋敷ぷしお "Nekoyashikipu Shio". 入間人間 has a sourced
                # reading and its credit line still said "Iruma Ningen", because the line was
                # romanised whole and never consulted it.
                raw = r["author"].strip()
                seen.add(raw)
                for _nm, _role in _split_authors()(raw, ruled=ruled):
                    if _nm and _nm.strip():
                        seen.add(_nm.strip())

        todo = [s for s in sorted(seen)
                if s and (not (names.get(s) or {}).get("reading")
                          or (refresh
                              and (names.get(s) or {}).get("reading_basis") == "analyser"))
                # A name already in Latin has nothing to read. Worse, the analyser does not
                # decline — it reads the SPACE between the words as 記号, so "Sal Jiang" came back
                # "サル キゴウ jiang". Asking a Japanese analyser to read English is our error, not
                # its failure.
                and has_japanese(s)
                and not (kind == "authors" and is_credit_line(s, ruled))]
        if a.limit:
            todo = todo[: a.limit]

        added = skipped = 0
        for s in todo:
            r, uncertain = analyse_best(tok, s, modes)
            if not r:
                skipped += 1
                continue
            # A reading identical to the surface adds nothing as FURIGANA — but it is still what the
            # romanisation is built from, and バクガタリzzZ needs "Bakugatari zzZ" as much as any
            # other title does. Skipping it conflated "useless as ruby" with "useless", and left
            # every kana-and-Latin title with no English at all.
            # THE SAME RULE AS THE OTHER WRITE SITE, and there are two: this one refills a whole
            # kind and the one below fills what a later pass named. Guarding one of them let the
            # analyser write スタジオクロマト・スタジオコロリド a second time, on the very run
            # after the guard went in, which is what a rule applied at one of two producers buys.
            if not _reading_facts().spells(s, r):
                skipped += 1
                continue
            same_as_surface = r.replace(" ", "") == s.replace(" ", "")
            rec = names.setdefault(s, {})
            if not same_as_surface:
                spans = furigana_spans(tok, s, modes[0])
                if spans:
                    rec["furigana_spans"] = spans
            rec.update({"reading": r, "reading_at": today, "reading_basis": "analyser",
                        "reading_pass": 4, "reading_source": ANALYSER,
                        "reading_source_kind": "analyser",
                        # Never true. This is the labelled guess §5d permits, not a claim.
                        "verified": False})
            if uncertain or unrecognised_compound(tok, s, modes[0]):
                rec["reading_uncertain"] = True
            rec.setdefault("basis", "romaji")
            rec.setdefault("reading_note", ANALYSER_CAVEAT)
            added += 1

        print(f"{kind}: {len(todo)} without a reading -> {added} guessed, {skipped} left alone")
        if not a.dry_run:
            doc["names"] = names
            f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))



def furigana_spans(tokenizer, s, mode=None):
    """[[text, reading-or-null], …] for a whole string, aligned per kanji run.

    Alignment is per TOKEN because that is where a reading is actually known — asking for the
    reading of a whole title and then trying to place it is the harder problem and the one that
    produces ruby over the wrong character. SudachiPy supplies the tokens and their readings; only
    the placement inside a token is ours (kana.align).

    Returns None if any token cannot be aligned, because a title with ruby over half its kanji
    looks like a bug rather than a partial answer.
    """
    import kana as _k
    out = []
    for m in tokenizer.tokenize(s, mode):
        surf = m.surface()
        r = m.reading_form()
        if not surf:
            continue
        # A Latin letter inside a Japanese word IS read aloud — V in Vチューバー is ブイ, and ruby
        # saying so is useful. What is not useful is the SI expansion: Sudachi reads M as メートル,
        # metre. So Latin keeps its reading only when that reading is the letter's NAME, which is a
        # closed set of 26 and needs no maintenance, and is otherwise passed through bare.
        if surf and len(surf) == 1 and surf.isascii() and surf.isalpha():
            nm = LETTER_NAME.get(surf.upper())
            out.append([surf, _k.to_hiragana(nm)] if nm and kata(r) == nm else [surf, None])
            continue
        # SURFACE FIRST, exactly as analyse() does — the two must agree or one string gets two
        # different readings. 怪異部～M県Y市の怪現象について～ built its romaji from analyse(), which
        # passes ASCII through, and its ruby from here, which did not: Sudachi reads M as メートル,
        # the SI symbol for metre, so the page showed "M Ken Y Shi" beside めーとる over the M.
        # Latin in a Japanese title is read as letters, and no reader needs furigana over "M".
        if all(_stands_for_itself(c) for c in surf):
            out.append([surf, None])
            continue
        if not r or r == "*" or has_kanji(r):
            return None
        # The override applies HERE too. It was applied when building the reading string and not
        # when building the ruby, so the same title read "Watashi" in romaji and showed わたくし
        # above the kanji — two renderings of one reading disagreeing on the page.
        got = _k.align(surf, READING_OVERRIDE.get(surf) or kata(r))
        if got is None:
            return None
        for text, rd in got:
            out.append([text, _k.to_hiragana(rd) if rd else None])
    # Merge neighbouring unread runs so the markup does not fragment plain text pointlessly.
    merged = []
    for text, rd in out:
        if rd is None and merged and merged[-1][1] is None:
            merged[-1][0] += text
        else:
            merged.append([text, rd])
    return merged


# 第12話, 12話, ＃15①, 第５０−２話　夢現 — a chapter name is mostly a NUMBER wearing a counter, and
# translating that structure is worth more than romanising it: "Ch. 12" reads, "Dai 12 Wa" does not.
# The subtitle after it is a title and is romanised like one.
# The number can carry a sub-part on EITHER side of the counter — 第50-2話 and 第90話-1 are both
# written, as are circled digits ①②③ used as a part marker. All of it is the number.
CIRCLED = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5", "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9"}
CHAPTER_PAT = re.compile(
    r"^\s*[#＃]?\s*(?:第\s*)?"
    r"([0-9]+(?:[-−.][0-9]+)?)"
    r"\s*(?:話|回|話目|幕|章|球|服|皿|輪|侵略|角|限|節|夜|日目|冊目|泊目|軒目)?"
    r"\s*([-.][0-9]+)?\s*(.*)$")
EXTRA_PAT = re.compile(
    r"^\s*[【（(\[]?\s*(番外編|特別編|おまけ|最終話|最終回|前編|後編|中編|完結)\s*[】）)\]]?\s*(.*)$")

# THE SAME LABEL, WRAPPED. 【第100話】心合わせて and （第18話）失敗の達人 say exactly what 第100話 心合わせて
# says, and the bracket is punctuation around it. CHAPTER_PAT anchors at the start, so a wrapper
# made it miss entirely and the whole label was romanised: "[Dai 100Wa]shin Awasete",
# "( Dai 18Wa ) Shippai no Tatsujin", "( Dai 17 Hanashi ) Doki!". 186 phrases read that way.
#
# The wrapper is unwrapped and its contents offered to the same pattern, so there is one producer
# of what a chapter label is. Where the contents are NOT a chapter the unwrapping is discarded and
# the name renders exactly as before, which is the fallback: a bracket this does not understand
# costs nothing.
# THE CLOSING BRACKET HAS TO BE THE ONE THAT OPENED. A single class of closers let the match end
# at the first bracket of any kind, so 【第132話(1)】 stopped inside its own parenthesis: the label
# came out `Ch. 132 (1` with a stray `】` after it, which reached readers as `Ch. 132 (1 ]`. Each
# pair is its own branch and its contents exclude only its OWN closer, so a nested bracket is part
# of the label it sits in.
WRAPPED_PAT = re.compile(
    r"^\s*(?:【\s*([^】]+?)\s*】|（\s*([^）]+?)\s*）|\(\s*([^)]+?)\s*\)|\[\s*([^\]]+?)\s*\])"
    r"\s*(.*)$")


# A CHAPTER NUMBERED IN KANJI IS STILL A NUMBER. `CHAPTER_PAT` wants ASCII digits, which NFKC gives
# it for ７ and not for 七, so 第七話 missed the structure branch entirely and was romanised whole as
# `Dai Nana Hanashi`: the word "chapter" spelled out in Latin as though it were the chapter's name.
# Chapter numbers are small, so this reads the everyday 1-999 forms and nothing cleverer.
_KANJI_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9}
_KANJI_UNIT = {"十": 10, "百": 100}
KANJI_NUM = re.compile(r"[〇零一二三四五六七八九十百]+")


def kanji_number(s):
    """`七` -> 7, `十二` -> 12, `二十三` -> 23, or None where it does not read as one."""
    total = cur = 0
    seen = False
    for ch in s:
        if ch in _KANJI_DIGIT:
            cur = _KANJI_DIGIT[ch]
            seen = True
        elif ch in _KANJI_UNIT:
            total += (cur or 1) * _KANJI_UNIT[ch]
            cur = 0
            seen = True
        else:
            return None
    return (total + cur) if seen else None


def digits_for_kanji(n):
    """`第七話` -> `第7話`, leaving anything that is not a counted number alone.

    ONLY BETWEEN A COUNTER AND ITS MARKER, never loose in a subtitle: 千歳 and 十七歳の hold the same
    characters and are words. The number has to be introduced by 第 or a hash and followed by one of
    the counters a chapter wears, which is what makes it structure rather than content.
    """
    def sub(m):
        v = kanji_number(m.group(2))
        return f"{m.group(1)}{v}{m.group(3)}" if v is not None else m.group(0)
    return re.sub(r"([第#＃])\s*([〇零一二三四五六七八九十百]+)\s*(話|回|話目|幕|章|夜|日目)",
                  sub, n)

# A VOLUME, WHICH IS NOT A CHAPTER. 巻 was absent from the counter list above, so ４巻 第３９話 matched
# the bare-number branch as chapter four and the real chapter fell into the subtitle and was
# romanised: "Ch. 4 Maki Dai 39Wa". Read off the front first, so what follows is judged on its own.
VOLUME_PAT = re.compile(r"^\s*([0-9]+)\s*巻\s*(.*)$")
EXTRA_EN = {"番外編": "Extra", "特別編": "Special", "おまけ": "Bonus", "最終話": "Final",
            "最終回": "Final", "前編": "Part 1", "後編": "Part 2", "中編": "Part 2", "完結": "End"}


def part_marks(s):
    """Circled digits written as a bracketed part, so NFKC cannot fold them into a neighbour."""
    out = s or ""
    for c, d in CIRCLED.items():
        out = out.replace(c, f" ({d})")
    return out.strip()


def chapter_en(name, romanise_rest):
    """An English rendering of a chapter name, or None if it is not chapter-shaped.

    `romanise_rest` renders whatever follows the number — a subtitle, which is a title and gets a
    title's treatment. Structure is translated, content is romanised: those are different jobs and
    conflating them gives "Dai 90 Wa 1 Hasshakusama Ribaibaru", which helps nobody.
    """
    if not name:
        return None
    # Circled digits are a PART marker, and NFKC turns ② into a bare "2" — so ＃15② normalised to
    # "#152" and read as chapter one hundred and fifty-two. They are converted first, to the
    # hyphenated form they mean, and only then is the rest normalised.
    n = name
    for c, d in CIRCLED.items():
        n = n.replace(c, "-" + d)
    n = unicodedata.normalize("NFKC", n).replace("\u2212", "-").replace("\uff0d", "-").strip()
    # A kanji chapter number becomes a digit before anything tries to read the structure.
    n = digits_for_kanji(n)

    # A leading volume number is taken off the front and put back at the end, so the chapter inside
    # is read as a chapter. Without this "2巻 第26話" came out "Ch. 2 Maki Dai 26Wa": the volume
    # became the chapter and the chapter became scenery. 53 names begin this way.
    vol = None
    mv = VOLUME_PAT.match(n)
    if mv:
        vol, n = mv.group(1), mv.group(2).strip()
        if not n:
            return latinise(f"Vol. {vol}")

    # A PLATFORM'S ROW INDEX IS NOT THE WORK'S CHAPTER NUMBER. コミックDAYS and マガポケ prefix their own
    # row number to the label the work uses: "100.第94話しんゆうのたのみ" is row 100 carrying chapter
    # 94. The leading integer matched first and the real label fell into the subtitle, so it read
    # "Ch. 100 . Dai 94 Hanashi Shin Yū no Ta Nomi", wrong in the number as well as the romanising.
    #
    # An explicit 第N話 or #N outranks a bare leading integer, because one is the work saying what
    # this chapter is and the other is a list saying where it sits. Where the remainder is NOT such
    # a label the prefix is left alone, which keeps "07Chapter.5" and its like as they were.
    # The prefix is index material and nothing else: digits, separators, and the words a platform
    # numbers its own rows with. "07Chapter.12第6話-2" carries both numberings and read
    # "Ch. 07 Chapter . 12 Dai 6Wa - 2". Requiring the prefix to be ONLY index material is what
    # keeps a real title safe: anything with a word in it that is not one of these is left alone.
    INDEXY = re.compile(r"^[\s0-9.．\-_#＃]*(?:(?:chapter|episode|ep|ch)[\s.．]*[0-9]*[\s.．\-_]*)*$",
                        re.I)
    mi = re.search(r"(第\s*[0-9]+|[#＃]\s*[0-9]+)", n)
    if mi and mi.start() > 0 and INDEXY.match(n[:mi.start()]):
        n = n[mi.start():].strip()

    # Unwrap a bracketed label before matching. Only where the contents parse as a chapter: a
    # bracket around anything else is left alone and the name renders as it did.
    mw = WRAPPED_PAT.match(n)
    if mw:
        inner = next(g for g in mw.groups()[:4] if g is not None).strip()
        after = (mw.group(5) or "").strip()
        if CHAPTER_PAT.match(inner) and ("話" in inner or "回" in inner
                                         or re.match(r"^\s*[#＃第]", inner)):
            n = (inner + " " + after).strip()

    m = CHAPTER_PAT.match(n)
    if m and (m.group(1) is not None) and ("話" in n or "回" in n or n.lstrip().startswith(("#", "＃"))
                                           or re.match(r"^\s*第", n)):
        num = m.group(1) + (m.group(2) or "")
        # The separator between a number and its subtitle belongs to neither. "12.普通の話"
        # left the dot at the front of the subtitle and rendered "Ch. 12 .普通の話".
        rest = re.sub(r"^[\s.．・:：、,\-−–—]+", "", (m.group(3) or "")).strip()
        tail = romanise_rest(rest) if rest else ""
        out = f"Ch. {num}" + (f" {tail}" if tail else "")
        return latinise((f"Vol. {vol}, " + out) if vol else out)
    if vol:
        # 3巻発売フェア and its like: a volume and then something that is not a chapter at all.
        tail = romanise_rest(n) if n else ""
        return latinise(f"Vol. {vol}" + (f" {tail}" if tail else ""))
    m = EXTRA_PAT.match(n)
    if m:
        rest = (m.group(2) or "").strip()
        tail = romanise_rest(rest) if rest else ""
        out = EXTRA_EN[m.group(1)] + (f" {tail}" if tail else "")
        return latinise((f"Vol. {vol}, " + out) if vol else out)
    return None


def wants_reading(s, rec, kind="authors", refresh=False):
    """Whether the autopilot still owes this string a reading. What `fill_missing` queues on.

    A KANA AUTHOR NAME CARRYING A GUESS IS OUTSTANDING WORK, not a filled slot, and that is the one
    case this adds to "has no reading at all". Everything else here is additive by design, so a
    string already holding an analyser reading is left alone unless `refresh` asks for it. A kana
    name is different in kind: pass 1 answers it exactly, for nothing, and cannot be wrong, so a
    guess in the slot is not an answer that might improve later but an error waiting to be replaced.
    181 author names were in that state, three of them read wrongly.

    THE COUNTER-CASE, AND WHY TITLES ARE NOT INCLUDED. 399 kana titles carry an analyser reading
    too, and on six of them the analyser is RIGHT where the surface is not: は is the topic particle
    in ワタシはサバサバしてただけなのに and is said wa, which is what the analyser returns and what
    Hepburn wants. A title is a sentence and a pen name is not, so the same substitution that
    rescues きみはシュガー is what wrecked はうあゆ. NAMES-PLAN §1 already keeps the two standards
    apart for this reason, and the rule follows the standard rather than the character.

    A PUBLISHER GOES WITH THE PEN NAME, on the same test. A company, a label and a self-publishing
    circle are all named rather than narrated, so a kana publisher name has no particle in it to
    get right and the surface is its reading. It is also the same population: 25 print rows name
    their own author as the publisher, so the string being asked about is frequently a pen name.
    """
    import kana as _k                                                     # noqa: PLC0415
    # A REFUTATION IS A DECISION, NOT AN EMPTY SLOT. `curate.py` removes the reading and records
    # why, and the whole content of that record is that there is nothing to put in its place: 時一二
    # is not a Japanese name and NDL deliberately holds no kana for it; 角川青羽 is a Shanghai
    # company rather than a person. The autopilot saw a name with no reading and filled it on the
    # next build, so 古川楊也 came back as フルカワ ヨウナリ and 陳巧蓉 as チン タクミ ヨウ within
    # hours of a reviewer saying neither can be read. Ten names were in that loop.
    if rec.get("reading_refuted"):
        return False
    if not rec.get("reading"):
        return True
    # OUR KANA, NOT THEIRS, WHERE THE NAME IS ALREADY KANA. `community-printed` is here for the
    # reason `openbd_reading.normalised` refuses a collation key outright: a source transcribing a
    # kana name can spell it differently from the way the artist writes it, and とりいしづく filed
    # トリイシズク is that person's name with a different kana in it. A kana surface is its own
    # reading and outranks anything typed by somebody else, so pass 1 takes it back. The owner's
    # correction of 2026-08-09 leaves that standing: a reading that does not overcome a fallback
    # basis certainly does not overcome the artist's own spelling of their own name.
    if rec.get("reading_basis") not in ("analyser", "back-converted", "community-printed"):
        return False
    return bool(refresh) or (kind in ("authors", "publishers") and _k.kana_only(s))


def reader():
    """A callable giving a reading for one name, or None where nothing can read it.

    WHAT ASKS FOR THIS. `credits.dedupe` collapses a name written beside its own reading, and it
    settles the kanji cases by looking the name up in the store. A credit line is never fed to the
    naming pass, so neither half of `田口ケンジ / タグチケンジ` was ever stored, the lookup found
    nothing, and the doubled credit shipped to a reader. Handing dedupe a reader closes that
    without putting a store write in its path or a Sudachi import in a module that must stay pure.

    Returns None where SudachiPy is absent, which callers treat as "no reader" rather than as an
    error, the same as everything else in this file.

    Cached per call, because a corpus credits the same person hundreds of times and tokenising is
    the expensive part.
    """
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return None
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    seen = {}

    def read(name):
        key = str(name or "")
        if key not in seen:
            got, _uncertain = analyse_best(tok, key, modes)
            seen[key] = got
        return seen[key]

    return read


def segment_reader():
    """A callable giving `(reading, furigana spans)` for one fragment, or None where nothing can.

    WHAT ASKS FOR THIS. `names/gloss.py` reads a title that prints a reading in brackets, and it
    reads it in pieces so the bracket answers for the run it sits after and the analyser answers
    for everything else. It needs both halves of the answer for each piece: the reading, and the
    spans the ruby is cut from, which have to be cut from the same fragment or the ruby spells
    something the reading does not say.

    Both come out of this file and neither is recomputed anywhere, which is the point. `gloss.py`
    stays pure and offline, this holds the Sudachi import, and the alignment a caller gets is the
    one `fill_missing` would have produced for the same string.

    Cached per call, and it returns None where SudachiPy is absent, the same as `reader` above.
    """
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return None
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    seen = {}

    def read(fragment):
        key = str(fragment or "")
        if key not in seen:
            got, _uncertain = analyse_best(tok, key, modes)
            seen[key] = (got, furigana_spans(tok, key, modes[0]) if got else None)
        return seen[key]

    return read


#: A stored reading the register table may take back. `stated`, `surface` and `researched` are a
#: source's kana or a reviewer's decision, and neither is the analyser's to overrule.
OVERRULABLE = ("analyser", "back-converted")


def _reading_facts():
    """`facts/reading`, imported late so this module keeps working run from its own directory."""
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from facts import reading as _r
    return _r


def overruled(tokenizer, s, reading, mode=None):
    """Whether this stored reading still holds the analyser's own answer where the table overrules it.

    The test is the presence of the UN-overridden kana in the reading, rather than a comparison with
    a fresh derivation, and the difference is what keeps this from re-reading the whole store: a
    record is stale here only because of a decision in `READING_OVERRIDE`, never because
    SudachiDict moved a token boundary since the reading was written.

    Kana-only, on purpose. 抱き reads ダキ as a noun and イダキ as the verb stem, and neither this
    nor the table it reads can tell those apart, which is why 抱き is not in the table.
    """
    held = kata(str(reading or ""))
    if not held:
        return False
    # A COMPOUND IS ANSWERED WITHOUT THE TOKENISER, because the question is about the whole word.
    # If the title states one and the stored reading does not carry the word's reading, that reading
    # was assembled from the characters and is exactly what the table exists to replace.
    for key, want in COMPOUND_READING.items():
        if key in str(s or "") and want not in held:
            return True
    for m in tokenizer.tokenize(s, mode):
        want = READING_OVERRIDE.get(m.surface())
        got = kata(m.reading_form() or "")
        if want and got and got != want and got in held:
            return True
    return False


def fill_missing(strings, kind, quiet=False, refresh=False, ruled=None):
    """Give every string a reading if one can be found. Idempotent, offline, safe to call always.

    THIS IS THE AUTOPILOT. Everything else in this directory is a pass someone runs; this is the one
    build.py calls on every build, so a title that appears overnight has an English rendering by
    morning without anyone touching it. It only ever ADDS: a name that already has a reading — from
    a source, from kana, from a previous run — is left exactly as it was.

    Returns the number added. Missing SudachiPy is not an error: the names simply are not filled and
    the interface shows Japanese, which is the documented fallback rather than a failure.
    """
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return 0
    import pass1_kana as _pass1
    f = STORE / f"{kind}.yaml"
    if not f.exists():
        return 0
    doc = yaml.safe_load(f.read_text()) or {}
    names = doc.setdefault("names", {})
    todo = [s for s in strings
            if s and wants_reading(s, names.get(s) or {}, kind, refresh)
            and has_japanese(s) and not (kind == "authors" and is_credit_line(s, ruled))]
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    # A CURATED REGISTER DECISION HAS TO REACH WHAT WAS ALREADY READ. `READING_OVERRIDE` is applied
    # while a reading is being produced, and this function only ever produces one for a record that
    # has none, so 私 was fixed for every title read after the entry was added and for no title read
    # before it. 抱かれたい女 was reported the same way: five records held イダカレタイ and the
    # entry that answers it changed none of them.
    #
    # ONLY WHERE THE STORED READING HOLDS THE ANALYSER'S OWN ANSWER for a token this table
    # overrules, which is the narrow test and not `--refresh`. Re-deriving every analyser reading
    # would take SudachiDict's drift with it: 163 of 2,663 no longer re-derive identically and four
    # are worse for it, ケイオン！ シャッフル now reading `Shuffle`. The table is ours and is the one
    # thing here known to be right, so it is the only thing allowed to invalidate a stored reading.
    # THE STORE'S KEYS AND NOT THE CALLER'S SET, because staleness is a property of a stored record
    # and not of what the pipeline happened to see this run. `抱かれたい女～JD…～` is an edition
    # title that reaches no series row, and scanning only `strings` left it reading イダカレタイ
    # beside four siblings that had been corrected.
    #
    # PRE-FILTERED ON THE SURFACE, so the tokeniser sees a handful of records rather than the whole
    # store. A token this table overrules cannot be in a reading whose title does not contain the
    # characters.
    _done = set(todo)
    stale = [s for s in names
             if s and s not in _done
             # BOTH TABLES, or a compound title never reaches the check below. Bracketed,
             # because `and` binds tighter than `or` and the flat form dropped the guards
             # either side of it. The pre-filter keeps the tokeniser off the whole store; it
             # decides nothing.
             and (any(w in s for w in READING_OVERRIDE)
                  or any(w in s for w in COMPOUND_READING))
             and (names.get(s) or {}).get("reading_basis") in OVERRULABLE
             and overruled(tok, s, (names.get(s) or {}).get("reading"), modes[0])]
    todo += stale
    if not todo:
        return 0
    today = str(datetime.date.today())
    added = surfaced = skipped_spelling = 0
    for s in todo:
        # A KANA NAME IS PASS 1's, AND PASS 1 RUNS WHEN SOMEBODY REMEMBERS. This one runs on every
        # build, so every kana name arriving after the last manual pass got an analyser reading for
        # a question with no lookup in it, and an analyser reading running text takes は as the
        # particle: はうあゆ went to the site as Wa u Ayu under the artist's own work. 181 author
        # names were in this state. The rule is pass 1's and is called rather than repeated.
        # NAMES ONLY, for the counter-case `wants_reading` records: は is the topic particle in a
        # title and is said wa, so the surface is the wrong answer there and the right one here. A
        # publisher is a name on that test, which is the same reason it is one there.
        surface = _pass1.surface_fields(s, kind) if kind in ("authors", "publishers") else None
        if surface is not None:
            rec = names.setdefault(s, {})
            # Additive only, like the rest of this function: a source that stated the reading, or
            # a reviewer who settled it, is never overwritten by the surface.
            # THE SAME LIST `wants_reading` SELECTS ON, and it has to stay the same list: a name
            # queued there and refused here is a name the pass reports as filled and leaves alone.
            if (rec.get("reading_basis") or "analyser") in ("analyser", "back-converted",
                                                            "community-printed"):
                # Named rather than reusing `f`, which is the store path this function writes back
                # to and is still live: shadowing it made the whole pass raise on save.
                for _stale in ("reading_uncertain", "note", "furigana_spans",
                               "reading_source_kind"):
                    rec.pop(_stale, None)
                # `pass` and `source` are NameStore's argument names, which it maps onto
                # reading_pass and reading_source. This writes the file directly, so it writes the
                # stored spelling and drops the two that would land beside it as strays.
                rec.update({k: v for k, v in surface.items() if k not in ("pass", "source")},
                           reading_at=today, reading_pass=1, reading_source="surface",
                           verified=True)
                added += 1
                surfaced += 1
            continue
        r, uncertain = analyse_best(tok, s, modes)
        if not r:
            continue
        # A KANA NAME'S READING MUST SPELL IT, and the analyser does not know that. It read
        # `スタジオクロマト・スタジオコロリド` as `スタジオクロマト スタジオコロリド`, turning the
        # interpunct into a space, and the reading stopped spelling the name. `a kana name's
        # reading spells it` caught it after the fact and blocked a gate; nothing had stopped it
        # being written. One rule, in `facts/reading`, asked here before writing and there after.
        if not _reading_facts().spells(s, r):
            skipped_spelling += 1
            continue
        rec = names.setdefault(s, {})
        if r.replace(" ", "") != s.replace(" ", ""):
            spans = furigana_spans(tok, s, modes[0])
            if spans:
                rec["furigana_spans"] = spans
        rec.update({"reading": r, "reading_at": today, "reading_basis": "analyser",
                    "reading_pass": 4, "reading_source": ANALYSER,
                    "reading_source_kind": "analyser", "verified": False})
        if uncertain or unrecognised_compound(tok, s, modes[0]):
            rec["reading_uncertain"] = True
        rec.setdefault("basis", "romaji")
        rec.setdefault("reading_note", ANALYSER_CAVEAT)
        added += 1
    if added:
        doc["names"] = names
        f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        if not quiet:
            # COUNTED APART BECAUSE THEY ARE DIFFERENT CLAIMS. A surface reading is exact and needs
            # no marking; an analyser's is a guess and the interface marks it. One number covering
            # both would have reported the 181 corrections as 181 more guesses.
            print(f"names filled    : {added - surfaced} new {kind} read automatically "
                  f"(analyser, unverified), {surfaced} answered by their own kana (surface)"
                  # SAID EVERY RUN AND NOT ONLY WHEN IT FIRES. A reading refused for not spelling
                  # its own name is the analyser meeting a name it cannot read, which is worth
                  # seeing; a number that appears only on a bad day is a number nobody recognises.
                  + f", {skipped_spelling} refused for not spelling their own name")
    return added

if __name__ == "__main__":
    main()


# Full-width punctuation is Japanese typography, not content: 【】！？　・ read as Japanese on an
# English page even when every letter around them is Latin. NFKC handles most, but not the marks it
# considers distinct characters rather than compatibility forms.
PUNCT_MAP = {"　": " ", "、": ",", "。": ".", "・": " · ", "～": "~", "〜": "~", "―": "—", "ー": "-",
             "【": "[", "】": "]", "《": "<", "》": ">", "「": "\u201c", "」": "\u201d",
             "『": "\u201c", "』": "\u201d", "〈": "<", "〉": ">", "×": "x", "｜": "|", "／": "/"}


def latinise(text):
    """Punctuation an English reader can read, without touching letters."""
    if not text:
        return text
    out = unicodedata.normalize("NFKC", text)
    for a, b in PUNCT_MAP.items():
        out = out.replace(a, b)
    return re.sub(r"\s{2,}", " ", out).strip()


def _misread():
    """`facts.reading.misread`, imported late for the reason `_roles` is: this module is imported
    by passes that do not have `adapters` on the path until they add it."""
    from facts import reading
    return reading


def _romanisation_facts():
    """`facts/romanisation`, imported late so this module runs from its own directory."""
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from facts import romanisation as _r
    return _r


def romanise_ja(tok, modes, text):
    """Romanise a fragment, a chapter subtitle or one name out of a credit line, or return it as it
    came.

    THROUGH `facts/romanisation`, WHICH IS WHERE THE RULE IS, READER-PLAN item 7. This called
    `title_case` directly and left `particles` off, while a title passes it on, so a chapter label
    capitalised the particles a title lowercases: `Koe Ni Nosete Fanfaare` on the same tab as
    `Uesugi Kun wa Onnanoko o Yametai`, and on one feed row the same phrase appeared twice spelled
    two ways. 41 rows were in that state.

    THE DOCSTRING SAID THE OPPOSITE and had done since it was written: "the same styles, so nothing
    here can disagree with a title". The claim was true of the style and false of the casing, which
    is the shape a second implementation always takes."""
    import kana as _k
    if not text:
        return text
    if not has_japanese(text):
        return latinise(text)        # already Latin words, but maybe Japanese punctuation
    # A WORD THE ANALYSER READS CONFIDENTLY AND WRONGLY. `facts/reading/misread` holds the ones a
    # source states differently; every test of the analyser's confidence passes on these, which is
    # why they need a table rather than a mark.
    text = _misread().corrected(text)
    r, _unc = analyse_best(tok, text, modes)
    if not r:
        return latinise(text)       # nothing readable; at least fix the punctuation
    return latinise(_romanisation_facts().romanise(r, "macron"))


def renderer_fingerprint():
    """What the chapter and credit renderer currently is, as a short hash.

    THE CACHE HAD NO INVALIDATION. phrases.yaml is written once per string and every entry in it is
    derived, so a fix to how a string is rendered never reached the strings already rendered. That
    cost three separate faults in one day: a name stayed "Ōkumara Suko" after its reading was
    sourced, a credit line stayed "Iruma Ningen" while the person in it was right, and a chapter
    stayed "Ch. 4 Maki Dai 39Wa" after 巻 was understood. Each fix was correct and invisible, and
    each time the file had to be emptied by hand for it to land.

    Hashing the renderer means the file invalidates itself: change how a string is rendered and
    every string is rendered again, without anyone remembering to. The alternative is a version
    number somebody has to bump, which is the same bug one level up.
    """
    import hashlib
    import inspect
    parts = [repr(CLOSES), repr(OPENS)]
    # `is_credit_line` IS IN HERE BECAUSE IT PICKS THE RENDERER, and leaving it out was the gap that
    # let `Jei, Katō` stand after the interpunct rule said ジェイ・加藤 is one person. It decides
    # between writing no phrase at all and `romanise_ja` for every string in the map, so a change to
    # it makes every entry stale exactly as a change to either of those does.
    # `analyse` AND `analyse_best` ARE IN HERE BECAUSE THEY ARE THE RENDERER. Everything above
    # delegates the actual reading to them, and neither was hashed: gluing a lone sokuon to the
    # word in front of it changed 14 phrases and the file went on serving the old ones, which is
    # precisely the invisible-fix this function exists to prevent. The failure is the same shape as
    # `is_credit_line`'s and was found the same way, by a fix landing and nothing moving.
    #
    # `CLOSES` AND `OPENS` ARE DATA THE RENDERER READS, and a table is as much of the renderer as
    # the code that consults it: adding the ASCII marks to them changed 500 phrases.
    for fn in (chapter_en, part_marks, credit_line_phrase, romanise_ja, latinise,
               is_credit_line,
               analyse, analyse_best):
        try:
            parts.append(inspect.getsource(fn))
        except (OSError, TypeError):
            parts.append(repr(fn))
    parts += [CHAPTER_PAT.pattern, EXTRA_PAT.pattern, VOLUME_PAT.pattern,
              WRAPPED_PAT.pattern,
              repr(sorted(EXTRA_EN.items())), repr(sorted(CIRCLED.items()))]
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()[:16]


def fill_chapters(names_seen, quiet=False, ruled=None, credits=True):
    """English for chapter names and credit lines, stored beside titles and authors.

    These are the bulk of what remains Japanese on an English page — 202 chapter names against 6
    titles — and they are two different problems. A chapter name is mostly STRUCTURE (第12話) which
    translates; a credit line is a list of ROLES and NAMES, where the roles translate and the names
    are romanised. Neither is served by romanising the whole string.

    `ruled` REACHES HERE TOO, AND FORGETTING IT UNDID THE WHOLE OF THE INTERPUNCT FIX. The phrase map
    answers before anything else in `kari/app.js`, so `ジェイ・加藤` went on rendering `Jei, Katō` off
    a phrase written the last time `is_credit_line` said the field named two people, with the store
    record and the shipped division both saying one. Two producers of one fact and the older one
    wins the lookup (STANDING-INSTRUCTIONS §3).
    """
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return 0
    f = STORE / "phrases.yaml"
    doc = yaml.safe_load(f.read_text()) if f.exists() else {}
    doc.setdefault("note", "Chapter names and credit lines rendered for the English view. Structure "
                           "is translated (第12話 -> Ch. 12, 原作 -> story); names are romanised.")
    names = doc.setdefault("names", {})
    # EVERY ENTRY HERE IS DERIVED, so when the renderer changes they are all stale. Dropped rather
    # than patched: nothing can say which of them a given change touches, and re-deriving is cheap
    # beside shipping a wrong one. This is the invalidation the cache never had.
    fp = renderer_fingerprint()
    carried = ()
    if doc.get("renderer") != fp:
        # RE-RENDERED, NOT DISCARDED. The file accumulates across runs and holds strings this build
        # is not looking at, from an archived month or a work that has since moved; emptying it
        # dropped 第３６話　うさぎの国の乙女 and left it rendering as Japanese on an English page.
        # The keys go back into the queue so everything is redone and nothing is lost, which is the
        # same rule the source writers learned: a pass must not delete what it is not looking at.
        carried = tuple(names)
        names.clear()
        doc["renderer"] = fp
        if not quiet and carried:
            print(f"  chapter renderer changed; re-rendering {len(carried)} phrase(s)")
    # Also strings that are only Japanese PUNCTUATION — IDOL×IDOL STORY！ has no kana or kanji and
    # still reads as Japanese typography on an English page.
    todo = [x for x in set(names_seen) | set(carried)
            if x and x not in names and (has_japanese(x) or latinise(x) != x)]
    if not todo:
        return 0
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    added = 0
    for x in todo:
        en = chapter_en(x, lambda t: romanise_ja(tok, modes, t))
        if en is None:
            # `credits=False` SAYS THE CALLER KNOWS THESE ARE NOT CREDIT FIELDS, and the guess below
            # is only worth making where they might be. `is_credit_line` answers True for
            # `Walking the Underground - 地底をゆく` and for `2019年1月号増刊(2018年12月20日発売)`,
            # which are a volume's designation and a magazine's issue: 158 of them got no phrase at
            # all and floored, because the skip that protects a real credit field from being
            # romanised as one run was applied to strings that are not credit fields.
            if credits and is_credit_line(x, ruled):
                # A CREDIT FIELD GETS NO PHRASE. The map held one romanisation of the whole field,
                # roles and all, written once and never revisited; the interface composes the line
                # from the shipped division instead, so the names follow the store and the roles
                # follow the one gloss table. Skipping rather than falling through to `romanise_ja`
                # is deliberate: that would spell `[著]中村明日美子` as one run, which is the fault
                # in its worst form rather than a fallback.
                if not credit_line_phrase(x):
                    continue
            else:
                # A CIRCLED DIGIT IS A PART MARKER, and NFKC flattens it into the number beside it:
                # Step.14① came out "Step.141", which reads as chapter one hundred and forty-one.
                # chapter_en converts them for its own matching and this path never did, so a name
                # it does not recognise lost the distinction entirely.
                en = romanise_ja(tok, modes, part_marks(x))
        # A RENDERING THAT IS STILL JAPANESE IS NOT A RENDERING, and the map must not hold one.
        # `kari/app.js`'s `phraseHeld` already refuses an answer carrying kana or kanji, so an
        # entry like that is a row the interface ignores and `kana left in a romanisation` counts.
        # `于是秘封由此开始。2 … そして秘封へと至る。2 …-中国語翻訳版` is a Chinese edition of a
        # Japanese work whose title holds both, and the analyser handed back the same string with
        # its full stops narrowed, which passed `en != x` and nothing else.
        if en and en != x and not has_japanese(en):
            names[x] = en
            added += 1
    if added:
        doc["names"] = names
        f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        if not quiet:
            print(f"phrases filled  : {added} chapter names / credits rendered")
    return added


# `CREDIT_ROLE` AND `credit_en` STOOD HERE AND ARE GONE. They were a second role vocabulary: twelve
# words with English against the 45 the splitter recognises and the 47 the interface glosses, and
# `_ROLE_RE` matched with `.match()`, anchored at the start of a unit, so a role in a leading bracket
# or a trailing paren never matched at all. 258 bracketed and 120 trailing credits therefore had the
# whole field romanised as one run, and a reader met `[Cho]Nakamura Asumiko` and `Kabocha(Cho)`,
# which name a job in a language nobody outside Japan reads.
#
# The credit line is composed in the interface now, from the division `creditline.py` ships and the
# one gloss table in `kari/src/10-names.js`, so a role is glossed where a name is rendered and the
# analyser writes no phrase for a credit field at all. `credit_line_phrase` below is what says so.


def credit_line_phrase(_s):
    """Whether the phrase map may hold a rendering of this credit field. It may not.

    A PHRASE IS WRITTEN ONCE PER STRING AND NEVER REVISITED, which is the whole reason this is a
    function rather than a deleted branch. The map fixed one rendering of the whole field, so it
    romanised the roles along with the names and no later correction could reach either. Composing
    from the division reads the store on every render instead, so a reading sourced tomorrow reaches
    the byline tomorrow.

    Returning False here rather than dropping the call keeps the decision visible in
    `renderer_fingerprint`, so the day somebody makes it True again every phrase already written is
    re-rendered rather than quietly kept.
    """
    return False
