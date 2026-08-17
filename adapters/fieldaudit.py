#!/usr/bin/env python3
"""A platform that renamed a class returns rows with the field missing, and nothing errors.

WHAT THIS IS FOR. A rendered platform that moves a selector does not fail: the adapter still
returns the right number of well-formed rows, and every one of them is missing the same field. The
build accepts them, the counts look healthy, and the first sign is a reader finding a chapter with
no title on it. GAPS section 8 is the same argument about row counts; this is the argument about
fields.

WHY IT IS A MODULE. It lived inline in `.github/workflows/update.yml`, reading `data/build/feed.json`,
and STORE-PLAN section 13 stopped that file being written: the run died on the audit step, which is
the tripwire refusing to answer rather than a platform losing a field. A rule that decides whether a
day's capture may be published belongs where it can be read and tested, and the workflow keeps the
mechanism.

THE RULES, AND EACH WAS SEPARATED AFTER THE SHAPE BEFORE IT HID SOMETHING.

    per platform    a selector belongs to a platform, so a moved one takes out that platform's rows
    spread          a change to a shared renderer is a few rows everywhere and no platform over its share
    access          a platform stating no access on the route we read it by, which is its own number

    ./adapters/fieldaudit.py            audit the store and exit non-zero on a finding
    ./adapters/fieldaudit.py --quiet    the counts alone
"""
import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

#: A PLATFORM HAS LOST A FIELD WHEN IT HAS LOST MOST OF ITS OWN ROWS. Three is the floor because a
#: platform publishing one or two updates in a window says nothing either way, and half its rows is
#: what tells a moved selector from a work published without a byline.
LOST_FLOOR = 3
LOST_SHARE = 0.5

#: SPREAD ACROSS EVERYTHING, which per-platform counting cannot see. A shared renderer changing
#: shows up as a handful of rows on every platform and none of them over its share.
SPREAD = 25

#: ROWS STATING NO ACCESS AT ALL, counted apart from the two above. マガポケ is read by two routes
#: and `magapoke-feeds.yaml` carries access on none of its chapters while the rendered route carries
#: it on nearly all, so a work reached only by the feed has none.
#:
#: A SHARE AND NOT A COUNT, AFTER A COUNT TRIPPED THREE TIMES IN THREE DAYS AND WAS RIGHT ONCE. It
#: went 25 to 60 to 100 to 80, and each move was the corpus rather than a fault: first three
#: `try_labels` platforms, then those platforms publishing, then a work's backlist arriving in one
#: go. コミックDAYS listed 第39話 to 第46話 of ドリーム☆ジャンボ☆ガール on one day and ＧＵＲＵ
#: eleven chapters on another, both stated `observed` by the platform's own atom feed, which is a
#: real event and not a selector. A number that has to be raised whenever the corpus does something
#: ordinary is measuring the corpus.
#:
#: WHAT THE SHARE IS FOR, now that `access_moved` exists. That rule catches the fault this was
#: written for, a route that stops reading prices, per route and against its own rows. What is left
#: for a ceiling is a drift across everything that no single route shows enough of, so it is asked
#: as a proportion of the attested rows and stays put as the corpus grows. It has run between 4.6
#: and 6.3 per cent across the days above; a tenth is above every one of them and far below a
#: collapse.
NO_ACCESS_SHARE = 0.10

#: AND A FLOOR UNDER IT, because a share of a handful of rows is noise: a run that captured twenty
#: rows and stated access on none of them is a run to look at, and 10 per cent of twenty is two.
NO_ACCESS_FLOOR = 25

#: WHERE A ROUTE READS NO ACCESS AT ALL, asked of the coverage register rather than inferred from
#: the rows. A platform whose every row states no access is either a route that never reads it or a
#: platform that has just lost it entirely, and one run's rows cannot tell those apart: inferring it
#: would make the audit blind to exactly the failure it exists for. `data/coverage/extract.yaml`
#: records how each platform is read, and `labels` is the route that takes a bare list of chapter
#: labels off a page carrying no date, no byline and no price.
COVERAGE = pathlib.Path(__file__).resolve().parents[1] / "data" / "coverage" / "extract.yaml"


#: THE QUESTION LIVES WITH THE CORPUS'S OTHER QUESTIONS, STORE-PLAN §10. What this module owns is
#: the reading of the answer: which counts mean a selector moved, and where each threshold came
#: from. A query written here as well would be a second place to keep right.
POPULATION = "attested releases and the fields a selector carries"


def rows(db):
    """Attested releases as the audit reads them: the platform, the two named fields, the access."""
    from relational import asks
    return asks.population(db, POPULATION)


def unnamed(got):
    """Rows carrying no episode title or no author, which is what a moved selector produces."""
    return [r for r in got if not str(r.get("ep") or "").strip() or not r.get("author")]


def route_states_no_access(path=None):
    """Platform names the coverage register reads by a route that states no access, as a set."""
    import yaml
    at = pathlib.Path(path or COVERAGE)
    if not at.exists():
        return set()
    doc = yaml.safe_load(at.read_text()) or {}
    return {p["platform"] for p in (doc.get("platforms") or [])
            if p.get("platform") and p.get("rendered_as") == "labels"}


def unpriced(got, silent_routes=None):
    """Rows that are named, state no access, and are read by a route that reads access at all.

    A ROUTE THAT READS NO ACCESS IS NOT A ROW THAT LOST ONE. Excluded by the register rather than
    by what the rows happen to show, because a platform whose every row is silent may equally have
    lost the field this morning, and a rule that inferred the exemption would excuse exactly that.
    """
    quiet = route_states_no_access() if silent_routes is None else silent_routes
    return [r for r in got if str(r.get("ep") or "").strip() and r.get("author")
            and not r.get("access") and r.get("plat") not in quiet]


def moved(got):
    """`[(platform, lost, total)]` for every platform that lost the field across its own rows."""
    seen = collections.Counter(r["plat"] for r in got)
    lost = collections.Counter(r["plat"] for r in unnamed(got))
    return sorted((p, n, seen[p]) for p, n in lost.items()
                  if n >= LOST_FLOOR and n >= seen[p] * LOST_SHARE)


def access_moved(got, silent_routes=None):
    """`[(platform, silent, total)]` for a route that reads access and has stopped on most rows.

    THE PER-ROUTE RULE THE ACCESS SIDE NEVER HAD, and the reason the flat ceiling kept being the
    only thing firing. A selector for a price belongs to a route exactly as a selector for a title
    does, so the same floor and the same share apply. What makes it a LOSS rather than a route
    reading no prices is that some row THAT ROUTE read does state access.

    PER ROUTE AND NOT PER PLATFORM, which is the difference between a finding and a false one.
    コミックゼノン is read by its own adapter, stating access on both its rows, and by the catch-all
    resolver, stating it on neither; counted per platform that is three of four rows silent on a
    platform that states access, and nothing has moved.
    """
    quiet = route_states_no_access() if silent_routes is None else silent_routes
    key = lambda r: (r["plat"], r.get("route") or "")
    seen = collections.Counter(key(r) for r in got)
    priced = {key(r) for r in got if r.get("access")}
    silent = collections.Counter(key(r) for r in unpriced(got, quiet))
    return sorted((p, n, seen[k]) for k, n in silent.items()
                  for p in [k[0]]
                  if k in priced and n >= LOST_FLOOR and n >= seen[k] * LOST_SHARE)


def findings(got, silent_routes=None):
    """Every reason this capture may not be published, as sentences. Empty is the healthy answer."""
    out = []
    for p, n, total in moved(got):
        out.append(f"{p}: {n} of {total} rows carry no episode title or no author, so a selector "
                   f"has probably moved")
    named = unnamed(got)
    if len(named) > SPREAD:
        out.append(f"{len(named)} attested rows have no episode title or no author, spread too "
                   f"widely to be one platform")
    for p, n, total in access_moved(got, silent_routes):
        out.append(f"{p}: {n} of {total} rows state no access on a platform that states it "
                   f"elsewhere, so a price selector has probably moved")
    silent = unpriced(got, silent_routes)
    if len(silent) > NO_ACCESS_FLOOR and len(silent) > len(got) * NO_ACCESS_SHARE:
        out.append(f"{len(silent)} of {len(got)} attested rows state no access, over "
                   f"{NO_ACCESS_SHARE:.0%}, which is wider than any one route")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quiet", action="store_true", help="the counts alone")
    a = ap.parse_args(argv)

    import relational
    if not relational.DB.exists():
        raise SystemExit(f"no store at {relational.DB}; run ./build.py first")
    got = rows(relational.open_db())
    named, silent = unnamed(got), unpriced(got)
    print(f"attested {len(got)}, missing a name {len(named)}, missing access {len(silent)}")
    if not a.quiet:
        for r in named[:15]:
            print(f"   {r['plat']}  {str(r['work'])[:30]}  {r['ep']!r:.30}")
        for p, n in collections.Counter(r["plat"] for r in silent).most_common(8):
            print(f"   {n:4}  {p}")
    bad = findings(got)
    for line in bad:
        print(f"  {line}")
    if bad:
        raise SystemExit(f"{len(bad)} field audit finding(s). See RUNBOOK-github.md section 8.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
