#!/usr/bin/env python3
"""A publication date for a shop's row that states no ISBN, from the national bibliography.

WHY THIS EXISTS. BOOK☆WALKER sells files and states no ISBN on any of the 5,908 volumes read from
it, so `madb/isbn_dates.py` and openBD both answer nothing about its shelf however complete they
are. 89 of the undated rows nevertheless sit on imprints that print books: 百合姫コミックス,
まんがタイムKRコミックス, ＦＵＺコミックス, ZERO-SUMコミックス and a tail. A commercial imprint
publishes a dated volume with an ISBN, so a date exists and the only difficulty is that the shop
does not hold the number that would find it.

WHY A TITLE MATCH IS ALLOWED HERE AND REFUSED IN `isbn_dates.py`. That module's rule is right and
this does not break it: a title identifies nothing on its own, and `ndl.py` records `citrus+`
returning an unrelated 2007 book on a bare title search. The join here is not title alone. It is
the rule `identity.py` already applies to a serialisation and its book run, and `extract.agrees`
to a volume and its series: **a title match proposes, and at least one person's name must agree
before anything is recorded.** Everything else goes to a review file with its evidence.

THE CASE THAT PROVES IT, met on the first run. 一迅社's `Memories` by 菅野マナミ matches two
records: 大友克洋's MEMORIES from 講談社 and a 1991 大陸書房 book by つづき春. The folded titles are
identical and neither person agrees, so both are refused. A rule that took the publisher or the
earliest date instead would have dated a 2020s 百合姫 volume to 1991.

WHAT AN EDITION MARKER DOES, AND WHY 小冊子 IS NOT ONE. `identity.fold` strips bracketed matter,
so 女子校だからセーフ【単話版】 folds onto 女子校だからセーフ and matches the tankōbon. That is
right: the bracket names the EDITION the shop sells, and the work is the same work. 小冊子 is not
bracketed and does not fold away, so 『citrus』小冊子 does not match citrus, which is also right,
because a booklet given away with a volume is a different publication rather than another edition
of the same one.

WHICH DATE IS TAKEN. The earliest across every agreeing record, which is a first publication and
not the edition the shop happens to sell. 星川銀座四丁目 is on BOOK☆WALKER as KADOKAWA's 2017 MFC
reissue and the bibliography holds 芳文社's 2010 original, so the work is dated 2010-08.

WHAT IT IS STILL NOT. The first publication of a serialised work, which was in a magazine that
MADB's 単行本 dataset does not cover. The basis says so, in the words `bookwalker_volumes.py`
already uses for the same silence.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import extract                                                                 # noqa: E402
import identity                                                                # noqa: E402
import isbn as _isbn                                                           # noqa: E402
from names.inputs import split_authors                                         # noqa: E402

# What a stored answer says it rests on, in the vocabulary `cmoa_volumes.PREFERENCE` and
# `openbd/enrich.py` already use for the bibliography's answer. The suffix is the whole of the
# difference: an ISBN identifies the edition and a title plus a person identifies the work.
BASIS = "madb-tankobon-title-match"

# A run that matches almost nothing has read a truncated dataset or lost a field, rather than
# meeting a shelf of unpublished books, and the two look identical from here. 57 of the 1,209
# undated rows joined at release 1.2.18. The floor is set well under that because the population
# shrinks as rows are dated and the last run over it will legitimately match few.
MIN_MATCHES = 5


def people(names):
    """The comparison keys for the shop's credit string.

    `split_authors` splits it, because the shop writes `冬芽沙也 / 中村 朱里` and that module is
    already the project's reader of a credit line. The key is `extract.norm` because that is the
    form `credits` below puts the bibliography's side in, and one form for one comparison is the
    whole point (STANDING-INSTRUCTIONS §3).
    """
    out = set()
    for name, _reading in split_authors(names or ""):
        # The shop writes a role in brackets after a name: `のん(キャラクターデザイン)`.
        bare = extract.norm(re.sub(r"[（(][^）)]*[）)]\s*$", "", name).strip())
        if bare:
            out.add(bare)
    return out


# HOW A CATALOGUE AND A SHOP WRITE THE SAME TITLE DIFFERENTLY. Each of these is a form one side
# uses and the other does not, and each was read off a real pair before it was written down. A
# title is matched under every form it can take, so neither side has to have written it the same
# way, and `identity.fold` still does the width, spacing and punctuation.
#
#   = parallel title   MADB follows ISBD and prints the publisher's own English title after ` = `:
#                      `OLと人魚 = The OL and the Mermaid`, `おやすみシェヘラザード = Nighty
#                      night,Sheherazade`. The shop prints the Japanese alone.
#   ～subtitle～        The shop keeps the marketing subtitle the catalogue drops: the shelf has
#                      `Killer Twinkle～アンチはステージに上がれません～` and MADB `Killer Twinkle`.
#                      It also covers an edition marker written the same way, `～改訂版～`.
#   短編集 / 作品集     A collection is titled `ロンリーガールに花束を 樫風短編集` on the shelf and
#                      `ロンリーガールに花束を` in the catalogue, and the other way round for
#                      `元カノに幻想を抱くなバーカ : 西沢5ミリ短編集`. Both sides are tried.
#
# WHAT IS DELIBERATELY NOT HERE, and it is the counter-case that keeps the rest honest. 小冊子 is
# not stripped. A booklet given away with a volume is a different publication from the volume, so
# `ゆるゆり　小冊子` must not join `ゆるゆり`, and a rule that cut any trailing word would.
PARALLEL_TITLE = re.compile(r"\s=\s.*$")
SHOP_SUBTITLE = re.compile(r"[～〜~][^～〜~]*[～〜~]\s*$")
COLLECTION = re.compile(r"[^\s　]*(?:短編集|作品集)\s*$")


def keys(title):
    """Every folded form one title can be looked up under."""
    stripped = COLLECTION.sub("", SHOP_SUBTITLE.sub("", PARALLEL_TITLE.sub("", title or "")))
    forms = (title, PARALLEL_TITLE.sub("", title or ""), SHOP_SUBTITLE.sub("", title or ""),
             COLLECTION.sub("", title or ""), stripped)
    return {k for k in (identity.match_key(f) for f in forms) if k}


def credits(record):
    """Every person a bibliography record names, read for a join across two catalogues.

    WHY THIS IS NOT `extract.people`, WHICH ANSWERS ALMOST THE SAME QUESTION. That function reads
    `flat`, which joins MADB's `["トクヲツム", {"@value": "トクヲツム", "@language": "ja-hrkt"}]`
    into one string, and then drops any all-katakana part as the reading of the name before it.
    That rule is right for what it does and it costs a katakana PEN NAME, which this shelf is full
    of: トクヲツム, ヨドカワ and ポルリン were all read as naming nobody, and a record naming
    nobody agrees with nothing.

    So the reading is removed by taking `primary` rather than by recognising it afterwards, and
    the role parser is `extract.strip_role`, shared with `people` so the two cannot disagree about
    what a role looks like.

    WHY THE LOOSER RULE IS SAFE HERE AND WOULD NOT BE THERE. `extract.agrees` is choosing which
    volumes belong to one work inside a single catalogue, where a wrong yes merges two works. This
    asks whether an exact folded title match across two catalogues is the same book, so a name
    read here can only ever confirm a title that has already matched.
    """
    raw = extract.primary(record.get("schema:creator", ""))
    return {extract.norm(extract.strip_role(part))
            for part in re.split(r"\s*/\s*", raw) if extract.strip_role(part)}


def undated(record):
    """Whether a BOOK☆WALKER work record still has no publication date of any kind.

    Read off the volumes rather than off `date_basis`, because the basis says WHY a row is undated
    and this asks WHETHER it is. A record that gains a date keeps its basis field, and a reader
    that went by the basis would keep offering the row for ever.
    """
    return not any(v.get("published") for v in (record.get("volumes") or []))


def dated_volumes(records):
    """`(date, isbn)` for every bibliography record that states both, earliest first."""
    out = []
    for r in records:
        date = extract.flat(r.get("schema:datePublished", "")).strip()
        number = _isbn.isbn13(extract.flat(r.get("schema:isbn", "")))
        if date and number:
            out.append((date, number))
    return sorted(out)


def agreeing(row, records):
    """The bibliography records that agree with this row on at least one person's name.

    A record naming nobody agrees with nothing. MADB leaves `schema:creator` empty on some older
    imports, and treating an empty set as agreement would turn the rule into a title match, which
    is the rule this module exists to avoid being.
    """
    ours = people(row.get("creator"))
    if not ours:
        return []
    return [r for r in records if credits(r) & ours]


def answer(row, records):
    """`(date, isbn, matched)` for one row, or None where nothing agrees.

    `matched` is the evidence: how many records shared the title, how many agreed on a person, and
    which record supplied the date. A stored join that does not carry what convinced it cannot be
    audited and cannot be withdrawn on better evidence (DEFINITIONS §5).
    """
    fit = agreeing(row, records)
    dates = dated_volumes(fit)
    if not dates:
        return None
    date, number = dates[0]
    return date, number, {"titles_matched": len(records), "people_agreed": len(fit),
                          "volumes_dated": len(dates), "isbn": number}


def index(records):
    """Bibliography records grouped under every folded form of their title."""
    out = {}
    for r in records:
        name = extract.primary(r.get("schema:name", ""))
        for key in keys(name):
            out.setdefault(key, []).append(r)
    return out


def match(rows, by_title):
    """`(answers, review)` over every row, where `answers` are joins the person rule accepted.

    A row whose title matched and whose people did not is NOT silently dropped. It goes to
    `review` with the count of what matched, because a shop and a bibliography disagreeing about
    who drew a book is a lead about one of them rather than an absence of evidence.
    """
    answers, review = {}, []
    for row in rows:
        title = (row.get("title") or {}).get("ja") or ""
        # One record can sit under several of a row's forms, and a record counted twice would
        # report the evidence as twice what it is.
        found = {}
        for key in keys(title):
            for r in by_title.get(key, []):
                found[id(r)] = r
        records = list(found.values())
        if not records:
            continue
        got = answer(row, records)
        if got:
            date, number, matched = got
            answers[row["work_id"]] = {"date": date, "isbn": number, "matched": matched}
        else:
            review.append({"work_id": row["work_id"], "title": title,
                           "creator": row.get("creator"), "publisher": row.get("publisher"),
                           "titles_matched": len(records),
                           "people_agreed": len(agreeing(row, records)),
                           "bibliography_names": sorted(
                               {extract.primary(r.get("schema:creator", "")) for r in records}),
                           "why": ("no person agreed" if not agreeing(row, records)
                                   else "agreed, and no agreeing volume states both a date and "
                                        "an ISBN")})
    return answers, review


HEADER = """\
# A publication date for a BOOK☆WALKER row, from the national bibliography, joined on the title
# and on a person's name. NOT a record of the shop's edition: see adapters/madb/by_title.py for
# why a title match alone is refused and what the join had to agree on before this was written.
"""


def render(work_id, got, tag, retrieved):
    """One enrichment record, as YAML."""
    m = got["matched"]
    return HEADER + "\n".join([
        "source: madb-title",
        f"retrieved: {retrieved}",
        f"work_id: {extract.yaml_str(work_id)}",
        "record_type: volume_enrichment",
        f"madb_release: {extract.yaml_str(tag)}",
        "volumes:",
        f"  - isbn: {extract.yaml_str(got['isbn'])}",
        f"    published: {got['date']}",
        f"    published_basis: {BASIS}",
        "    matched:",
        f"      titles_matched: {m['titles_matched']}",
        f"      people_agreed: {m['people_agreed']}",
        f"      volumes_dated: {m['volumes_dated']}",
        "      rule: >-",
        "        The folded title matched and at least one person's name agreed. The date is the",
        "        earliest across every agreeing volume, so a work reissued under a second imprint",
        "        is dated from its first edition rather than from the one the shop sells.",
        "",
    ])


def main(argv=None):
    import argparse
    import datetime
    import json

    import yaml

    from madb import isbn_dates

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a pinned MADB release directory")
    ap.add_argument("--tag", required=True, help="MADB release tag, recorded in every record")
    ap.add_argument("--works", default="data/source/bookwalker")
    ap.add_argument("--out", default="data/source/madb-title")
    ap.add_argument("--review", default="data/queue/madb-title-review.yaml")
    ap.add_argument("--retrieved", default=datetime.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    rows = [yaml.safe_load(p.read_text()) for p in sorted(pathlib.Path(a.works).glob("*.yaml"))]
    todo = [r for r in rows if r and undated(r)]
    print(f"{len(todo)} of {len(rows)} {pathlib.Path(a.works).name} rows have no date")

    records = list(isbn_dates.records(pathlib.Path(a.cache) / isbn_dates.VOLUMES))
    print(f"{len(records)} 単行本 record(s) in {a.tag}")
    answers, review = match(todo, index(records))
    print(f"HEALTH: {len(answers)} row(s) joined on a title and a person, "
          f"{len(review)} matched a title and no person")
    if len(answers) < MIN_MATCHES:
        print(f"Refusing to write: {len(answers)} join(s), under the {MIN_MATCHES} a healthy run "
              "makes. That is a truncated dataset or a changed field rather than a shelf of "
              "unpublished books, and the two look identical from here.")
        return 1
    if a.dry_run:
        for wid, got in sorted(answers.items()):
            print(f"  {wid}: {got['date']} {got['isbn']}")
        return 0

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for wid, got in sorted(answers.items()):
        (out / f"{wid}.yaml").write_text(render(wid, got, a.tag, a.retrieved))
    rp = pathlib.Path(a.review)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(
        "# Rows whose title matched a 単行本 record and whose people did not. NOT RECORDS.\n"
        "#\n"
        "# A shop and the national bibliography disagreeing about who drew a book is a lead about\n"
        "# one of them. The commonest cause here is the bibliography naming nobody on an older\n"
        "# import, and the second is an anthology, which has no single author to agree on.\n"
        "source: madb-title\n"
        f"retrieved: {a.retrieved}\n"
        "role: title-matches-refused\n"
        f"refused: {len(review)}\n"
        "works:\n"
        + "".join(f"  - {json.dumps(r, ensure_ascii=False)}\n" for r in
                 sorted(review, key=lambda r: r["work_id"])))
    print(f"{len(answers)} enrichment record(s) -> {a.out}; {len(review)} refused -> {a.review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
