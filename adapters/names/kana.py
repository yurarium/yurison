import re
import unicodedata

#!/usr/bin/env python3
"""Kana as the stored form of a reading, and the three romanisation styles derived from it.

WHY THIS IS A MODULE AND NOT A CALL TO cutlet. NAMES-PLAN §8.1 decides that the romanisation style
— Yūri / Yuuri / Yuri — is a reader preference, not a build-time constant. That decision only
survives if the DATA stores something all three styles can be generated from, and the only such
form is the kana itself: ゆうり yields all three, while the string "Yuri" yields none of the others
and cannot even tell you whether it was ゆり or ゆうり. So the rule is store the reading, render the
style, and this module is the renderer.

cutlet is MIT and would have done Hepburn for us, but its own documentation lists macrons under
things it does not do — so it could only ever have produced one of the three styles. Since we must
own the other two anyway, owning all three costs one table and removes a dependency. §5c reached
the same conclusion from the other direction.

WHICH HEPBURN. Modified (revised) Hepburn, the library standard:

  - ん is always `n`, never `m` before b/p/m. Nanbu, not Nambu. Real people spell themselves both
    ways, but a stated preference is recorded per-name in the store (basis `stated`) and overrides
    anything here, so the mechanical fallback only has to be consistent and conventional.
  - ん before a vowel or y takes an apostrophe: しんいち → Shin'ichi, which is the whole reason the
    rule exists — without it Shinichi reads as し-に-ち.
  - っ doubles the following consonant, except before ch where Hepburn writes tch: まっちゃ → matcha.
  - えい is `ei`, not `ē`. Long i is `ii`, not `ī`. Both are Hepburn as written, not oversights.

WHAT THIS GETS WRONG, AND WHY IT IS SURVIVABLE. おう is a long o inside a morpheme (とうきょう →
Tōkyō) but two vowels across a morpheme boundary (おもう → omou, not omō), and telling those apart
needs morphological analysis this deliberately does not do — §5c warns that analysers are unreliable
on exactly the names we care about, and running one here would buy a rendering nicety at the price
of a dependency. So the macron and plain styles occasionally over-shorten a kana-only verb phrase.
This is a RENDERING defect, not a data defect, and that distinction is the whole payoff of §8.1:
the kana on disk is exactly right, so improving this later costs no requests and no re-collection.
The doubled style is unaffected, because it writes back what was written.

LENGTH IS RECORDED, NOT RESOLVED. A mora carries the kana that lengthened it rather than a boolean,
because the three styles need different things from it: macron wants "this vowel is long", the
doubled style wants the literal kana that was written (おう → ou, おお → oo — those are different
spellings and flattening them loses information we were handed), and the plain style wants it gone.

ROMAJI BACK-CONVERSION is the reverse table, and it exists for one reason: the bulk databases in
§3 return romanised titles rather than kana, and a romanised string cannot drive the style toggle.
Converting it back to kana restores that ability — but the conversion is LOSSY in exactly the place
that matters, because a macron-less romanisation has already thrown the length away and "Yuri"
cannot be un-flattened. So anything this produces is recorded with reading_basis `back-converted`
and is never `stated`; the source string is kept verbatim beside it so a later kana source can
replace the guess without having lost the original.
"""

# The Japanese names of the Latin letters. Closed set, no maintenance, and the only readings a
# single Latin character legitimately takes in running Japanese.
#
# HERE RATHER THAN IN pass4_analyser, WHICH IS WHERE IT WAS. Two producers make furigana spans:
# the analyser tokenises, and `align` below pairs a whole reading against a whole surface. Only the
# first knew this rule, so `Queentopia` came back carrying キュー and `rurudo` carrying るるど. One
# table, one reader, per STANDING-INSTRUCTIONS §3. pass4_analyser re-exports the name so every
# existing reference still resolves.
LETTER_NAME = {
    "A": "エー", "B": "ビー", "C": "シー", "D": "ディー", "E": "イー", "F": "エフ", "G": "ジー",
    "H": "エイチ", "I": "アイ", "J": "ジェー", "K": "ケー", "L": "エル", "M": "エム", "N": "エヌ",
    "O": "オー", "P": "ピー", "Q": "キュー", "R": "アール", "S": "エス", "T": "ティー", "U": "ユー",
    "V": "ブイ", "W": "ダブリュー", "X": "エックス", "Y": "ワイ", "Z": "ゼット",
}

# Mora → (romaji, vowel). Written hiragana-first; katakana is folded onto it before lookup, so the
# katakana-only extended morae (ファ, ヴィ, ティ …) appear here in their hiragana-folded spelling.
BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o",
    "ゔ": "vu",
    # Small kana standing alone — they only reach here when nothing combined with them, which is
    # itself a signal the string is decorative rather than a reading.
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "ゎ": "wa",
}

# Two-kana morae. Youon plus the extended set katakana uses for foreign sounds, which titles are
# full of (ピクニック, ヴァンパイア) even when authors are not.
DIGRAPH = {
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo", "きぇ": "kye",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho", "しぇ": "she",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo", "じぇ": "je",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho", "ちぇ": "che",
    "ぢゃ": "ja", "ぢゅ": "ju", "ぢょ": "jo",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    "ふぁ": "fa", "ふぃ": "fi", "ふぇ": "fe", "ふぉ": "fo", "ふゅ": "fyu",
    "うぃ": "wi", "うぇ": "we", "うぉ": "wo",
    "ゔぁ": "va", "ゔぃ": "vi", "ゔぇ": "ve", "ゔぉ": "vo", "ゔゅ": "vyu",
    "てぃ": "ti", "でぃ": "di", "てゅ": "tyu", "でゅ": "dyu",
    "とぅ": "tu", "どぅ": "du",
    "つぁ": "tsa", "つぃ": "tsi", "つぇ": "tse", "つぉ": "tso",
    "いぇ": "ye",
    "くゎ": "kwa", "ぐゎ": "gwa",
}

MACRON = {"a": "ā", "i": "ii", "u": "ū", "e": "ē", "o": "ō"}
VOWELS = "aiueo"
SOKUON = "っ"
PROLONG = "ー"
HATSUON = "ん"

# Which following kana lengthens which vowel. えい is deliberately absent: Hepburn writes Keiko,
# not Kēko, and treating い as a lengthener there would produce a spelling nobody uses.
LENGTHENS = {"a": {"あ"}, "i": {"い"}, "u": {"う"}, "e": {"え"}, "o": {"う", "お"}}

KATAKANA_START, KATAKANA_END = 0x30A1, 0x30F6
HIRAGANA_START = 0x3041

# Punctuation a kana-only string may contain, and what it becomes when rendered. These are not
# readings — nothing is pronounced — so they pass through rather than being romanised. Anything not
# listed here is emitted unchanged, which is the right default for ☆ and × and their friends.
PUNCT = {"、": ", ", "。": ". ", "・": " ", "〜": "~", "～": "~", "＝": "=", "！": "!", "？": "?",
         "「": "“", "」": "”", "『": "“", "』": "”", "（": " (", "）": ") ",
         "…": "...", "‥": "..", "　": " ", "＆": " & ", "／": "/"}

# What may sit between kana without making a string un-romanisable. Symbols are included because a
# title like ガールズ×ヴァンパイア is fully determined — the × is already Latin and stays Latin.
PUNCT_OK = set(" 　・-〜～＝=、。「」『』（）()！？!?…‥,.／/×☆★♪†＆&＋+♡♥∞→←＊*:：;；’'\"")


def to_hiragana(s):
    """Fold katakana onto hiragana so one table serves both. ー and small kana survive unchanged."""
    return "".join(
        chr(ord(c) - KATAKANA_START + HIRAGANA_START) if KATAKANA_START <= ord(c) <= KATAKANA_END else c
        for c in s
    )


def to_katakana(s):
    """Katakana is the storage form for readings — it is what MADB, openBD and furigana use."""
    return "".join(
        chr(ord(c) - HIRAGANA_START + KATAKANA_START) if HIRAGANA_START <= ord(c) <= 0x3096 else c
        for c in s
    )


def is_kana(c):
    o = ord(c)
    return HIRAGANA_START <= o <= 0x3096 or KATAKANA_START <= o <= 0x30FA or c in (PROLONG, "ヽ", "ヾ")


def has_kanji(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF or 0x3400 <= ord(c) <= 0x4DBF for c in s)


def has_kana(s):
    return any(is_kana(c) for c in s)


def has_latin(s):
    return any(("a" <= c <= "z") or ("A" <= c <= "Z") or (0xFF21 <= ord(c) <= 0xFF5A) for c in s)


def script_class(s):
    """The §2 buckets. Order matters: kanji wins, because one kanji is enough to need a source."""
    if has_kanji(s):
        return "kanji"
    if has_kana(s) and has_latin(s):
        return "mixed"
    if has_kana(s):
        return "kana"
    if has_latin(s):
        return "latin"
    return "other"


def kana_only(s):
    """True when every meaningful character is kana — the pass 1 condition.

    Punctuation and whitespace pass, because 〜 and ・ and spaces are not readings and a title like
    ひとりぼっち〜ゆめのなか〜 is still mechanically romanisable. A digit is not: 1話 needs a reading
    decision (ichi? hito?) we have no source for.
    """
    seen = False
    for c in s:
        if is_kana(c):
            seen = True
        elif c in PUNCT_OK:
            continue
        else:
            return False
    return seen


def morae(reading):
    """Split a kana string into morae, each carrying whatever lengthened it.

    Returns a list of dicts: {'r': romaji, 'v': final vowel, 'long': the lengthening kana or None}.
    Non-kana characters pass through as {'raw': c} so a partly-Latin title still renders.
    """
    s = to_hiragana(reading)
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == SOKUON:
            out.append({"sokuon": True})
            i += 1
            continue
        if c == HATSUON:
            out.append({"r": "n", "v": None, "long": None, "n": True})
            i += 1
            continue
        pair = s[i:i + 2]
        if len(pair) == 2 and pair in DIGRAPH:
            r, i = DIGRAPH[pair], i + 2
        elif c in BASE:
            r, i = BASE[c], i + 1
        else:
            out.append({"raw": reading[i]})
            i += 1
            continue
        v = r[-1] if r and r[-1] in VOWELS else None
        long = None
        if v and i < n:
            nxt = s[i]
            if nxt == PROLONG:
                long, i = PROLONG, i + 1
            elif nxt in LENGTHENS.get(v, ()):
                # A VOWEL KANA THAT WILL ITSELF BE LENGTHENED BELONGS TO WHAT FOLLOWS IT, not to
                # what precedes. 女王 is ジョ オ ウ, and taking the オ into ジョ leaves the ウ
                # stranded as its own syllable: jōu, which is not a romanisation of anything. The
                # long vowel there is オウ, so the answer is joō.
                #
                # Only where the lengthener is a written vowel. ー is not a vowel and cannot start
                # a long vowel of its own, so オーウチ keeps its merge and stays Ōuchi.
                nxt2 = s[i + 1] if i + 1 < n else None
                nv = (BASE.get(nxt) or "")[-1:]
                if not (nxt2 and nv and nxt2 in LENGTHENS.get(nv, ())):
                    long, i = nxt, i + 1
        out.append({"r": r, "v": v, "long": long})
    return out


def romanise(reading, style="macron"):
    """Render a kana reading in one of the three styles §8.1 makes a reader preference.

    style: 'macron' (Yūri) | 'double' (Yuuri) | 'plain' (Yuri).

    The doubled style writes the kana that was actually there — おう becomes `ou` and おお becomes
    `oo`, because those are two different spellings and we were given which one it was.
    """
    ms = morae(reading)
    parts, pending_sokuon = [], False
    for idx, m in enumerate(ms):
        if m.get("sokuon"):
            pending_sokuon = True
            continue
        if "raw" in m:
            parts.append(PUNCT.get(m["raw"], m["raw"]))
            pending_sokuon = False
            continue
        r = m["r"]
        if m.get("n"):
            # Apostrophe only where the next mora would otherwise merge into it.
            nxt = ms[idx + 1] if idx + 1 < len(ms) else None
            if nxt and "r" in nxt and (nxt["r"][0] in VOWELS or nxt["r"][0] == "y"):
                r = "n'"
            parts.append(r)
            pending_sokuon = False
            continue
        if pending_sokuon:
            r = ("t" + r) if r.startswith("ch") else (r[0] + r)
            pending_sokuon = False
        v, long = m["v"], m["long"]
        if long and v:
            if style == "macron":
                # Long i is `ii` when it was written いい (Hepburn's own spelling) but `ī` when it
                # was written with ー — biiru would be a misreading of ビール.
                r = r[:-1] + ("ī" if (v == "i" and long == PROLONG) else MACRON[v])
            elif style == "double":
                r = r + (v if long == PROLONG else BASE[long])
            # 'plain' drops it entirely, which is the point of the style.
        parts.append(r)
    if pending_sokuon:
        parts.append("")
    return "".join(parts)


# Grammatical particles stay lower case in a romanised Japanese title — "Kimi no Na wa", not
# "Kimi No Na Wa". Never the first word, where the particle reading is not the likely one and a
# title has to start with a capital regardless.
# Deliberately conservative. The short sentence-final particles — na, ne, yo, sa — and the
# one-letter ones — o, e — collide with ordinary nouns: 名 is "na" and means NAME, so including it
# turned 君の名は into "Kimi no na wa". Lower-casing a noun is a worse error than capitalising a
# particle, because it reads as a typo rather than as a style choice, so the list holds only
# particles that are rarely anything else when standing alone.
PARTICLES = {"wa", "ga", "no", "ni", "wo", "to", "de", "mo", "kara", "made", "yori",
             # を and へ render as single letters and, standing alone between words, are the
             # particles essentially always. 名 ("na") was the collision worth avoiding, not these.
             "o", "e"}


def title_case(s, particles=True):
    """Capitalise a rendered name without touching an internal apostrophe: Shin'ichi, not Shin'Ichi.

    `particles=False` for a PERSONAL NAME. Grammatical particles do not occur inside one, so the
    rule can only misfire there: 宮原 都 came out "Miyahara to" because 都 reads "to", which is also
    the particle と. Lower-casing part of someone's name is a worse error than capitalising a
    particle in a title, and unlike the title case it is about a person.

    Particles are left alone in titles. This matters because the alternative — capitalising every word —
    reads as machine output to anyone who knows the language, and the strings we get FROM sources
    already have it right, so a renderer that got it wrong would look like a downgrade exactly
    where it is meant to be an improvement.
    """
    # The punctuation table already carries its own trailing space, so a token boundary next to it
    # produced ",  ". Collapse before splitting rather than after, or the empty word becomes a word.
    s = re.sub(r"\s+", " ", s).strip()
    # A word does not necessarily start or end with a letter. 彼氏の女友達がぐいぐい来る（私に）
    # romanised to "(watakushi Ni)": the bracket took the capital and left the word lower case,
    # while "ni)" failed to match the particle list because of the one it carried. Both come from
    # the same assumption. Capitalise the first LETTER wherever it sits, and test the particle on
    # the word with its punctuation stripped.
    def cap(w):
        for i, c in enumerate(w):
            if c.isalpha():
                return w[:i] + w[i].upper() + w[i + 1:]
        return w

    out = []
    for i, w in enumerate(s.split(" ")):
        if not w:
            out.append(w)
            continue
        core = w.strip("（）()「」『』【】《》[]{}、。,.!?！？…—-~〜・:：;；\"'")
        if particles and i and core.lower() in PARTICLES:
            out.append(w.lower())
        else:
            out.append(cap(w))
    return " ".join(out)


# ---------------------------------------------------------------------------------------------
# Romaji → kana, for the bulk databases that hand back romanised strings (§3.2, §3.3).

_REVERSE = {}
for _k, _r in list(DIGRAPH.items()) + list(BASE.items()):
    _REVERSE.setdefault(_r, _k)
# The line that exists for exactly this: where two kana can produce one romaji, say which one a
# romanised source meant. `wo` was reaching うぉ, because DIGRAPH is merged first and setdefault
# lets it keep the key, while を never contests it at all. を romanises as `o`, so nothing in the
# table ever maps `wo` back to it. Every source that hands us romaji writes the particle `wo`, and
# kana.PARTICLES and pass2_bulk.JA_PARTICLES both already say so. Five stored readings had
# あなたが私ウォ変えたから and its like.
_REVERSE.update({"n": "ん", "shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ", "ji": "じ",
                 "wo": "を"})
_MAX_R = max(len(r) for r in _REVERSE)
# A macron is length information a plain letter has already thrown away, so expand it back into the
# kana that would have been written. ē → ei is the Hepburn convention running in reverse.
_MACRON_EXPAND = {"ā": "aa", "ī": "ii", "ū": "uu", "ē": "ei", "ō": "ou",
                  "â": "aa", "î": "ii", "û": "uu", "ê": "ei", "ô": "ou"}


def romaji_to_kana(s):
    """Best-effort reverse transliteration; None when anything fails to convert.

    Returning None on ANY leftover is deliberate. A partial conversion of an official English title
    ("Otherside Picnic") would produce a plausible-looking kana string that is not a reading of
    anything, and a wrong reading is the failure mode §1 is built to avoid. Refusing is cheap, and
    it is also what stops an English word being silently transliterated as though it were Japanese.
    """
    if not s:
        return None
    text = s.lower().strip()
    for mac, plain in _MACRON_EXPAND.items():
        text = text.replace(mac, plain)
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " -　":
            out.append(" ")
            i += 1
            continue
        if c == "'":
            i += 1
            continue
        if c == "n" and i + 1 < n and text[i + 1] not in VOWELS and text[i + 1] != "y":
            out.append("ン")
            i += 1
            continue
        # Gemination: a doubled consonant is っ plus the consonant, tch is っ plus ch.
        if c not in VOWELS and i + 1 < n and text[i + 1] == c:
            out.append("ッ")
            i += 1
            continue
        if text.startswith("tch", i):
            out.append("ッ")
            i += 1
            continue
        for ln in range(min(_MAX_R, n - i), 0, -1):
            chunk = text[i:i + ln]
            if chunk in _REVERSE:
                out.append(to_katakana(_REVERSE[chunk]))
                i += ln
                break
        else:
            return None
    kana = " ".join("".join(out).split())
    return kana or None


# ── Furigana alignment ────────────────────────────────────────────────────────────────────────
#
# Whole-string ruby — the reading of a title stacked over the whole title — is what this project
# shipped first and it is not how furigana works. Real furigana sits over the kanji it reads, and
# the kana already in the surface sit under nothing.
#
# The standard method, and there is no permissively-licensed Python library that does it for
# arbitrary text: pykakasi is GPL and word-level only, and JmdictFurigana is per-kanji but is
# CC BY-SA (JMdict's licence, which this project avoids) and its own documentation discourages
# using it across sentences. kuroshiro does it properly and is JavaScript. So the morphological
# analysis stays with the library that is good at it — SudachiPy, Apache-2.0, already a dependency,
# giving a reading per token — and only the alignment inside a token is ours.
#
# THE ALGORITHM. Split the surface into runs of kanji and runs of kana. The kana runs must appear
# in the reading, in order, unchanged: they are ANCHORS. Whatever lies between two anchors is the
# reading of the kanji run between them. 喰べたい / タベタイ anchors on べたい, leaving タ for 喰.
#
# It fails safely. If an anchor cannot be found the alignment is abandoned for that token and the
# caller falls back to reading the whole token — because ruby over the WRONG character is worse
# than ruby over too many, and unlike a whole-token reading it is wrong in a specific, visible
# place that a reader will notice.

# A kana that is pronounced as a different kana when it works as a particle. An anchor is kana the
# two sides carry unchanged, and these three are exactly the kana that do not: あの子は優しすぎる。
# reads アノコワヤサシスギル。, so the は never matched, the anchor search failed, and the whole title
# went without ruby. 169 of 842 kanji titles were in that state, most of them for this reason.
#
# Applied only when the character stands alone as a run, which is what a particle is. こんにちは is
# one word and its は is read は; the topic marker is a run of its own between other runs.
PARTICLE_SOUND = {"は": "わ", "へ": "え", "を": "お"}


# 四つ仮名: ぢ and づ merged with じ and ず in speech, and a reading records the sound. ゆりづくし
# reads ユリズクシ, so a comparison that keeps them apart rejects a correct reading.
YOTSU = {"ぢ": "じ", "づ": "ず"}


def _expand_choonpu(t):
    """Replace ー with the vowel it lengthens, so アラサー and アラサア compare equal.

    A reading may spell a long vowel either way and both are right. The surface keeps the bar
    because that is how the title is written; the reading often spells the vowel out.
    """
    out = []
    for c in t:
        if c in "ーｰ" and out:
            r = BASE.get(to_hiragana(out[-1])) or DIGRAPH.get(to_hiragana(out[-1])) or ""
            out.append({"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}.get(r[-1:], c))
        else:
            out.append(c)
    return "".join(out)


# ヶ in a place name is a genitive marker read か or が, not a small ケ: 阿佐ヶ谷 is アサガヤ.
KE_SMALL = {"ヶ": ("か", "が"), "ケ": ("か", "が", "け")}


def _anchor_eq(read, text):
    """Does this stretch of the reading spell this run of surface kana?

    Two things the two sides disagree about, neither of them a real difference:

    PARTICLES. は, へ and を are pronounced わ, え and お when they do a particle's work, so a
    reading spells them as they sound. あの子は優しすぎる。 reads アノコワヤサシスギル。.

    PUNCTUATION. A surface carries brackets and marks that a reading may or may not repeat.
    「触れたい」は恋の始まり reads フレタイワコイノハジマリ, with the brackets gone. Compared with
    punctuation dropped from both sides, so the reading may keep it or not.

    169 of 842 kanji titles were failing to align, and between them these two account for it. A
    title that fails to align gets no furigana at all, which is why one unmatched character costs
    the whole line.
    """
    return _same_kana(read, text)


def _kana_seq(t):
    """The comparable kana of a string: composed, long vowels spelled out, ぢづ folded, the rest
    dropped. Punctuation goes because a reading may or may not repeat the surface's."""
    t = to_hiragana(_expand_choonpu(unicodedata.normalize("NFC", t or "")))
    return [YOTSU.get(c, c) for c in t if is_kana(c)]


def _same_kana(read, text):
    """Does this stretch of reading spell this stretch of surface?

    ONE DEFINITION, because four callers asked it and each had drifted. A surface writes は and a
    reading records わ; ー and the vowel it lengthens are the same sound; ヶ in a place name is が.
    Every one of those is the same kind of fact, that Japanese is written one way and read another,
    and a comparison that knows some of them and not others calls correct furigana a contradiction.
    """
    a, b = _kana_seq(read), _kana_seq(text)
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y or PARTICLE_SOUND.get(y) == x:
            continue
        alt = KE_SMALL.get(to_katakana(y))
        if alt and x in alt:
            continue
        return False
    return True


def _kana_eq(a, b):
    return to_hiragana(a) == to_hiragana(b)


def align(surface, reading):
    """[(text, reading-or-None)] for one token, or None if the reading cannot be placed.

    A pair with reading None is text that reads as itself: kana, punctuation, Latin. It takes no
    ruby.

    THE SET HAS TO SPELL THE READING, and this is where that is decided. `ruby spells the reading`
    is the invariant and its stated fallback is to drop the ruby and keep the reading, which
    build.py applies to spans it loads from the store and cannot apply to spans it gets from here.
    So the producer applies it: a set that does not reconstruct the reading comes back as None, the
    title renders with no furigana, and the reading and the romanisation are untouched.

    It bites where the solver put a Latin run's reading on the kanji beside it. `BOMBSHELLS
    天野しゅにんた…` reads ボムシェルズアマノ…, and the solver gave BOMBSHELLS one kana and 天野 the
    other seven, so 天野 carried むしぇるずあまの. Nothing caught it: the run holds two kanji under
    seven kana, which is plausible arithmetic. Now that a Latin run takes no ruby at all the
    remainder no longer spells the reading, and the whole set goes rather than that.
    """
    got = _align(surface, reading)
    return got if got and ruby_spells(got, reading) else None


def _align(surface, reading):
    if not surface or not reading:
        return None
    # COMPOSED, because a decomposed kana is a different string that looks identical. Three titles
    # are stored with げ written け + U+3099 COMBINING VOICED SOUND MARK, and the combining mark is
    # not kana, so it fell out of every comparison and left the run one character longer than its
    # reading. 銀玉の価値を上げる方法 lost its furigana to a character nobody can see.
    surface = unicodedata.normalize("NFC", surface)
    reading = unicodedata.normalize("NFC", reading)

    # WHERE BOTH SIDES ARE SPACED THE SAME WAY, THE SPACES CORRESPOND, AND THEY SETTLE THE SPLIT.
    # `狗之餌 廃狼` reads `イヌノエサ ハイロウ` and the boundary is written on both sides. Stripping
    # it left the solver below free to place the split anywhere that fits, and it takes the first
    # fit while trying the shortest first, so the leading run got ONE kana and the remainder landed
    # on the last: 狗之餌 carried い and 廃狼 carried ぬのえさはいろう. 30 spans shipped holding fewer
    # kana than they have kanji, which is not a reading anybody could produce.
    #
    # Segment counts have to match. A reading is word-separated by the analyser and a surface is
    # not, so `ゆりでなる♡えすぽわーる` against `ユリ デ ナル ...` has spaces that mean something
    # else entirely. Where the counts disagree this says nothing and the whole-string search runs
    # exactly as before.
    s_parts = [p for p in re.split(r"[ 　]+", surface) if p]
    r_parts = [p for p in re.split(r"[ 　]+", reading) if p]
    if len(s_parts) > 1 and len(s_parts) == len(r_parts):
        seps = re.findall(r"[ 　]+", surface.strip())
        out, whole = [], True
        for i, (s, r) in enumerate(zip(s_parts, r_parts)):
            if i:
                out.append((seps[i - 1] if i - 1 < len(seps) else " ", None))
            got = _align(s, r)
            if got is None:
                whole = False
                break
            out.extend(got)
        if whole:
            return out
    reading = re.sub(r"[ 　]+", "", reading)

    if not any(not is_kana(c) and (c.isalnum() or "一" <= c <= "鿿") for c in surface):
        return [(surface, None)]                      # nothing to annotate

    # An ANCHOR is text that appears in the reading as itself: kana, and punctuation, which both
    # sides carry unchanged. Everything else is READ — kanji, but also digits and Latin, because
    # 100日後に reads ヒャクニチゴニ and treating "100" as an anchor makes the whole title unalignable.
    def is_anchor(c):
        return is_kana(c) or not (c.isalnum() or "一" <= c <= "鿿")

    runs, cur, cur_is_kanji = [], "", None
    for c in surface:
        k = not is_anchor(c)
        if cur and k != cur_is_kanji:
            runs.append((cur, cur_is_kanji))
            cur = ""
        cur, cur_is_kanji = cur + c, k
    if cur:
        runs.append((cur, cur_is_kanji))

    # Backtracking, not greedy first-match. An anchor kana often also occurs INSIDE the reading of
    # the kanji before it: 100日後に reads ヒャクニチゴニ, and pinning the anchor に to the FIRST ニ
    # leaves 100日後 reading ヒャクニ and the tail unconsumed. The search has to be free to reject a
    # placement and try the next one, which is what makes this the standard alignment rather than a
    # scan. Titles are short and runs are few, so the exhaustive form is fast enough and is much
    # easier to be sure of than a scoring heuristic.
    def solve(i, pos, strict):
        if i == len(runs):
            return [] if pos == len(reading) else None
        text, readable = runs[i]
        if not readable:
            # How much of the reading this run consumes is not simply its length: the reading may
            # drop punctuation the surface carries, so a run of five characters can spell three.
            # Every length that still spells the run is tried, longest first, so a reading that
            # does keep its punctuation is matched as written.
            #
            # UNDER `strict` THE RUN MUST BE SPELLED WHOLE. Letting it consume nothing is what lets
            # the kanji run beside it swallow the punctuation: 潮滅に沈む翡翠、北のまちの黒曜 reads
            # ...ヒスイ、キタ... and shipped with 翡翠 carrying ひ and 北 carrying すい、きた, the
            # 、 eaten by a run that has no 、 in it. A kana run is already whole, because its `lo`
            # is its own length, so this only ever tightens punctuation.
            # WHITESPACE IS NOT SOMETHING THE READING CAN SPELL. Its spaces were taken out above,
            # so a surface run of ` ～` has one character the reading can carry and one it cannot.
            # Requiring the whole run made strict fail on every title spaced before a mark, and the
            # permissive pass then let the kanji run swallow the mark: 百合探偵少女 read ゆ beside
            # 朱理推 reading りたんていしょうじょ～あかりすい.
            lo = (len([c for c in text if not c.isspace()]) if strict
                  else sum(1 for c in text if is_kana(c)))
            for take in range(min(len(text), len(reading) - pos), lo - 1, -1):
                if not _anchor_eq(reading[pos:pos + take], text):
                    continue
                rest = solve(i + 1, pos + take, strict)
                if rest is not None:
                    return [(text, None)] + rest
            return None
        # A read run takes at least one kana, and every split is tried until the rest fits.
        for stop in range(pos + 1, len(reading) + 1):
            rest = solve(i + 1, stop, strict)
            if rest is not None:
                return [(text, reading[pos:stop])] + rest
        return None

    # THE STRICT PASS FIRST, AND ITS FAILURE IS NOT AN ERROR. A reading that keeps every mark the
    # surface carries is aligned against them, which pins the runs either side. A reading that
    # genuinely drops them, and many do, fails that pass and is aligned by the permissive one,
    # which is the behaviour this had throughout.
    return [(t, _ruby_worth_printing(t, r))
            for t, r in (solve(0, 0, True) or solve(0, 0, False) or [])] or None


def _ruby_worth_printing(text, reading):
    """The reading to put over this run, or None where nothing should go over it.

    APPLIED ON THE OUTPUT, because the run has to stay READABLE for the search to place it. Latin
    and digits are read runs on purpose: 100日後 reads ヒャクニチゴ, and treating them as anchors
    makes that title unalignable. What the solver is free to do, and did, is give a run a reading
    nobody should see.

    A READING THAT REPEATS ITS OWN TEXT ANNOTATES NOTHING. `紗痲 Fallin' Jail` reads
    `シャマ Fallin' Jail`, so the solver paired Fallin with Fallin and Jail with Jail, and the work
    shipped rendering `紗痲しゃま FallinFallin' JailJail` in Japanese with furigana on. A reader
    reported it.

    FURIGANA OVER A LATIN WORD IS NOT FURIGANA. `Queentopia` came back under キュー and `rurudo`
    under るるど, which is the solver spending a kanji run's reading on the run beside it. The
    exception is a SINGLE letter read as its own name, V in Vチューバー being ブイ, which is worth
    printing and is a closed set of 26. pass4_analyser has applied exactly this rule to its own
    spans all along; this is the second producer of the same fact learning it.
    """
    if reading is None:
        return None
    t, r = str(text), str(reading)
    if unicodedata.normalize("NFKC", r) == unicodedata.normalize("NFKC", t):
        return None
    if t.isascii() and any(c.isalnum() for c in t):
        if len(t) == 1 and t.isalpha():
            named = LETTER_NAME.get(t.upper())
            return reading if named and to_katakana(r) == named else None
        return None
    return reading


# Per-character readings, for splitting a compound's reading across its characters (jukugo-ruby).
# One on-reading and one kun-reading each, which is thin: 純 is listed シュン and 純情 is ジュンジョウ.
# So a split is never trusted on the table alone. It has to reconstruct the stored reading exactly,
# and it has to be the only way of doing so.
_UNIHAN = None

# 連濁: the second element of a compound often voices its first consonant, 花火 ハナ+ヒ -> ハナビ.
RENDAKU = {"カ": "ガ", "キ": "ギ", "ク": "グ", "ケ": "ゲ", "コ": "ゴ",
           "サ": "ザ", "シ": "ジ", "ス": "ズ", "セ": "ゼ", "ソ": "ゾ",
           "タ": "ダ", "チ": "ヂ", "ツ": "ヅ", "テ": "デ", "ト": "ド",
           "ハ": ["バ", "パ"], "ヒ": ["ビ", "ピ"], "フ": ["ブ", "プ"],
           "ヘ": ["ベ", "ペ"], "ホ": ["ボ", "ポ"]}


def _unihan():
    global _UNIHAN
    if _UNIHAN is None:
        import json
        import pathlib
        p = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "unihan-on.json"
        try:
            _UNIHAN = (json.loads(p.read_text()) or {}).get("readings") or {}
        except OSError:
            _UNIHAN = {}
    return _UNIHAN


def char_readings(c):
    """Every katakana reading one character might take here, including regular sound changes.

    促音便 (the final mora becoming ッ before a voiceless consonant, 学校 ガク+コウ -> ガッコウ) and
    連濁 are both included, because a compound that undergoes either is still the same two
    characters and refusing it would just push a correct split into the fallback.
    """
    out = set()
    for r in _unihan().get(c) or []:
        r = to_katakana((r or "").strip())
        if not r or not kana_only(r):
            continue
        out.add(r)
        if len(r) > 1:
            out.add(r[:-1] + "ッ")                      # 促音便
        head = RENDAKU.get(r[0])
        for v in ([head] if isinstance(head, str) else head or []):
            out.add(v + r[1:])                          # 連濁
    return out


def jukugo_split(surface, reading):
    """[(character, reading)] splitting one kanji run across its characters, or None.

    None wherever the split is not certain: no partition found, or more than one. A wrong split is
    worse than no split, because it puts a reading over a character it does not belong to and the
    reader has no way to tell. Falling back leaves the run annotated as a group, which is what the
    layout rules call for when the parts cannot be worked out.
    """
    surface, reading = surface or "", to_katakana(reading or "")
    if len(surface) < 2 or not reading:
        return None
    cand = [char_readings(c) for c in surface]
    if not all(cand):
        return None

    found = []

    def walk(i, pos, acc):
        if len(found) > 1:
            return
        if i == len(surface):
            if pos == len(reading):
                found.append(list(acc))
            return
        for r in cand[i]:
            if reading.startswith(r, pos):
                acc.append((surface[i], r))
                walk(i + 1, pos + len(r), acc)
                acc.pop()

    walk(0, 0, [])
    return found[0] if len(found) == 1 else None


def ruby_spells(spans, reading):
    """Do these ruby spans spell this reading?

    The one definition of the question, because four places asked it and a strict string
    comparison is the wrong test. Furigana writes a particle as it is SPELLED and the reading
    records it as it SOUNDS: あの子は優しすぎる。 puts nothing over は and reads アノコワ…, so a
    literal comparison calls correct ruby a contradiction. Putting わ over は would be the actual
    error. Punctuation is dropped from both sides for the same reason a reading may not carry it.
    """
    if not spans or not reading:
        return False
    # Reading first, surface second. The rules are asymmetric: a SURFACE は may sound like わ, and
    # not the other way round, so passing them the wrong way round rejects correct ruby.
    return _same_kana(reading, "".join(x[1] or x[0] for x in spans))
