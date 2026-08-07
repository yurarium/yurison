#!/usr/bin/env python3
"""Credits in the author store that are not people, and what each one is instead.

WHY THE AUTHOR STORE HOLDS A TELEVISION COMPANY. `build.py`'s autopilot feeds
`pass4_analyser.fill_missing` every credit the corpus carries, and a credit line names whoever the
source put in it. 円谷プロダクション is the sole credit on the SSSS.GRIDMAN anthology, 一迅社
publishes ふたりエスケープ公式コミックアンソロジー and is credited on it, and 東方Project is credited
on three works derived from it. Each is a real credit written by the source, and none of them is a
person.

`credits.is_a_person` DOES NOT CATCH THEM AND WAS NOT WRITTEN TO. Its docstring says what it is for:
a platform that puts the newest chapter where the author goes, so `#1(1)` and `７` become bylines.
It tests whether a credit is made only of digits and punctuation, which no company name is, and the
autopilot never asks it anyway. Nothing was failing; nobody had asked the question.

WHAT HAPPENS TO ONE, AND WHY IT IS NOT DELETION. The credit is what the source wrote and the
interface prints the field as written, so the record stays and keeps rendering. What it stops doing
is passing as a personal name:

  THE ANALYSER IS TRUSTED ABOUT A COMPANY AND NOT ABOUT A PERSON. `build.py` withholds furigana from
  a reading a machine guessed for a PERSON, because a pen name is what an analyser is worst at and a
  misread name misnames somebody. A company name is made of ordinary words and is neither a pen name
  nor a coinage: 円谷プロダクション reads ツブラヤプロダクション and the ruby over 円谷 is つぶらや.
  The protection is for people and it costs an organisation its furigana for nothing.

  A PERSONAL NAME HOLDS NO GRAMMATICAL PARTICLE and an organisation's name is a phrase that may.
  `title_case` is told which it is looking at.

A MAGAZINE IS A VENUE (DEFINITIONS, appendix). 電撃G'sマガジン is credited on
剣道娘は異世界でも斬り結ぶ【タテスク】 beside the game studio, which is the platform naming where the
work runs in the field a byline goes in. The database does not get to rewrite what a source wrote,
so the credit stays; calling it an author is the category error the appendix names, and marking it
`magazine` is how the record stops making that claim.

NOTATION IS THE OTHER HALF, and it duplicates a record the store already holds.
`はいむらきよたか(キャラクターデザイン)` is one person with a role welded on, and the store holds the
person separately. The test is `inputs.split_authors`, which is the splitter every other caller
uses: a string it reduces to one part that is not the string is cataloguing around a name, and the
name is the record that should answer.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# WRITTEN OUT, AND EVERY ENTRY READ OFF A CREDIT THIS CORPUS CARRIES. `inputs.ROLES` records why:
# a class of organisation kanji reads 委員会 and 学院 for free and reads 会 and 院 as organisations
# too, and a credit field is full of pen names built from ordinary words. 部 alone would take
# 阿部 and 渡部, 社 alone would take any pen name ending in it, so neither is here.
#
# The kind is what the thing IS, because that is the answer a later reader needs. `organisation`
# for all of them would record only that we declined to call it a person.
KINDS = (
    ("committee", ("製作委員会", "制作委員会", "実行委員会")),
    ("company", ("プロダクション", "株式会社", "有限会社")),
    ("school", ("学院",)),
    ("project", ("プロジェクト", "Project", "PROJECT")),
    ("magazine", ("マガジン",)),
    ("studio", ("スタジオ", "STUDIO", "Studio")),
    ("desk", ("編集部", "編纂室", "資料室")),
)

NOTATION = "notation"


def organisation(name):
    """The class of organisation this credit names, or None where nothing says it is one.

    A SUBSTRING TEST, because the class word sits at either end: 円谷プロダクション closes with it
    and スタジオコロリド opens with it.
    """
    s = str(name or "")
    for kind, words in KINDS:
        if any(w in s for w in words):
            return kind
    return None


def notation(name):
    """Whether this credit is one name with cataloguing welded on to it.

    THE SPLITTER DECIDES, so this is not a fourth copy of the role vocabulary. There are three
    already: `inputs.ROLES`, `openbd_reading.ROLE_ONLY` and `pass4_analyser.ROLE`, and the third
    one missing キャラクターデザイン is how these records were created. See STANDING-INSTRUCTIONS §3.

    A string the splitter leaves alone is a name. `南瓜かぷちー(表紙` keeps its unbalanced bracket
    through the splitter and is therefore NOT reported here: it is a capture that went wrong
    upstream, which is a different fault with a different fix, and calling it notation would file it
    where nobody would look for it.
    """
    from names.inputs import split_authors
    s = str(name or "").strip()
    if not s:
        return False
    parts = split_authors(s, interpunct=False)
    return len(parts) == 1 and parts[0][0] != s


def kind(name):
    """What this credit is, where it is not a person. None means nothing here says otherwise.

    None IS NOT "THIS IS A PERSON". It is silence, which is the honest answer for a credit no rule
    recognises, and it is what keeps the vocabulary from having to know every organisation on earth.
    """
    return organisation(name) or (NOTATION if notation(name) else None)


def sweep(names):
    """Mark every record this recognises. `{name: kind}` for what changed.

    Additive and idempotent: a record already carrying the same mark is left alone, so this can run
    again without touching the file.
    """
    changed = {}
    for name, rec in names.items():
        got = kind(name)
        if not got or rec.get("entity") == got:
            continue
        rec["entity"] = got
        changed[name] = got
    return changed


# Where the corpus itself files a name as something other than a person. Read by the check, and
# deliberately NOT by `kind` above: a measure that asks what the fix asks can only report what the
# fix already handles (STANDING-INSTRUCTIONS §14b).
def filed_elsewhere(publishers, rows):
    """Every name the corpus records as a publisher or an imprint, from the two places it does.

    `publishers` is data/names/publishers.yaml's own set. `rows` are the series rows, whose print
    editions carry the publisher and the imprint each volume was issued under.
    """
    out = set(publishers or ())
    for row in rows or ():
        for pr in (row.get("print") or ()):
            for field in ("publisher", "imprint"):
                v = str(pr.get(field) or "").strip()
                if v:
                    out.add(v)
    return out


def main(argv=None):
    import argparse

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", default="data/names/authors.yaml")
    ap.add_argument("--apply", action="store_true", help="write the marks back to the store")
    a = ap.parse_args(argv)

    path = pathlib.Path(a.store)
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get("names") or {}
    changed = sweep(names)
    counts = {}
    for name, got in sorted(changed.items()):
        counts[got] = counts.get(got, 0) + 1
        print(f"  {got:10} {name}")
    print(f"{len(changed)} credit(s) marked: "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if a.apply and changed:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        print(f"written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
