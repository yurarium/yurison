#!/usr/bin/env python3
"""What the site is served, field by field, and which of those fields the store could answer.

WHY THIS EXISTS. STORE-PLAN makes the relational store the sole compiled form, and every section of
it is a migration. A migration with no number is a sequence of changes that feel like progress, so
this is the number: how much of what a reader is served still reaches them without passing through
the store. It starts at the identity spine and must end at everything.

IT ASKS ABOUT WHAT THE SITE SERVES, NOT ABOUT WHAT THE STORE HOLDS. A budget counting tables would
rise by adding a table nobody reads. The population here is the files `deploy.sh` copies, so the
only way to move it is to make a field the site actually gets answerable from the store.

WHAT IT CANNOT SEE, and STORE-PLAN §1 says so outright: a field derivable in principle and not in
fact, because the emitter still reads the JSON. Derivability is what this measures and emission is
what proves it, which is why §6 is a section of its own rather than a footnote here.
"""
import json
import pathlib
import re

#: The corpus files `deploy.sh` copies into `kari/data`. `checks.json`, `status.json` and `run.json`
#: are deliberately absent: they are the RUN's report on itself rather than data about works, and
#: requiring the gate's own findings to come from the store would be a category error. The line is
#: between what a reader's page is built from and what describes the run that built it.
CORPUS = ("index.json", "works.json", "series.json", "credits.json", "publishers.json")

#: A key that reads as a field name rather than as data.
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: A key that is one of an ISSUED SERIES: a short prefix and a run of digits, `w00253`, `c00154`.
#: Split so the prefix and the width can be compared across the keys, which is what makes a series.
SERIAL = re.compile(r"^([A-Za-z_]{1,3})([0-9]{2,})$")


def is_series(keys):
    """Whether these keys are issued identifiers of one series rather than field names.

    THE CASE THIS EXISTS FOR. `series.json:merged` maps a retired work id to the work that
    absorbed it, `{"w00253": "w00097", ...}`, 151 of them. Its keys pass as field names and its
    values are strings, so neither signal in `is_map` fires and one field was counted as 151.

    THE RULE IS SAMENESS AND NOT SHAPE, which is what keeps it off records. One key looking like
    `sha256` proves nothing; every key sharing a prefix AND a digit width is a run of identifiers
    somebody issued. `schema.sql` writes the same thing as `id GLOB 'w[0-9]*'`, and stating it as a
    series rather than as a list of prefixes means a fourth prefix needs no edit here.
    """
    if len(keys) < 2:
        return False
    seen = set()
    for k in keys:
        m = SERIAL.match(str(k))
        if not m:
            return False
        seen.add((m.group(1), len(m.group(2))))
    return len(seen) == 1


def is_map(d):
    """Whether a dict is keyed by DATA rather than by field name.

    THE PROBLEM THIS SOLVES. `feed/names.json` is keyed by folded title and holds 3,301 of them, so
    walking it naively reports 3,301 field paths that are one field. Collapsing every map to `{}`
    took the corpus from 137,131 paths to something a person can read.

    THREE SIGNALS, ANY OF WHICH IS ENOUGH, because each alone gets a real case wrong.

      THE KEYS ARE AN ISSUED SERIES, one prefix and one digit width across all of them. This is
      what catches `merged`, whose values are plain strings, so there is no vocabulary to read.

      THE KEYS READ AS DATA. `authors` in names.json is keyed `*sow*` and `2C=がろあ`, which no
      record would call a field. This is what catches a map whose values vary in shape, and the
      string-valued maps `floor` and `phrases`, where there are no value keys to compare.

      THE VALUES SHARE A SMALL VOCABULARY. A map of records has many entries drawing on a handful
      of fields between them. This is what catches a map whose keys happen to look like identifiers,
      which `credits.json` keyed by `c01876` would otherwise slip through as.

    THE SIZE FLOOR IS WAIVED FOR A SERIES AND FOR NOTHING ELSE. `credits.json:merged` holds six
    entries, and six is indistinguishable from a record BY SIZE; it is distinguishable by its keys
    being `c00154` and `c00268`, which no field is called.

    THE COUNTER-CASE THAT DECIDES THE DESIGN, and it is why neither signal is used alone. A
    `series.json` row has 31 keys and almost all of its values are scalars, so a rule reading "many
    keys, simple values" as a map would collapse the single most important record in the corpus into
    one path and report near-total coverage. Its keys ARE field names, so the first signal refuses
    it, and its values are not dicts, so the second never fires.
    """
    if not isinstance(d, dict) or not d:
        return False
    keys = list(d)
    if is_series(keys):
        return True
    if len(d) <= 8:
        return False
    named = sum(1 for k in keys if IDENTIFIER.match(str(k)))
    if named * 2 < len(keys):
        return True
    vals = [v for v in list(d.values())[:12]]
    if vals and all(isinstance(v, dict) for v in vals):
        seen = set()
        for v in vals:
            seen |= set(v)
        return len(seen) <= 40
    return False


def paths(doc, limit=30, depth=8):
    """Every distinct field path in one document, with lists and data-keyed maps collapsed.

    `limit` samples a list or a map rather than walking all of it, because a path that appears in
    the first thirty rows and nowhere else is not a field anybody is served differently.
    """
    out = set()

    def walk(v, at, d):
        if d > depth:
            return
        if isinstance(v, dict):
            if is_map(v):
                out.add(at + "{}")
                for x in list(v.values())[:limit]:
                    walk(x, at + "{}", d + 1)
                return
            for k, x in v.items():
                here = f"{at}.{k}" if at else str(k)
                out.add(here)
                walk(x, here, d + 1)
        elif isinstance(v, list):
            for x in v[:limit]:
                walk(x, at + "[]", d + 1)

    walk(doc, "", 0)
    return out


def served(build="data/build", texts=None):
    """`{file: {path}}` for every corpus file the site is served, feed months included.

    `texts` IS `{name: json text}` AND IS HOW THIS IS ASKED NOW. STORE-PLAN §13 stopped `build.py`
    writing these files, so reading a directory meant reading one that nothing fills: the budget
    over this answered 0 for every run after that change and nobody was told it had stopped
    looking. A directory that is not there is indistinguishable from a corpus with no fields in it,
    which is STANDING-INSTRUCTIONS §4 with the pattern removed rather than never matched.
    """
    if texts is not None:
        return {n: paths(json.loads(s)) for n, s in texts.items()
                if n in CORPUS or n.startswith("feed/")}
    root = pathlib.Path(build)
    out = {}
    for name in CORPUS:
        f = root / name
        if f.exists():
            out[name] = paths(json.loads(f.read_text(encoding="utf-8")))
    feed = root / "feed"
    if feed.is_dir():
        for f in sorted(feed.glob("*.json")):
            out[f"feed/{f.name}"] = paths(json.loads(f.read_text(encoding="utf-8")))
    return out


#: WHICH SHIPPED FIELDS THE STORE COULD ANSWER TODAY, as `file:path-prefix`. A declaration, because
#: nothing can infer that `series[].work` is `work.title`; the mapping is a design decision and
#: belongs where a reader can disagree with it.
#:
#: IT IS DELIBERATELY A PREFIX LIST AND NOT ONE ENTRY PER FIELD. A per-field list would be a second
#: thing to keep in step with the schema, which is the fault `_input_keys` refuses in `check.py`.
#: Each section of STORE-PLAN adds the prefixes it has modelled, so the list grows once per domain.
#:
#: THE SPINE, PLUS WHAT §2 FILLED AND §3 MODELLED. `volume` holds 6,108 rows, `edition` 6,920 and
#: `work_publisher` 2,661, so a volume's ISBN, number and designation are answerable, and so is each
#: dated event about it with the basis that date rests on, and which house and line it is published
#: under. §5b is why those are two tables: 812 volumes state a printing and a delivery that differ,
#: and one row per book could hold only one of them.
STORE_ANSWERS = (
    # §6: `index.json` IS EMITTED FROM THE STORE, one row per work with every record's address.
    "index.json:[].id", "index.json:[].t", "index.json:[].y", "index.json:[].c",
    "index.json:[].n", "index.json:[].d", "index.json:[].l", "index.json:[].ct",
    "index.json:[].g", "index.json:[].ids", "index.json:[].ci",
    "index.json:id",
    "index.json:t",
    "series.json:series[].id",
    "series.json:series[].work",
    "series.json:series[].first",
    # §5e: whether a work is running, and on whose word.
    # §6: the print rows a run is made of, which `publishers.json` and this file both count.
    "series.json:series[].print", "series.json:series[].print[].work_id",
    # WHAT A BLOCK STANDS FOR AS AGAINST WHAT IT SHOWS, and the register of what is not shown at
    # all. Both are emitted and both were unclaimed, and the budget only found them when a capture
    # brought in a row that carries them: a path nothing in the sample happened to hold is a path
    # this measure cannot see. `print_party.seq` holds the folded records and
    # `work_presentation.visibility` the register.
    "series.json:series[].print[].folded_names", "series.json:series[].print[].folded_names[]",
    "series.json:series[].visibility",
    "series.json:series[].print[].work_ids", "series.json:series[].print[].publisher",
    "series.json:series[].print[].imprint", "series.json:series[].print[].label",
    "series.json:series[].print[].first", "series.json:series[].print[].last",
    # WHEN A SHOP BEGAN DELIVERING THE FILE, from `print_row.delivered_from`. It has been served on
    # 1,121 print blocks and was never declared, which nobody saw because this budget was reading a
    # directory §13 had stopped filling.
    "series.json:series[].print[].delivered_from",
    # AND WHO DISTRIBUTES THE RUN, from `print_row.distributor`, which `_print_blocks` reads in the
    # same SELECT as the line above. `works.json:works[].distributor` was declared and this path was
    # not, and the field is written onto a block only where the row HAS a distributor, so it stayed
    # invisible until a work that has one arrived. The same shape as `delivered_from`: a field the
    # store answers, served for as long as it has existed, never named here.
    "series.json:series[].print[].distributor",
    "series.json:series[].print[].volumes", "series.json:series[].print[].shop_url",
    "series.json:series[].state",
    "series.json:series[].state_basis",
    "series.json:series[].state_claims",
    "series.json:series[].completed_basis",
    "series.json:series[].author",
    "works.json:works[].marketing_label",
    "works.json:works[].marketing_label_basis",
    # §6: every field of `works.json` is modelled as of 2026-08-13. The file is not yet emitted
    # from the store, which is what the section still owes it, and the reason is in STORE-PLAN.
    "works.json:count", "works.json:works",
    "works.json:works[].title", "works.json:works[].creator", "works.json:works[].grouping",
    "works.json:works[].sources", "works.json:works[].records", "works.json:works[].volumes",
    "works.json:works[].admitted_by", "works.json:works[].admitted_by[]",
    "works.json:works[].records[]",
    "works.json:works[].creator_basis", "works.json:works[].distributor",
    "works.json:works[].periodical", "works.json:works[].shop_url",
    "works.json:works[].work_id",
    # §5c: the grounds a work was admitted on, and what a source says its run is.
    "works.json:works[].admitted_by",
    "works.json:works[].volume_count",
    "works.json:works[].explicit_content",
    "works.json:works[].completed_claim",
    "works.json:works[].publisher",
    "works.json:works[].imprint",
    # §6: the record layer. `work_origin` and `work_record` are keyed on the catalogue record,
    # because `works.json` holds 2,574 of those against 3,038 works.
    "works.json:works[].first_publication",
    "works.json:works[].records",
    "works.json:works[].volumes[].number",
    "works.json:works[].volumes[].openbd",
    "works.json:works[].volumes[].cover_url",
    "works.json:works[].volumes[].final_volume",
    "works.json:works[].volumes[].final_volume_basis",
    "feed/credit-keys.json:{}",
    "works.json:works[].volumes[].isbn",
    "works.json:works[].volumes[].number_n",
    "works.json:works[].volumes[].published",
    "works.json:works[].volumes[].delivered",
    "works.json:works[].volumes[].designation",
    "works.json:works[].volumes[].published_basis",
    "works.json:works[].volumes[].published_source",
    "works.json:works[].volumes[].isbn_source",
    "works.json:works[].volumes[].madb_id",
    # §6: `credits.json` IS EMITTED FROM THE STORE, so every path in it is answered by definition
    # rather than by declaration. `emit.credits` is the only thing that writes the file and
    # `test_emit` compares it byte for byte against what the compiler used to produce.
    "credits.json:count", "credits.json:generated", "credits.json:note",
    "credits.json:credits", "credits.json:credits{}", "credits.json:merged", "credits.json:merged{}",
    "credits.json:credits{}.id",
    "credits.json:credits{}.name",
    # §6: `publishers.json` IS EMITTED FROM THE STORE, so every path in it is answered by
    # definition. `emit.publishers` is the only thing that writes it.
    "publishers.json:count", "publishers.json:generated", "publishers.json:note",
    "publishers.json:merged", "publishers.json:merged{}",
    "publishers.json:publishers", "publishers.json:publishers{}",
    "publishers.json:publishers{}.id",
    "publishers.json:publishers{}.name",
    # §4: what a platform offers of a work, and what it published.
    "series.json:series[].sources[].platform",
    "series.json:series[].sources[].url",
    "series.json:series[].sources[].chapters",
    "series.json:series[].sources[].free",
    "series.json:series[].sources[].free_timed",
    "series.json:series[].sources[].priced",
    "series.json:series[].sources[].latest",
    "series.json:series[].sources[].partial",
    "series.json:series[].sources[].retrieved",
    "feed/current.json:releases[].id",
    "feed/current.json:releases[].wid",
    "feed/current.json:releases[].work",
    "feed/current.json:releases[].plat_name",
    "feed/current.json:releases[].ep",
    "feed/current.json:releases[].pub",
    "feed/current.json:releases[].url",
    "feed/current.json:releases[].type",
    "feed/current.json:releases[].seen",
    # §6: `feed/current.json` AND THE ARCHIVED MONTHS ARE EMITTED FROM THE STORE as of 2026-08-13.
    # One emitter for both, because a row is the same row wherever it is filed and what differs is
    # the date filter over it. The archive is re-derived every build and what is locked is the ROW
    # SET rather than the bytes, which is what lets a name the store has since corrected reach a
    # month published before the correction.
    "feed/current.json:releases", "feed/current.json:window_days", "feed/current.json:from",
    "feed/current.json:to", "feed/current.json:generated",
    "feed/2026-07.json:releases", "feed/2026-07.json:month", "feed/2026-07.json:generated",
    "feed/current.json:releases[]", "feed/2026-07.json:releases[]",
    # §6: `feed/meta.json` IS EMITTED FROM THE STORE as of 2026-08-13, which closes the section.
    # What the emitter is HANDED rather than asked for is the run's own report on itself: how wide
    # the window is, which months are archived and how many promotional samples were set aside all
    # describe what a build did rather than what the corpus holds, which is the same reasoning that
    # keeps `run.json` and `checks.json` out of this measure. Everything the census LEARNED is in
    # the store: the platforms, how far each listing has fallen behind, and the two queues.
    "feed/meta.json:platforms", "feed/meta.json:platforms[]",
    "feed/meta.json:contradicted", "feed/meta.json:print_candidates",
    "feed/meta.json:print_candidates[]", "feed/meta.json:web_works", "feed/meta.json:web_works[]",
    "feed/meta.json:samples_dropped", "feed/meta.json:platform_meta",
    "feed/meta.json:platform_meta{}", "feed/meta.json:lapsed", "feed/meta.json:lapsed[]",
    "feed/meta.json:archive_months", "feed/meta.json:archive_from",
    "feed/meta.json:window_days", "feed/meta.json:generated",
    # §5: THE RENDERINGS. A name is a `surface` row keyed by the fold the feed joins on, what is
    # claimed about it is a `claim` row, and what a reader is shown in Latin is a `romanisation` or
    # a `ruby` row. The three name maps take the same paths because they are the same shape.
    # THE MAP AND ITS CONTENTS ARE TWO PATHS, because `{}` is not a field separator: `titles` is the
    # map and `titles{}` is what one entry holds, and claiming the second does not claim the first.
    # §6: THE MAP IS EMITTED FROM THE STORE as of 2026-08-13, every key of all seven sections.
    "feed/names.json:generated", "feed/names.json:note",
    "feed/names.json:titles", "feed/names.json:titles{}",
    "feed/names.json:authors", "feed/names.json:authors{}",
    "feed/names.json:publishers", "feed/names.json:publishers{}",
    "feed/names.json:imprints", "feed/names.json:imprints{}",
    # WHAT AN ENGLISH PAGE CALLS EACH PLATFORM, from `platform_register.en`, READER-PLAN item 5.
    # The interface held its own table of these until the register carried them, and this budget
    # caught the new field the moment it was served: a field a reader gets has to be one the store
    # can answer, and saying so here is the declaration that it is.
    "feed/names.json:platforms", "feed/names.json:platforms{}",
    "feed/names.json:credit_parts", "feed/names.json:credit_parts{}",
    "feed/names.json:floor", "feed/names.json:floor{}",
    "feed/names.json:phrases", "feed/names.json:phrases{}",
    # §5d: THE MERGE MAP. A retired identifier and what absorbed it, which `superseded` holds and
    # which the anchor constraint needs before it can say one address reaches one work.
    "series.json:merged", "series.json:merged{}",
    # §6: `series.json` IS EMITTED FROM THE STORE as of 2026-08-13, so every path in it is answered
    # by definition: the file is what the tables say. The paths stay listed rather than the file
    # being excluded, because the measure asks what the SITE is served and the answer has to keep
    # being true.
    "series.json:generated", "series.json:note", "series.json:credence",
    "series.json:thresholds", "series.json:series",
    "series.json:series[].chapters", "series.json:series[].chapters_stated",
    "series.json:series[].collection", "series.json:series[].completed_basis_ja",
    "series.json:series[].credits", "series.json:series[].evidence",
    "series.json:series[].free", "series.json:series[].free_timed",
    "series.json:series[].latest", "series.json:series[].latest_any",
    "series.json:series[].latest_any_kind", "series.json:series[].latest_ep",
    "series.json:series[].oneshot", "series.json:series[].partial",
    "series.json:series[].priced", "series.json:series[].series_url",
    "series.json:series[].skipped", "series.json:series[].sourced_from",
    "series.json:series[].sources", "series.json:series[].state_basis_ja",
    "series.json:series[].stated_next", "series.json:series[].url",
    "series.json:series[].credits[]", "series.json:series[].evidence[]",
    "series.json:series[].sourced_from[]", "series.json:series[].sources[]",
    "series.json:series[].state_claims[]",
    "series.json:series[].stated_next.cadence", "series.json:series[].stated_next.platform",
    "series.json:series[].stated_next.next_update",
    "series.json:series[].stated_next.next_update_undecided",
    "credits.json:merged",
    "publishers.json:merged",
    "series.json:series[].work_en",
    "series.json:series[].author_en",
)


def around(build="data/build", texts=None):
    """Every `file:path` the site is served that the store could not answer, sorted."""
    claimed = set(STORE_ANSWERS)
    out = []
    for name, ps in served(build, texts).items():
        for p in sorted(ps):
            key = f"{name}:{p}"
            if key in claimed or any(key.startswith(c + ".") for c in claimed):
                continue
            out.append(key)
    return sorted(out)
