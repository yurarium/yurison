#!/usr/bin/env python3
"""Which record answers for a folded name, where several spellings fold onto one key.

WHY THIS IS A MODULE AND NOT A CLOSURE IN THE BUILD. `feed/names.json` ships ONE entry per folded
name and 112 author spellings fold onto another's key, so something has to choose. build.py chose,
and STORE-PLAN §6 needs the store to know the same answer: an emitter ranking the records again
would be the second implementation §3 counts seven shipped bugs from, and it would be the one that
disagrees. So the rule lives here and both of them ask it.

FULLEST MEANS THE RECORD ANSWERING THE MOST QUESTIONS A READER CAN ASK OF IT. Ranking by field
count rather than by which spelling looks canonical avoids deciding that full-width brackets are
wrong, which they are not; the two spellings are one work and either may be the one a source used.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from facts import division as _division                                 # noqa: E402
from facts import reading as _reading                                   # noqa: E402

#: How much a claim about an English name is worth, highest first. ASKED OF `facts/reading`, which
#: owns which English name wins.
EN_BASIS = _reading.en_ranks()

#: And how much a claim about a READING is worth, same order, same reason. `analyser` and
#: `back-converted` are a machine's answer and sit below every one that came from somewhere.
#: ASKED OF `facts/division`, which owns which reading wins.
READING_BASIS = _division.ranks()


def fullness(rec):
    """How much a name record actually says, for choosing between two that fold together.

    Field count alone was wrong the moment both records had an `en`. 見えてますよ！愛沢さん is
    held twice, and the copy carrying a curated translation lost to one carrying a community
    database's string, because the loser also happened to hold a reading, a ruby split and a set
    of furigana spans. Counting fields measured the wrong thing: what matters first is WHICH
    English name, and only then how much else is attached.

    AND THE SAME FAULT AGAIN ON THE READING, found by `a person is spelled one way`. 春結千晶 is
    held twice, once as itself and once with an ideographic space in it, and the spaced copy holds
    an analyser's `ハル ケツ 　 チアキ` while the plain one holds ハルユウチアキ off the shop that
    sells the artist's books. Neither has an `en`, so both scored zero twice over and the tie went
    to field count, which the analyser's copy wins by carrying the ruby, the spans and the two
    marks saying not to trust it. A reader was shown `Haru Ketsu Chiaki` with a [?] beside it while
    a researched reading of the same person sat in the file.

    So a reading a source states outranks a machine's, on the same order the name store ranks them
    by, and only then does field count decide.
    """
    if not isinstance(rec, dict):
        return (0, 0, 0, 0)
    has_en = 1 if rec.get("en") else 0
    rank = EN_BASIS.get(rec.get("basis"), 0) if has_en else 0
    reading = READING_BASIS.get(rec.get("reading_basis"), 0) if rec.get("reading") else 0
    rest = sum(1 for v in rec.values() if v not in (None, "", [], {}))
    return (has_en, rank, reading, rest)


def fold_map(records, fold):
    """`({folded: record}, [(folded, others), …], {folded: spelling})`, keeping the fullest.

    A dict comprehension here let the last writer win, and the winner depended on iteration order.
    彼氏の女友達がぐいぐい来る(私に) is held twice, once with full-width brackets and once without,
    and the copy that arrived second carried no English name: a curated translation was written to
    the store, applied cleanly, and then silently dropped on the way to the page. The name was
    absent from the site with nothing anywhere reporting a problem.

    THE THIRD RETURN IS WHOSE ANSWER WON, which the store records as `name_record.renders`. The
    entry a reader is shown has to come from one record: its reading, its English, its marks and
    its citation are one record's account of the name, and assembling them from whichever record
    happened to hold each would ship a name nobody ever wrote down.
    """
    best, lost, chosen = {}, {}, {}
    for k, v in records.items():
        f = fold(k)
        if f in best:
            lost[f] = lost.get(f, 0) + 1
        if f not in best or fullness(v) > fullness(best[f]):
            best[f], chosen[f] = v, k
    return best, sorted(lost.items()), chosen
