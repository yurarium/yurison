#!/usr/bin/env python3
"""Whether a ・ in a credit separates two people or sits inside one person's name.

WHY THIS EXISTS. `pass4_analyser.is_credit_line` returned True for every string holding an
interpunct, and pass 4 skips a credit line, so a person whose own name contains one could never
enter the name store. That was the reported fault. Measuring the class found a worse one: the
splitter that feeds the store treats ・ as a separator, so seven people were already in the store
cut in half, with a registry identifier minted for each half. `くろば・Ｕ` reached a reader as
`Kuro Ba, U`, `さりい・Ｂ` as `Sarii, B` and `ジェイ・加藤` as `Jei, Katō`, which is a wrong split
published under the artist's own work.

WHAT DECIDES IT, AND IT IS EVIDENCE RATHER THAN SHAPE. A ・ separates people where every piece it
separates is credited SOMEWHERE ELSE on its own. 矢立肇 has a credit of his own on ラブライブ!, and
the bibliography lists 機動戦士ガンダム 水星の魔女 青春フロンティア as
`HISADAKE / 富野由悠季 / 波多ヒロ / 矢立肇`, which is a source writing the two apart. Nothing in the
corpus credits `くろば` or `Ｕ` alone, so the ・ in `くろば・Ｕ` is a character in somebody's name.

WHERE THE EVIDENCE MAY NOT COME FROM, AND THIS IS THE WHOLE OF THE CARE IN THIS MODULE
(STANDING-INSTRUCTIONS §14b). `data/names/authors.yaml` and `data/identity/credits.yaml` both hold
records for `くろば` and `Ｕ`, because the splitter under question put them there. Asking either one
whether a piece is a name of its own is asking the split whether the split was right, and it answers
yes every time: all twelve strings read as SEVERAL against the store, including the seven that are
one person. `creditline._is_a_name_of_its_own` was that question, and it is why the site was
publishing `Jei, Katō`.

So the evidence is read from credit fields that hold NO interpunct at all. 8,812 of the corpus's
8,865 do. Nothing under question contributes to the evidence about itself, and no field feeding the
evidence needs an interpunct decision to be split, so the circle is not narrowed, it is absent.

RULES TRIED AND REJECTED, so they are not re-derived.

  SCRIPT SHAPE: a ・ separates people where every piece holds a kanji, on the reasoning that ・ is
  how Japanese writes a foreign name (ステファン・セジク, アナ・C・サンチェス) and two Japanese names
  joined by one are two people. It gets eleven of the twelve right and it is wrong about
  `スタジオクロマト・スタジオコロリド`, which holds no kanji and is two animation studios. It also
  has no answer for two kana pen names joined by a ・, which is a shape a corpus of manga credits is
  full of, and it would silently join them.

  PIECE COUNT: three pieces means a foreign name. `アナ・C・サンチェス` is one person in three
  pieces and every pair in this corpus is two people, so the rule fits and states nothing: it is
  the same claim as "the middle piece is a single letter", read off four examples.

WHAT A PERSON IS ASKED, AND WHEN. Where some pieces are attested and some are not, the evidence
points both ways and this returns UNDECIDED. A string in that state is left exactly as the pipeline
treated it before, counted by `interpunct credits nobody has ruled on`, and settled by an entry in
`data/identity/interpunct-rulings.yaml`, which wins over anything computed here. A wrong split
invents a person and a wrong join erases one, so neither is worth guessing to empty a number.
"""
import pathlib
import re

import key                                                              # noqa: E402

# The answers. `ONE` means the whole string is one person and the ・ is a character in their name;
# `SEVERAL` means it is a separator; `UNDECIDED` means the corpus points both ways and a person is
# owed the question.
ONE = "one"
SEVERAL = "several"
UNDECIDED = "undecided"

INTERPUNCT = re.compile(r"[・･]")

# NOT `credit-rulings.yaml`, WHICH IS A DIFFERENT REGISTER AND WAS HERE FIRST. That file holds 85
# rulings on pairs of credits that share one READING and `adapters/credit_identity.py` reads it;
# `credits sharing a reading nobody has ruled on` is the budget behind it. This file answers a
# question about one credit string. The names are close enough that writing to the wrong one looks
# like an edit and reads as 81 pairs losing their ruling, which is what happened here once.
RULINGS = "data/identity/interpunct-rulings.yaml"


def pieces(name):
    """What an interpunct divides this string into, or `()` where it holds none."""
    if not INTERPUNCT.search(str(name or "")):
        return ()
    got = tuple(p.strip() for p in INTERPUNCT.split(str(name)) if p.strip())
    return got if len(got) > 1 else ()


def attested_apart(fields, split):
    """Folded names some source credits ON ITS OWN, read only off fields holding no interpunct.

    `fields` is every credit field the corpus carries. `split` is the splitter that KEEPS an
    interpunct inside a part, `inputs.split_authors(…, interpunct=False)` folded down to names, and
    it is handed in rather than imported so this stays a function of its inputs and the suite can
    give it a stub. Which of the two splitters it is makes no difference here, since every field
    this reads holds no interpunct for them to disagree about, and it makes all the difference in
    `settled` below, where a part has to arrive with its ・ still in it.

    THE FILTER IS THE POINT. A field holding an interpunct is a field this module has an open
    question about, so it contributes nothing to the answer, and the fields that remain can be split
    without anybody deciding anything about a ・ first.
    """
    out = set()
    for field in fields or ():
        text = str(field or "")
        if not text.strip() or INTERPUNCT.search(text):
            continue
        for name in split(text):
            if str(name or "").strip():
                out.add(key.fold(name))
    return out


def role(name, attested):
    """`ONE`, `SEVERAL` or `UNDECIDED` for one credit string, from the corpus evidence alone.

    A string with no interpunct in it gets `ONE`, which is the true answer and not a default: there
    is nothing here to separate anybody.
    """
    got = pieces(name)
    if not got:
        return ONE
    apart = [key.fold(p) in (attested or ()) for p in got]
    if all(apart):
        return SEVERAL
    if not any(apart):
        return ONE
    return UNDECIDED


def load_rulings(path=RULINGS):
    """`{folded credit: ONE | SEVERAL | None}` from the hand-written file. `{}` where there is none.

    A KEY WITH NO VALUE IS AN ANSWER AND NOT AN EMPTY SLOT (§5). It says a person has been asked
    about this string and has not answered yet, and it stops the rule answering in the meantime, so
    a case somebody flagged is held rather than being settled by a measure they doubted.
    """
    import yaml
    f = pathlib.Path(path)
    if not f.exists():
        return {}
    doc = yaml.safe_load(f.read_text()) or {}
    out = {}
    for credit, said in (doc.get("rulings") or {}).items():
        value = (said or {}).get("people") if isinstance(said, dict) else said
        out[key.fold(credit)] = value if value in (ONE, SEVERAL) else None
    return out


def settle(name, attested, ruled=None):
    """The answer for one credit string: a person's ruling where there is one, the rule otherwise.

    ONE PRODUCER PER STRING (§3). The file is consulted first and its answer is final, so no string
    is decided in two places and no caller has to merge two verdicts.
    """
    said = (ruled or {}).get(key.fold(name), False)
    if said in (ONE, SEVERAL):
        return said
    if said is None:
        return UNDECIDED
    return role(name, attested)


def settled(fields, split, ruled=None):
    """`{folded name: ONE | SEVERAL}` for every interpunct credit in `fields` that has an answer.

    BOTH ANSWERS TRAVEL, because the two callers default in opposite directions and both are right
    to. `inputs.split_credits_detail` splits on a ・ when it is feeding the name store and
    keeps it when it is composing a byline to print, and that disagreement is what the corpus can
    now settle for the strings it has evidence about. A map of just the names to keep whole would
    leave the printing caller keeping 矢立肇・富野由悠季 whole, and a map of just the names to split
    would leave the store cutting くろば・Ｕ in half. So both answers travel, and a string with
    neither is left to the flag exactly as before.

    UNDECIDED IS ABSENT FROM THE MAP, which is what makes "the flag decides" the same sentence as
    "nothing settled this".
    """
    attested = attested_apart(fields, split)
    out = {}
    for field in fields or ():
        for name in split(str(field or "")):
            if not pieces(name):
                continue
            said = settle(name, attested, ruled)
            if said in (ONE, SEVERAL):
                out[key.fold(name)] = said
    return out


def unruled(fields, split, ruled=None):
    """The credit strings a person is owed a ruling on, in order. The budget counts these.

    Both shapes are in it: a string the corpus points both ways about, and a string somebody put in
    the ruling file and has not answered yet.
    """
    attested = attested_apart(fields, split)
    out = set()
    for field in fields or ():
        for name in split(str(field or "")):
            if pieces(name) and settle(name, attested, ruled) == UNDECIDED:
                out.add(name)
    return sorted(out)
