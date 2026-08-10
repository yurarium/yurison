#!/usr/bin/env python3
"""How two spellings of a name are compared. Two questions, two functions, one home.

WHY THIS EXISTS. A census on 2026-08-10 found thirteen functions called `fold`, and on real input
they disagreed:

    ＮＯＡＨ      key.fold NOAH        identity.fold noah        cmoa.fold NOAH
    くろば・Ｕ    key.fold くろば・U     identity.fold くろばu       cmoa.fold くろば・U
    山本 和音     key.fold 山本和音      identity.fold 山本和音      cmoa.fold 山本 和音

Two records that are one person under one fold and two people under another is the identity fault
this project keeps meeting. One invariant pinned one of the thirteen against the browser and the
other twelve answered to nobody.

THEY WERE NOT ALL ANSWERING THE SAME QUESTION, and that is why there were thirteen. There are two
questions and they want different answers:

    fold(s)      Is this the same NAME? The identity key. Conservative.
    loosely(s)   Might these be the same ENTITY, seen through two sources? For matching.

WHAT DECIDED EACH DIMENSION, measured over the 6,076 surfaces the store holds:

    NFKC width      universal agreement, and the project already ruled that full-width Latin is a
                    width and not a spelling when it fixed `ＮＯＡＨEditorial Department`.
    the space       108 merges, every one of them one person: 源 久也 and 源久也, 北斗 すい and
                    北斗すい. In Japanese the space between a family and a given name is typography.
    case            4 merges: TOBI and Tobi, 灼熱の卓球娘REBURN!! and its lower-cased twin. Real,
                    and a judgement, because case CAN distinguish a styling somebody chose.
    the interpunct  3 merges: さりいB and さりい・B are one person. But a ・ also SEPARATES people,
                    which is the whole of `facts/credit`'s interpunct rule, so removing it from an
                    identity key would erase the difference the corpus works to establish.
    brackets        57 merges: 森奈津子 and 森奈津子(作) are one person and the bracket is a role.
                    A bracket can also disambiguate two people, so this is a judgement too.

AND THE RULING THAT SPLITS THEM. This project has already decided, in the interpunct work, that a
wrong join erases a person while a wrong split invents one. Merging is the more dangerous
direction, so the IDENTITY key takes only the dimensions that are pure typography, and every
judgement lives in `loosely`, where a caller opts into it by name.
"""
import re
import unicodedata

#: Bracketed apparatus: a role, a gloss, a publisher's note. Not part of a name.
_BRACKETED = re.compile(r"[（(〔【\[][^）)〕】\]]*[）)〕】\]]")
_INTERPUNCT = re.compile(r"[・･]")


def fold(s):
    """The identity key: is this the same NAME?

    NFKC and the space, which are typography and nothing else. NFKC maps the ideographic space to
    an ASCII one, so 山本　和音 and 山本 和音 and 山本和音 are one key without a second rule.

    NOTHING ELSE. Case, the interpunct and brackets each merge real pairs and each can merge two
    things that are not one, and a wrong join erases somebody. `loosely` is where those live.
    """
    return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "")


def loosely(s):
    """The matching key: might these be the same ENTITY, seen through two sources?

    `fold` plus the three judgements: case, the bracketed apparatus, and the interpunct. Use it to
    ASK whether two records might be one, never to decide that they are. A caller that stores this
    as an identity has merged on a guess.
    """
    s = _BRACKETED.sub("", unicodedata.normalize("NFKC", str(s or "")))
    return _INTERPUNCT.sub("", s).replace(" ", "").lower()


#: THE POPULATIONS OF NAME THE STORE HOLDS, keyed by the fold above. `curate`, `names/store` and
#: `adapters/relational` each wrote this down, which the duplicates lint found on 2026-08-10.
KINDS = ("authors", "publishers", "titles")

#: The two a naming pass can research. A publisher's name is settled from its own page and from the
#: imprint registry, never by asking an analyser or a bulk source, so the passes reach two of the
#: three. `pass2_bulk` and `pass3_search` each held this as a local tuple.
RESEARCHABLE_KINDS = ("authors", "titles")
