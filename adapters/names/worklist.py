#!/usr/bin/env python3
"""The queue for choosing an English name, ordered by what can be settled and how.

WHY THIS IS NOT `curate.todo`. That function answers "which works still show a romanisation", most
recently updated first, and it answers it well: the queue for the first two rounds was picked by
hand with the filter "has no `en`", which excluded every work already carrying a machine
romanisation from the pass meant to replace it. What it does not say is what to DO with each row,
and the rows are not one job.

A DAY OF CORRECTIONS SAID WHAT THE JOBS ARE. Nine titles were corrected by the project owner on
2026-08-10 and eight of them had the same shape: something already stated the answer and nothing had
looked. The publisher's tagline said 勇者 while the reading said ユウモノ. A title's own dashes said
がらんのひめ and were romanised as more title. A work's lead art printed `Destiny` while the record
carried a misspelling invented here. A cover printed `A hundred scenes of Girls Love`. An entry's own
note said 언니 while its rendering said `Onni`, and another said "a maid romance" while rendering
ベーズ as somebody's name rather than as baize.

So the queue is ordered by WHERE THE ANSWER IS LIKELY TO BE, not by recency, and each row says which
route to try. A reviewer who works it in order spends the first hour on titles that need reading and
not deciding.

    ./adapters/names/worklist.py            the queue, grouped
    ./adapters/names/worklist.py --json     the same, for a tool

WHAT IT CANNOT SEE, and it is the reason the routes are suggestions rather than answers: whether a
licensor exists, what a cover prints, and whether a coinage is a coinage. Every one of those needs
somebody to look. This orders the looking.
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from facts import namekey                                              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Edition and status apparatus a publisher bolts onto a title. A row differing from another only by
#: one of these is the same work, so the English attached to the base is the answer and nobody needs
#: to compose one.
TAG = (r"百合|GL|ガールズラブ|完結|新装版|完全版|合本版|分冊版|単話版?|単話売|話売り|電子版|"
       r"電子限定|タテスク|タテヨミ|フルカラー|カラー版|読切版?|試し読み|無料|コミック|同人版")
APPARATUS = re.compile(rf"[【\[]\s*(?:{TAG})[^】\]]*[】\]]|[（(]\s*(?:{TAG}|[A-Za-z][A-Za-z0-9 .!+-]{{1,22}})\s*[)）]")

#: A rendering carrying one of these is English. A romanisation of Japanese carries none of them,
#: which is how a sibling's "answer" is told from a sibling's romanisation.
ENGLISH = re.compile(r"\b(the|a|an|of|and|in|is|my|your|with|to|for|who|that|but|it|she|her|i|we|"
                     r"on|at|from|about|too|not|so|be|have|has|do|does|story|girl|love)\b", re.I)

#: A title already written in Latin letters. `GIRL FRIENDS`, `schadenliebe` and `marriage black`
#: are the work's own name and need no English rendering at all, so a queue that sends somebody to
#: translate them is wasting the one resource this queue exists to spend. Found on the first run of
#: this module, which had 30 of them under `compose`.
ALREADY_LATIN = re.compile(r"^[A-Za-z0-9 .,!?&@:'\-+#/♡×~]+$")

#: A title this short, in kana, is usually a coinage or a name, and a romanisation is the finished
#: answer for those. Kept as a hint and never as a verdict.
COINAGE = re.compile(r"^[ぁ-ゖァ-ヺー0-9!?♡・\s]{1,8}$")

#: A surface written straight through in kana, stating no division of its own.
UNDIVIDED_KANA = re.compile(r"^[ぁ-ゖァ-ヺーゝゞヽヾ]+$")

#: A PARTICLE IS A STATED DIVISION even with no space around it. `レンズのむこう` divides at の and
#: `イヴとイヴ` at と, so `Renzu no Mukō` and `Ivu to Ivu` are right and the first version of the
#: rule below called both of them broken. A particle has to sit between two other kana to count:
#: `のだ` opens with one and is a coinage.
PARTICLE = re.compile(r"[ぁ-ゖァ-ヺー].*?[のとはがをにもでへや].*?[ぁ-ゖァ-ヺー]")


def _bare(title):
    """`title` with edition apparatus removed, folded, so a variant meets its base."""
    s = title
    for _ in range(6):
        s2 = APPARATUS.sub("", s).strip(" 　-–—・:：")
        if s2 == s:
            break
        s = s2
    return namekey.fold(s)


def rows(build="data/build"):
    """Every works-list row still showing a romanisation, with the route most likely to settle it.

    READ OFF THE ROWS A READER SEES, which is `series.json`, and not off the name store. The store
    holds 3,164 titles against 3,046 rows because 226 are edition variants and print-only records
    that are no row at all, so a queue built there sends a reviewer to work that nobody can see.
    `check.inv_a_work_shows_the_english_its_record_holds` is what makes the two agree on the rest.
    """
    at = pathlib.Path(build)
    titles = json.loads((at / "feed" / "names.json").read_text())["titles"]
    series = json.loads((at / "series.json").read_text())["series"]

    answered = {}
    for k, v in titles.items():
        if isinstance(v, dict) and v.get("en"):
            answered.setdefault(_bare(k), (k, v["en"]))

    out = []
    for r in series:
        ja = str(r.get("work") or "")
        # THE ROW'S OWN ANSWER FIRST, because that is what a reader sees. An edition takes its
        # work's English name in the build rather than in the store, so a queue reading only the
        # store keeps sending somebody to eleven rows that are already named.
        row_en = (r.get("work_en") or {})
        if row_en.get("en"):
            continue
        rec = titles.get(ja) or {}
        if (rec.get("basis") or row_en.get("basis")) not in (None, "romaji"):
            continue
        sib = answered.get(_bare(ja))
        shown = ((rec.get("romaji") or {}).get("macron") or "")
        if ALREADY_LATIN.match(ja.strip()):
            route, why = "already-latin", "the work's own name is in Latin letters"
        # A ROMANISATION THAT DIVIDES A SURFACE STATING NO DIVISION. さろめりっく is seven kana
        # written straight through and reaches a reader as `Saro Meri Kku`; the spaces are the
        # analyser's and nobody wrote them. This is not a naming job at all, it is the reading, and
        # sending it to somebody to translate hides a fault behind a queue.
        elif (UNDIVIDED_KANA.match(ja.strip()) and " " in shown.strip()
              and not PARTICLE.search(ja.strip())):
            route, why = "broken-romanisation", ("the surface states no division and the "
                                                 "romanisation invents one; this is a reading fault")
        elif sib and sib[0] != ja and ENGLISH.search(sib[1]):
            route, why = "inherit", f"the same work as {sib[0]}, which is {sib[1]!r}"
        elif sib and sib[0] != ja:
            route, why = "inherit-romaji", f"{sib[0]} carries {sib[1]!r}, itself a romanisation"
        # A PARTICLE MAKES IT A PHRASE AND NOT A COINAGE, whatever its length. `レンズのむこう` is
        # seven kana and means beyond the lens; `イヴとイヴ` is five and is Eve and Eve. Both were
        # filed as coinages to confirm, which is the queue telling a reviewer the job is smaller
        # than it is.
        elif COINAGE.match(ja) and not PARTICLE.search(ja.strip()):
            route, why = "coinage", "short and in kana with no particle, so a romanisation may be the answer"
        else:
            route, why = "compose", "no sibling has a name; look for a licensor, then the work's own art"
        out.append({"id": r.get("id"), "work": ja, "shown": shown, "route": route, "why": why,
                    "publisher": [p.get("publisher") for p in (r.get("print") or [])],
                    "platform": [s.get("platform") for s in (r.get("sources") or [])]})
    return out


#: What each route means, in the order a reviewer should work them.
ROUTES = (
    ("inherit", "A sibling record already holds an English name. Nothing to decide: the apparatus "
                "made a different key and the name never reached this row."),
    ("compose", "Nobody has named it. Look for an English licensor first, then the work's own "
                "cover or lead art, then the publisher's page, and compose only if all of those "
                "are silent. Record which routes were tried."),
    ("inherit-romaji", "A sibling carries a romanisation too. Joining them changes a spelling and "
                       "not a state, so this is consistency work and it comes last."),
    ("coinage", "Short and in kana. A romanisation is often the finished answer here, so the job "
                "is to confirm that rather than to translate."),
    ("broken-romanisation", "The romanisation divides a surface that states no division, so the "
                            "row shows a name nobody wrote. Belongs with the reading work and not "
                            "with naming."),
    ("already-latin", "The work's own name is in Latin letters and no English rendering is owed. "
                      "Here so the count is honest about what is left to do."),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    got = rows(a.build)
    if a.json:
        print(json.dumps(got, ensure_ascii=False, indent=1))
        return 0
    for route, why in ROUTES:
        mine = [g for g in got if g["route"] == route]
        print(f"\n{route}: {len(mine)}\n  {why}")
        for g in mine:
            print(f"    {g['work'][:40]:42} {g['shown'][:32]:34} {g['why'][:60]}")
    print(f"\n{len(got)} row(s) a reader sees without an English name")
    return 0


if __name__ == "__main__":
    sys.exit(main())
