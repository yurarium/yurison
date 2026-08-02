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


def title_case(s):
    """Capitalise a rendered name without touching an internal apostrophe: Shin'ichi, not Shin'Ichi."""
    return " ".join(w[:1].upper() + w[1:] if w else w for w in s.split(" "))


# ---------------------------------------------------------------------------------------------
# Romaji → kana, for the bulk databases that hand back romanised strings (§3.2, §3.3).

_REVERSE = {}
for _k, _r in list(DIGRAPH.items()) + list(BASE.items()):
    _REVERSE.setdefault(_r, _k)
_REVERSE.update({"n": "ん", "shi": "し", "chi": "ち", "tsu": "つ", "fu": "ふ", "ji": "じ"})
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
