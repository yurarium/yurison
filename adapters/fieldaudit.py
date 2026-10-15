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


#: WHY THERE IS NO PER-ROUTE RULE FOR ACCESS, after two days of trying to write one. A moved price
#: selector is a reading that USED to carry access and stopped, and a single run cannot see "used
#: to": within one capture, a reading that is mostly silent looks exactly like a reading that never
#: read prices at all. The rule written on 2026-08-17 fired twice and was wrong both times, on
#: コミックゼノン where two routes read one platform, and on MAGCOMI where one route reads it
#: through two files; keyed tighter each time, it then reported コミックDAYS, whose atom reading
#: carries access on 3 of 31 rows, which satisfies "states it elsewhere" on noise. A check whose
#: pattern has never matched a real fault and stops good runs is worse than none, so it is gone
#: rather than tuned again.
#:
#: WHAT WOULD ACTUALLY CATCH IT is the previous run: the store is journal-backed and holds what each
#: reading carried yesterday, so "this reading dropped access on rows it used to price" is a
#: question with an answer. That is a different instrument from anything here, which reads one
#: capture, and it is written down as a gap rather than approximated by a rule that cannot mean it.

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
    silent = unpriced(got, silent_routes)
    if len(silent) > NO_ACCESS_FLOOR and len(silent) > len(got) * NO_ACCESS_SHARE:
        out.append(f"{len(silent)} of {len(got)} attested rows state no access, over "
                   f"{NO_ACCESS_SHARE:.0%}, which is wider than any one route")
    return out


def platform_files(platform, paths):
    """The source files among `paths` that are `platform`'s own capture, by its display name.

    A FILE SPANNING PLATFORMS IS NOT ONE OF THEM. A moved selector is a fault in one platform's own
    adapter, and the general routes (`remaining`, `backfill`, `bylines`) write every platform into
    one file. This counted any file holding a row of the platform, so on 2026-10-16 three
    ヤンジャン+ rows set back `webpages/remaining.yaml` whole and thirty other works the run had
    just reached went with it. Such a platform is reported, and nothing of anyone else's is undone.
    """
    import yaml
    out = []
    for f in paths:
        try:
            d = yaml.safe_load(pathlib.Path(f).read_text(encoding="utf-8")) or {}
        except Exception:                                                   # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        own = {d.get("platform_name"), d.get("platform")}
        rows = {w.get("platform_name") for w in d.get("works") or [] if isinstance(w, dict)}
        if platform in own or (rows == {platform}):
            out.append(f)
    return out


def quarantine(platforms, root="."):
    """Restore each platform's changed source files to the last commit, and return them.

    QUARANTINE AND PUBLISH, ruled by the owner on 2026-10-15. A platform whose selector moved
    returns rows with a field missing from most of them, and before this the audit stopped the run,
    so one platform's bad morning withheld every platform's updates. Now that platform's capture is
    set back to the last good one, the rest is published, and the finding is recorded for
    `runhealth.py`, which raises an issue if it persists.
    """
    import subprocess
    changed = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "data/source"],
                             capture_output=True, text=True, cwd=root).stdout.split()
    files = sorted({f for p in platforms for f in platform_files(p, [
        str(pathlib.Path(root) / c) for c in changed])})
    if files:
        subprocess.run(["git", "checkout", "HEAD", "--", *[str(pathlib.Path(f).relative_to(root))
                                                           for f in files]],
                       check=True, cwd=root)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quiet", action="store_true", help="the counts alone")
    ap.add_argument("--quarantine", action="store_true",
                    help="set back a platform whose selector moved, record, and exit 0")
    ap.add_argument("--report", default=None, help="append outcomes here for runhealth.py")
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
    if not a.quarantine:
        if bad:
            raise SystemExit(f"{len(bad)} field audit finding(s). See RUNBOOK-github.md section 8.")
        return 0
    lost = [p for p, _, _ in moved(got)]
    files = quarantine(lost) if lost else []
    for f in files:
        print(f"  quarantined {f}: its last committed capture is published instead")
    outcomes = [{"id": f"fieldaudit:{p}", "ok": False, "stage": "checks",
                 "error": "a selector has probably moved; the last good capture is published"}
                for p in lost]
    wide = [l for l in bad if not any(l.startswith(f"{p}:") for p in lost)]
    outcomes.append({"id": "fieldaudit", "ok": not wide, "stage": "checks",
                     "error": "; ".join(wide)[:300]})
    if a.report:
        import json
        rp = pathlib.Path(a.report)
        got_r = json.loads(rp.read_text()) if rp.exists() else []
        rp.write_text(json.dumps(got_r + outcomes, ensure_ascii=False, indent=1))
    # TELL THE WORKFLOW TO COMPILE AGAIN, because the store it holds was built from what was just
    # set back.
    import os
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"rebuild={'yes' if files else 'no'}\n")
    print(f"{len(bad)} finding(s); {len(files)} file(s) quarantined across {len(lost)} platform(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
