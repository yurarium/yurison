#!/usr/bin/env python3
"""Assemble the thin-evidence review queue: 296 candidates, what was read, and what each said.

WHAT THIS PRODUCES AND WHAT IT DOES NOT. `data/queue/thin-evidence-review.yaml`, a REVIEW QUEUE.
Nothing leaves the corpus on its say-so: DEFINITIONS §2 admission stands until the project owner
rebuts it, and a takedown is a different thing again (REQUIREMENTS §4). Every row records what was
looked at and what it said, INCLUDING the rows that came back sound, because a work examined and
found solid is the record that stops it being re-examined forever.

THE FILE'S CONSUMER, named here because a register nothing reads is worse than none
(STANDING-INSTRUCTIONS §13). It is read by the project owner, who decides. `--check` re-derives the
population from today's corpus and reports where the written file and the corpus disagree, so the
queue going stale is visible rather than assumed. It deliberately does NOT use the key `candidates`,
which build.py globs data/queue/ for: these works are already in the database, and putting them on
a discovery surface would state a fact about us in front of a reader (§6).

THE ORDER OF WORK. `--plan` writes the list of pages worth reading, `sources.py` reads them, and
`--write` folds the answers in. Splitting it that way is what lets the parsers be tested offline
(STANDING-INSTRUCTIONS §12) and what makes a second run cost nothing when the cache is warm.

WHAT COUNTS AS A CONTRADICTION, and it is deliberately narrow. The admitting shop's own work page
no longer files the work on the shelf that admitted it. That is the comparator withdrawing the
claim §2 admitted the work on, stated by the only party entitled to withdraw it, and it needs no
judgement about the manga from anybody. Everything else found here is recorded and ranked and left
for the owner, per DEFINITIONS §7: designation, never judgement.

A PLATFORM'S FILING IS RECORDED AND DOES NOT SET THE VERDICT. Where カドコミ files a shelf-admitted
work as 少女 / ラブコメ / 女装 and applies neither 百合 nor GL, that is the publisher's own web arm
speaking and it belongs in the record. It is not a rebuttal on its own: 115 of the 372 corpus works
that platform hosts sit outside its yuri tags, so its silence is common enough to prove nothing by
itself. What it does is decide reading order.

Usage:
  review.py --plan pages.json
  sources.py --plan pages.json --cache $YURI_CACHE/shop-reading-cache --out said.json
  review.py --write data/queue/thin-evidence-review.yaml --read said.json --retrieved 2026-08-07
  review.py --check data/queue/thin-evidence-review.yaml
"""
import argparse
import collections
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import captures  # noqa: E402
import textnorm  # noqa: E402
from names import inputs  # noqa: E402
from thin import evidence as E  # noqa: E402
from thin import sources  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERIES = ROOT / "data/build/series.json"
ANTENNA = ROOT / "data/coverage/webcomics-works.yaml"
KADOKOMI = ROOT / "data/source/kadokomi/catalogue.yaml"
BW_CAPTURE = ROOT / "data/queue/bookwalker-yuri.yaml"
CMOA_CAPTURE = ROOT / "data/queue/cmoa-yuri.yaml"

BW = "BOOK☆WALKER"
CMOA = "コミックシーモア"


def split(row):
    """The people credited on a row, folded for comparison. inputs.split_authors decides where a
    role label ends; this module does not have a second opinion about that."""
    return [textnorm.norm(n) for n, _ in inputs.split_authors(row.get("author") or "")]


def key(title):
    return textnorm.norm(title or "")


def bare(title):
    """A title with its bracketed decorations and its Latin gloss removed.

    コミックシーモア prints 抱かれたい女 where the bibliography holds
    `抱かれたい女(ひと) = person who wants to be embraced : JDだけど…`, so an exact match finds 53 of
    the 75 and this finds 64. The 11 it still misses are recorded as unmatched rather than guessed
    at: a wrong shop row would attribute one work's filing to another.
    """
    import re
    t = re.sub(r"\s*[=:：]\s*[A-Za-z].*$", "", title or "")
    t = re.sub(r"【[^】]*】|\([^)]*\)|（[^）]*）", "", t)
    return textnorm.norm(t)


def load():
    """Everything the assembly reads. Returns a context dict; no network."""
    rows = json.loads(SERIES.read_text(encoding="utf-8"))["series"]
    antenna = {key(c["title"]) for c in (yaml.safe_load(ANTENNA.read_text())["candidates"])}
    cat = yaml.safe_load(KADOKOMI.read_text())
    tagged = {w["code"] for w in cat["works"]}
    bw = captures.load(BW_CAPTURE)
    cmoa = captures.load(CMOA_CAPTURE)
    facets = {it["id"]: it for it in (bw.get("items") or [])}
    shop = {}
    for t in (cmoa.get("titles") or []):
        shop.setdefault(key(t["title"]), t)
        shop.setdefault(bare(t["title"]), t)
    return {"rows": rows, "antenna": antenna, "tagged": tagged, "facets": facets,
            "cmoa_by_title": shop, "kadokomi_retrieved": str(cat.get("retrieved")),
            "index": E.author_index(rows, split)}


def shop_row(row, ctx):
    """The shop's own capture row for this work, and the id it is known by there."""
    shelf = E.evidence(row)[0]["source"]
    if shelf == BW:
        for p in (row.get("print") or []):
            wid = p.get("work_id") or ""
            if wid.startswith("bw-") and wid[3:] in ctx["facets"]:
                return ctx["facets"][wid[3:]]
        return None
    return ctx["cmoa_by_title"].get(key(row["work"])) or ctx["cmoa_by_title"].get(bare(row["work"]))


def plan(ctx, read=None, pages=None):
    """Which pages are worth reading, one entry per (work, page).

    Two rounds, and the second exists because the first was wrong. Called with no `read` it plans
    every candidate's own page at the shop that admitted it, plus the publisher's カドコミ page where
    the work is serialised there. EVERY candidate is planned, not a selected few: reading only the
    suspicious ones would make the answer depend on the ranking it is supposed to test.

    Called with the first round's answers it plans the VOLUME pages of any BOOK☆WALKER series whose
    series page came back without the tag. BOOK☆WALKER files its genres per volume, so a series
    page is a partial view and 霧尾ファンクラブ proves it: no tag on the series page, no tag on volume
    one, 百合 on volume two. `pages` is {url: html} for the series pages already fetched.
    """
    if read:
        return _volume_plan(read, pages or {})
    out = []
    for row in E.candidates(ctx["rows"]):
        wid = row["id"]
        shelf = E.evidence(row)[0]["source"]
        got = shop_row(row, ctx)
        if got and shelf == BW:
            out.append({"work": wid, "kind": "bookwalker", "url": got["url"]})
        elif got and shelf == CMOA:
            out.append({"work": wid, "kind": "cmoa", "url": got["url"]})
        for code in E.platform_codes(row, "カドコミ"):
            out.append({"work": wid, "kind": "kadokomi",
                        "url": f"https://comic-walker.com/detail/{code}"})
    return out


def _volume_plan(read, pages):
    out = []
    for wid, entries in read.items():
        for e in entries:
            if e["kind"] != "bookwalker" or (e.get("said") or {}).get("shelved") is not False:
                continue
            if "/series/" not in e["url"]:
                continue          # a volume page that lacks the tag is already the shop's answer
            for url in sources.volume_pages(pages.get(e["url"], "")):
                out.append({"work": wid, "kind": "bookwalker", "url": url})
    return out


def _said(entry, shelf):
    """Our own sentence for what one page stated. Never the publisher's words (REQUIREMENTS §2)."""
    s = entry.get("said")
    if not s:
        return f"not read: HTTP {entry.get('status')}" + (f" ({entry['error']})"
                                                          if entry.get("error") else "")
    if entry["kind"] == "bookwalker":
        what = "the series page" if "/series/" in entry["url"] else "this volume"
        if s["shelved"] is None:
            return f"{what} carried no genre tags at all, so it states nothing"
        # An unnamed tag is dropped from the sentence. bookwalker.tags returns whatever the page
        # put in the anchor and some carry no text, which reads as a stray 、 in front of the list.
        names = "、".join(n for n in s["tags"].values() if n)
        return (f"{what} is filed under {names}"
                + (f", tag 14 ({shelf}) among them" if s["shelved"]
                   else ", and not under tag 14, the shelf that admitted it"))
    if entry["kind"] == "cmoa":
        if s["shelved"] is None:
            return "the page states no genre, so it states nothing"
        crumb = " > ".join(x for x in (s.get("crumbs") or [])[1:-1] if x)
        who = "、".join(s.get("authors") or [])
        return (f"the shop files it under {s.get('genre') or crumb.split(' > ')[0]}"
                + (f" ({crumb})" if crumb else "")
                + (f", crediting {who}" if who else "")
                + (", genre 37 (百合・GL) among its genres" if s["shelved"]
                   else ", and no longer under genre 37 (百合・GL), the shelf that admitted it"))
    if entry["kind"] == "kadokomi":
        tags = "、".join(s.get("tags") or []) or "no tags"
        return (f"the publisher's own platform files it as {s.get('genre')}"
                + (f" / {s['sub_genre']}" if s.get("sub_genre") else "")
                + f" and applies {tags}"
                + (", 百合 or GL among them" if s.get("yuri_tagged")
                   else ", applying neither 百合 nor GL"))
    return "read"


def readings(paths):
    """Every round's answers, merged into {work: [pages]}, in the order the rounds ran."""
    out = collections.defaultdict(list)
    for p in paths or ():
        for wid, entries in json.loads(pathlib.Path(p).read_text(encoding="utf-8")).items():
            out[wid].extend(entries)
    return dict(out)


def contradicted(entries):
    """Whether the admitting shop has stopped filing the work on the shelf that admitted it.

    ONE PAGE CARRYING THE SHELF CLEARS THE WORK, whatever the others say, because BOOK☆WALKER tags
    volumes rather than works: 霧尾ファンクラブ's series page and its first volume carry no 百合 and
    its second volume does, and the work is plainly yuri. So the question is whether ANY page the
    shop serves for this work still carries it, and only a run of noes is an answer.
    """
    shop = [e for e in entries if e["kind"] in ("bookwalker", "cmoa")]
    said = [(e.get("said") or {}).get("shelved") for e in shop]
    return bool(said) and True not in said and False in said


def rows_for(ctx, read, retrieved):
    """One review row per candidate, ranked, strongest suspicion first."""
    out = []
    for row in E.candidates(ctx["rows"]):
        wid = row["id"]
        ev = E.evidence(row)[0]
        got = shop_row(row, ctx)
        sig = E.signals(row, key=key(row["work"]), antenna=ctx["antenna"],
                        tagged=ctx["tagged"], index=ctx["index"], split=split, facets=got)
        entries = read.get(wid) or []
        contra = contradicted(entries)
        platform_silent = any(e["kind"] == "kadokomi" and (e.get("said") or {})
                              and not e["said"].get("yuri_tagged") for e in entries)
        out.append({
            "work": wid,
            "title": row["work"],
            "imprint": (E.imprints(row) or [None])[0],
            "publisher": (row.get("print") or [{}])[0].get("publisher") or None,
            "shelf": {"comparator": ev["source"], "term": ev["term"], "retrieved": ev["read"]},
            "verdict": E.verdict(sig, contradicted=contra),
            "suspicion": E.suspicion(sig) + (5 if contra else 0) + (1 if platform_silent else 0),
            "signals": {k: v for k, v in sig.items() if v},
            "read": [{"source": {"bookwalker": BW, "cmoa": CMOA,
                                 "kadokomi": "カドコミ"}[e["kind"]],
                      "url": e["url"], "retrieved": retrieved,
                      "said": _said(e, ev["term"])} for e in entries],
        })
        if not entries:
            out[-1]["read"] = []
            out[-1]["unread"] = ("the shop's own row for this work was not re-identified from the "
                                 "capture, so its page was not read")
    out.sort(key=lambda r: (-r["suspicion"], r["work"]))
    return out


def summary(rows):
    """The counts a reader needs before believing any single row."""
    sig = collections.Counter(k for r in rows for k in r["signals"])
    return {"works": len(rows),
            "verdicts": dict(collections.Counter(r["verdict"] for r in rows)),
            "signals": dict(sig),
            "unread": sum(1 for r in rows if r.get("unread"))}


HEADER = """\
# THIN-EVIDENCE REVIEW QUEUE. Works whose only support is one retailer's yuri shelf, examined.
# NOT AN EVICTION LIST. Nothing here has left the corpus and nothing here may leave it on this
# file's say-so. DEFINITIONS §2 admits a work on a licensed retailer's yuri shelf as presumptive
# and rebuttable, and the rebuttal is the project owner's to make. A takedown is a different thing
# again (REQUIREMENTS §4).
#
# WHY THE POPULATION IS THIS ONE. 1,837 of 3,076 works rest on a shelf and nothing else, which is
# most of the database, and §2's `rebuttable` had no mechanism behind it. The operator found one
# entry that does not belong and one query that narrows without knowing the answer first: a yuri
# line contributes dozens of works, so an imprint contributing one or two, on a single shelf row,
# has nothing supporting it. That returns the 296 rows below. `adapters/thin/evidence.py` holds
# the query and reproduces it exactly.
#
# WHAT A VERDICT MEANS.
#   contradicted   Not one page the admitting shop serves for this work still files it on the shelf
#                  that admitted it. The comparator has withdrawn its own claim, which is the one
#                  form of rebuttal that needs no judgement about the manga from anybody.
#   corroborated   A source other than that shelf designates the work: the publisher's own title
#                  or imprint carries the word, or Web漫画アンテナ's 百合 tag names it.
#   unsupported    Nothing found either way. NOT a fault and NOT a suspicion. Most of the shelf is
#                  accurate and most of these rows are expected to be sound; what this records is
#                  that somebody looked, so nobody looks again from nothing.
#
# DESIGNATION, NEVER JUDGEMENT (§7). No row here asks whether a work IS yuri. Each asks whether any
# source designates it so and whether anything a source says contradicts the one shelf that does.
# Where sources conflict, both are written and the conflict is left standing.
#
# WHAT WAS READ. Every candidate's own page at the shop that admitted it, plus the publisher's own
# カドコミ page where the work is serialised there. `said` is OUR paraphrase of the source's own
# structured fields. Publisher synopsis was read during the pass and is stored nowhere
# (REQUIREMENTS §2, §4).
#
# BOOK☆WALKER TAGS A VOLUME, NOT A WORK, and that is what makes this file's numbers what they are.
# Reading series pages alone put 22 works here as contradicted. Reading the volumes each of those
# pages links leaves 3. 霧尾ファンクラブ is why: its series page carries 女性向け and 女性マンガ, volume 1
# carries those plus 学園, and volume 2 carries 百合. The work is unmistakably yuri and a series page
# would have called it rebutted. So a work counts as contradicted only when the tag is on none of
# the pages reached, and a series page lists between 2 and 13 of its volumes rather than all of
# them, so even that is a finding about the volumes reached.
#
# 11 ROWS WERE NOT RE-READ. Their コミックシーモア row could not be re-identified from the capture by
# title, and guessing a shop row would attribute one work's filing to another. They carry `unread`
# and whatever structural signals the corpus holds.
#
# SIGNALS THAT DID NOT DISCRIMINATE, recorded so they are not re-derived. BOOK☆WALKER's 男性向け
# facet is on 46% of the whole shelf and 37% of these rows, and is FALSE on the one work known not
# to belong. Which listing a row came from separates nothing: all 221 BOOK☆WALKER rows here came
# from the volume store. Cross-retailer agreement was measured by the operator beforehand: 20 works
# appear on both shelves, so absence from the other carries no information. コミックシーモア's own
# re-reading corroborated 64 of the 64 rows it could reach, so for that shop the recheck is a
# record rather than a discriminator.
#
# `hand_findings` HOLDS WHAT NO RULE HERE CATCHES. Scope and content questions a person noticed
# while reading, each with the page that raised it. They are not verdicts about the shelf and they
# are not evidence about anything until somebody follows them up.
#
# `reviews`, NOT `candidates`. build.py globs data/queue/ for the key `candidates` and treats what
# it finds as a discovery queue. These works are already in the database, so listing them there
# would put a fact about our own confidence in front of a reader (STANDING-INSTRUCTIONS §6).
"""


# WHAT A PERSON NOTICED THAT NO RULE HERE CATCHES. Each is a scope or content question rather than
# a designation one, so none of them belongs in a verdict about the shelf, and writing a rule for
# any single one would be fitting the rule to the case. They are recorded with their source so the
# lead is not lost, which is what a queue is for.
HAND_FINDINGS = [
    {"work": "w01338", "title": "サンストーン", "question": "scope, DEFINITIONS §6",
     "source": "コミックシーモア", "url": "https://www.cmoa.jp/title/182054/", "retrieved": "2026-08-07",
     "note": ("The shop credits ステファン・セジク and 上田香子, which is a foreign author and a Japanese "
              "translator. A Japanese edition that is a translation of a non-Japanese original is "
              "out of scope whatever shelf it sits on, and this is the shop stating it. Confirm "
              "against 誠文堂新光社 before acting.")},
    {"work": "w01456", "title": "Roaming", "question": "scope, DEFINITIONS §6",
     "source": "コミックシーモア", "url": "https://www.cmoa.jp/title/302784/", "retrieved": "2026-08-07",
     "note": ("Credited to マリコ・タマキ, ジリアンタマキ and 金原瑞人, the last of whom is a translator. "
              "Same question as サンストーン and the same next step, at トゥーヴァージンズ.")},
    {"works": ["w02348", "w02333"], "title": "ON a LEASH / 落差", "question": "scope, DEFINITIONS §6",
     "source": "BOOK☆WALKER", "url": "https://bookwalker.jp/series/526523/",
     "retrieved": "2026-08-07",
     "note": ("Both are SNP under the NETCOMICS imprint, 94 and 68 volumes of per-chapter releases, "
              "and BOOK☆WALKER still tags both 百合. NETCOMICS publishes Korean webtoons, so the "
              "scope question is live and nothing read here answers it. The shop names no origin "
              "and no translator, so this needs the publisher.")},
    {"work": "w03057", "title": "見てはいけない 淫情の懺悔", "question": "content, DEFINITIONS §7",
     "source": "BOOK☆WALKER", "url": "https://bookwalker.jp/dee636799f-b437-478f-8b11-34d0caa8c3db/",
     "retrieved": "2026-08-07",
     "note": ("Imprint BLIC-ERO, and the shop tags it 百合, 萌え and おとなマンガ. §7 excludes on a "
              "成年コミックマーク, an 18禁 designation, an adult imprint or adult-only distribution, and "
              "BOOK☆WALKER keeps its R18 stock on a separate store, so this shelf is all-ages and "
              "the work is admitted. Whether it wants `explicit_content` is the open question.")},
    {"works": ["w02706", "w01728", "w01604", "w01578"],
     "title": "コミック百合姫 / まんがタイムきららＭＡＸ / ちゃおデラックスホラー / 百合姫表紙集",
     "question": "the row is not a work",
     "source": "BOOK☆WALKER", "url": "https://bookwalker.jp/series/192567/",
     "retrieved": "2026-08-07",
     "note": ("Three magazines and a cover-art collection, carried as works, the first with 119 "
              "'volumes'. DEFINITIONS §2 has nothing to say about them because the question is not "
              "whether they are yuri. They inflate the corpus count and one of them, "
              "まんがタイムきららＭＡＸ, is among the three the shop no longer shelves.")},
]


def write(path, ctx, read, retrieved):
    rows = rows_for(ctx, read, retrieved)
    doc = {
        "source": "yurarium",
        "role": "review-queue",
        "record_type": "shelf_rebuttal_review",
        "generated": retrieved,
        "query": ("evidence is exactly one retailer shelf row, and the work's imprint appears on "
                  "no more than two shelf-only works, or it names no imprint at all"),
        "query_module": "adapters/thin/evidence.py",
        "summary": summary(rows),
        "hand_findings": HAND_FINDINGS,
        "reviews": rows,
    }
    path = pathlib.Path(path)
    path.write_text(HEADER + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False,
                                            default_flow_style=False, width=100),
                    encoding="utf-8")
    return rows


def check(path, ctx):
    """Where the written queue and today's corpus disagree. Prints, returns a count."""
    doc = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8")) or {}
    written = {r["work"] for r in (doc.get("reviews") or [])}
    now = {r["id"] for r in E.candidates(ctx["rows"])}
    gone, fresh = sorted(written - now), sorted(now - written)
    for w in gone:
        print(f"  reviewed, no longer a thin-evidence candidate: {w}")
    for w in fresh:
        print(f"  a thin-evidence candidate with no review row: {w}")
    print(f"{len(written)} reviewed, {len(now)} in the corpus today, "
          f"{len(gone) + len(fresh)} disagreement(s)")
    return len(gone) + len(fresh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", help="write the list of pages to read, as JSON")
    ap.add_argument("--write", help="write the review queue to this path")
    ap.add_argument("--read", nargs="+", default=[],
                    help="the JSON sources.py produced, one file per round")
    ap.add_argument("--cache", help="with --plan --read: where the first round's pages were saved")
    ap.add_argument("--check", help="compare a written queue against today's corpus")
    ap.add_argument("--retrieved", default="")
    a = ap.parse_args(argv)
    ctx = load()
    read = readings(a.read)
    if a.plan:
        # Round two reads volumes off series pages the first round already fetched, so it takes
        # them out of the cache rather than asking the shop for them again.
        held = {}
        if read and a.cache:
            import net
            for entries in read.values():
                for e in entries:
                    if e["kind"] == "bookwalker" and "/series/" in e["url"]:
                        held[e["url"]] = net.fetch(e["url"], a.cache, max_age_days=3650).text or ""
        pages = plan(ctx, read=read, pages=held)
        pathlib.Path(a.plan).write_text(json.dumps(pages, ensure_ascii=False, indent=1))
        print(f"{len(pages)} pages to read -> {a.plan}")
        return 0
    if a.write:
        rows = write(a.write, ctx, read, a.retrieved)
        print(f"{len(rows)} reviewed -> {a.write}")
        print(json.dumps(summary(rows), ensure_ascii=False))
    if a.check:
        return 1 if check(a.check, ctx) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
