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
import argparse, datetime, pathlib, re, sys, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import yaml  # noqa: E402

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
# The Japanese names of the Latin letters. Closed set, no maintenance, and the only readings a
# single Latin character legitimately takes in running Japanese.
LETTER_NAME = {
    "A": "エー", "B": "ビー", "C": "シー", "D": "ディー", "E": "イー", "F": "エフ", "G": "ジー",
    "H": "エイチ", "I": "アイ", "J": "ジェー", "K": "ケー", "L": "エル", "M": "エム", "N": "エヌ",
    "O": "オー", "P": "ピー", "Q": "キュー", "R": "アール", "S": "エス", "T": "ティー", "U": "ユー",
    "V": "ブイ", "W": "ダブリュー", "X": "エックス", "Y": "ワイ", "Z": "ゼット",
}

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
}


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
    """A reading for one character in isolation, or None. Analyser first, Unihan after."""
    for m in modes:
        r = [t.reading_form() for t in tokenizer.tokenize(ch, m)]
        if r and r[0] and r[0] != "*" and not has_kanji(r[0]):
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


def _stands_for_itself(c):
    return unicodedata.category(c)[0] in "PZS" or c.isascii() or c in SELF_STANDING


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
    for m in tokenizer.tokenize(s, mode):
        surf = m.surface()
        r = m.reading_form()
        glue = attaches_left(m.part_of_speech()) or (out and out[-1].endswith("\x02"))
        # SURFACE FIRST. Sudachi does not decline to read a symbol — it returns キゴウ, the reading
        # of 記号, the WORD "symbol". So a space, ～, ×, ♡ or ◎ each came back as a legitimate-looking
        # kana reading and sailed past a check for empty or unreadable output: 森島 明子 became
        # "Morishima Kigō Akiko" and 100日後に×××する女社長 grew three of them. Punctuation, symbols
        # and separators pass through as themselves whatever the analyser says about them.
        if surf and all(_stands_for_itself(c) for c in surf):
            out.append(surf)
            continue
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
        out.append(("\x00" if (glue or surf == "\u30fc") else "")
                   + (_sound or READING_OVERRIDE.get(surf) or kata(r))
                   + ("\x02" if surf in PREFIX_GLUE else ""))
    # No space before closing punctuation, and none after an opening one — " , " is not spacing,
    # it is damage.
    got = ""
    for tokn in out:
        if not tokn:
            continue
        glue = tokn.startswith("\x00")
        tokn = tokn.lstrip("\x00").lstrip("\x01").rstrip("\x02")
        if not tokn:
            continue
        if got and not glue and not (tokn[0] in "、。，．！？」』）】〉》・…" or got[-1] in "「『（【〈《"):
            got += " "
        got += tokn
    got = got.strip()
    ok = got if got and not has_kanji(got) else None
    return (ok, fell_back and ok is not None) if want_flag else ok


# A credit line is not a name. 原作／宮澤伊織(早川書房刊) 作画／水野英多 went through the analyser as
# one string and came back "Gensaku Kigō Miyazawa Iori Kigō …" — it romanised the ROLE LABELS and
# read ／ as 記号, the word "symbol". An analyser will always try; the guard has to be ours.
ROLE = ("原作", "作画", "漫画", "脚本", "構成", "企画", "監修", "協力", "編集", "案", "著")
SEP = "／/・、,＆&+"


def has_japanese(s):
    return any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in s)


def is_credit_line(s):
    if len(s) > 24:
        return True                       # a name that long is a sentence about several people
    if any(c in s for c in SEP):
        return True
    return any(r in s for r in ROLE)


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
        series = json.load(open("data/build/series.json"))["series"]
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
                for _nm, _role in _split_authors()(raw):
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
                and not (kind == "authors" and is_credit_line(s))]
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
            same_as_surface = r.replace(" ", "") == s.replace(" ", "")
            rec = names.setdefault(s, {})
            if not same_as_surface:
                spans = furigana_spans(tok, s, modes[0])
                if spans:
                    rec["furigana_spans"] = spans
            rec.update({"reading": r, "reading_at": today, "reading_basis": "analyser",
                        "reading_pass": 4, "reading_source": "sudachi",
                        "reading_source_kind": "analyser",
                        # Never true. This is the labelled guess §5d permits, not a claim.
                        "verified": False})
            if uncertain or unrecognised_compound(tok, s, modes[0]):
                rec["reading_uncertain"] = True
            rec.setdefault("basis", "romaji")
            rec["note"] = ("reading guessed by a morphological analyser, not stated by any source; "
                           "analysers are weakest on pen names and coinages")
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
WRAPPED_PAT = re.compile(r"^\s*[【（(\[]\s*([^】）)\]]+?)\s*[】）)\]]\s*(.*)$")

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
    mi = re.match(r"^\s*[0-9]+\s*[.．]\s*(.+)$", n)
    if mi:
        inner = mi.group(1).strip()
        if re.match(r"^\s*(?:第\s*[0-9]+|[#＃]\s*[0-9]+)", inner):
            n = inner

    # Unwrap a bracketed label before matching. Only where the contents parse as a chapter: a
    # bracket around anything else is left alone and the name renders as it did.
    mw = WRAPPED_PAT.match(n)
    if mw:
        inner, after = mw.group(1).strip(), mw.group(2).strip()
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


def fill_missing(strings, kind, quiet=False, refresh=False):
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
    f = STORE / f"{kind}.yaml"
    if not f.exists():
        return 0
    doc = yaml.safe_load(f.read_text()) or {}
    names = doc.setdefault("names", {})
    todo = [s for s in strings
            if s and (not (names.get(s) or {}).get("reading")
                      or (refresh and (names.get(s) or {}).get("reading_basis") == "analyser"))
            and has_japanese(s) and not (kind == "authors" and is_credit_line(s))]
    if not todo:
        return 0
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    today = str(datetime.date.today())
    added = 0
    for s in todo:
        r, uncertain = analyse_best(tok, s, modes)
        if not r:
            continue
        rec = names.setdefault(s, {})
        if r.replace(" ", "") != s.replace(" ", ""):
            spans = furigana_spans(tok, s, modes[0])
            if spans:
                rec["furigana_spans"] = spans
        rec.update({"reading": r, "reading_at": today, "reading_basis": "analyser",
                    "reading_pass": 4, "reading_source": "sudachi",
                    "reading_source_kind": "analyser", "verified": False})
        if uncertain or unrecognised_compound(tok, s, modes[0]):
            rec["reading_uncertain"] = True
        rec.setdefault("basis", "romaji")
        rec["note"] = ("reading guessed by a morphological analyser, not stated by any source; "
                       "analysers are weakest on pen names and coinages")
        added += 1
    if added:
        doc["names"] = names
        f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        if not quiet:
            print(f"names filled    : {added} new {kind} read automatically (analyser, unverified)")
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


def romanise_ja(tok, modes, text):
    """Romanise a fragment — a chapter subtitle, one name out of a credit line — or return it as it
    came. Uses the same analyser and the same styles, so nothing here can disagree with a title."""
    import kana as _k
    if not text:
        return text
    if not has_japanese(text):
        return latinise(text)        # already Latin words, but maybe Japanese punctuation
    r, _unc = analyse_best(tok, text, modes)
    if not r:
        return latinise(text)       # nothing readable; at least fix the punctuation
    return latinise(_k.title_case(_k.romanise(r, "macron")))


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
    parts = []
    for fn in (chapter_en, part_marks, credit_en, romanise_ja, latinise):
        try:
            parts.append(inspect.getsource(fn))
        except (OSError, TypeError):
            parts.append(repr(fn))
    parts += [CHAPTER_PAT.pattern, EXTRA_PAT.pattern, VOLUME_PAT.pattern,
              WRAPPED_PAT.pattern,
              repr(sorted(EXTRA_EN.items())), repr(sorted(CIRCLED.items()))]
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()[:16]


def fill_chapters(names_seen, quiet=False):
    """English for chapter names and credit lines, stored beside titles and authors.

    These are the bulk of what remains Japanese on an English page — 202 chapter names against 6
    titles — and they are two different problems. A chapter name is mostly STRUCTURE (第12話) which
    translates; a credit line is a list of ROLES and NAMES, where the roles translate and the names
    are romanised. Neither is served by romanising the whole string.
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
            if is_credit_line(x):
                en = credit_en(tok, modes, x)
            else:
                # A CIRCLED DIGIT IS A PART MARKER, and NFKC flattens it into the number beside it:
                # Step.14① came out "Step.141", which reads as chapter one hundred and forty-one.
                # chapter_en converts them for its own matching and this path never did, so a name
                # it does not recognise lost the distinction entirely.
                en = romanise_ja(tok, modes, part_marks(x))
        if en and en != x:
            names[x] = en
            added += 1
    if added:
        doc["names"] = names
        f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        if not quiet:
            print(f"phrases filled  : {added} chapter names / credits rendered")
    return added


# Roles as they appear in a Japanese credit line. Translating these and romanising the names is the
# only reading that produces something an English reader can use: the alternative rendered
# 原作／宮澤伊織 as "Gensaku / Miyazawa Iori", which names a role nobody outside Japan knows.
CREDIT_ROLE = {"原作": "story", "作画": "art", "漫画": "manga", "脚本": "script", "構成": "composition",
               "企画": "concept", "監修": "supervision", "協力": "assistance", "編集": "editor",
               "キャラクター原案": "character design", "案": "concept", "著": "author"}
_ROLE_RE = re.compile("(" + "|".join(sorted(CREDIT_ROLE, key=len, reverse=True)) + ")")


def credit_en(tok, modes, s):
    """A credit line with its roles translated and its names romanised."""
    # Split into CREDITS first, then role from name inside each. Splitting on every separator at
    # once tore 原作／宮澤伊織 into two entries and printed "story, Miyazawa Iori" — a role and a
    # person listed as if they were two people.
    out = []
    for unit in re.split(r"[、,　\s]{1,}|(?<=[)）])\s*", s):
        unit = unit.strip(" 　")
        if not unit:
            continue
        m = _ROLE_RE.match(unit)
        if m:
            role = CREDIT_ROLE[m.group(1)]
            rest = unit[m.end():].strip("：:／/・ 　")
            out.append(f"{romanise_ja(tok, modes, rest)} ({role})" if rest else role)
        else:
            bits = [b for b in re.split(r"[／/・＆&+]+", unit) if b.strip()]
            out.append(", ".join(romanise_ja(tok, modes, b.strip()) for b in bits))
    # Full-width Latin is Japanese typography: Ｂ is not B to a reader of English.
    return latinise(", ".join(x for x in out if x))
