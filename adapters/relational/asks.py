#!/usr/bin/env python3
"""Every standing question this store answers, as SQL. STORE-PLAN §10.

WHY A QUESTION AND AN INVARIANT ARE ONE OBJECT. A derivation is a question whose answer has to be
recomputed when its inputs move; an invariant is a question whose answer must be empty; a budget is
a question whose answer is counted and ratchets down. Written as separate registries they would have
to be kept in step, and the incremental path would re-answer one of them and not the others. This is
one registry with several shapes of expectation.

WHAT A SPEC HOLDS.

    sql        the question. An invariant returns the OFFENDING ROWS, one per violation, because
               `check.py` prints them and a count alone sends the reader looking.
    reads      the tables it touches, which is what `delta.converge` follows after a write.
    asserts    `empty` for an invariant. Absent for a question nobody has ruled on.
    budget     the number it may not exceed, for a budget. Absent otherwise.
    canary_rises_by  how much the canary should move a BUDGET's count, since a budget is a number
               and cannot be probed on a pass or a fail.
    why        what the number means, shown beside it in the gate's report.
    canary     SQL that plants a violation, so `--self-test` can prove the question can fail. A
               check whose pattern never matches reports clean, which is the fault STANDING
               INSTRUCTIONS §4 exists for, and a query is no more immune to it than a loop.
    fallback   what to do when it fires, for an invariant. Prose, shown to whoever hits it.

THE CANARY RUNS ON A COPY. `sqlite3.Connection.backup` into memory costs 25 ms for this store, so a
self-test plants its violation in a database nothing else can see and throws it away, rather than
writing to the store and trusting a rollback.

WHAT DOES NOT BELONG HERE. Anything about this repository rather than about the corpus: prose,
comment shape, which modules have tests, whether an adapter fetches through `net.py`. Those read the
source tree and stay in `check.py`, where they can.
"""

#: The questions the store answered before §10, which have no expectation attached: they are
#: reported, watched, and nobody has ruled that any particular answer is wrong.
QUESTIONS = {
    "claims resting on a community database": {
        "sql": "SELECT count(*) FROM claim WHERE source_kind = 'community-db'",
        "reads": ("claim",)},
    "claims we would lose if NDL were withdrawn": {
        "sql": "SELECT count(*) FROM claim WHERE source_kind = 'national-library'",
        "reads": ("claim",)},
    "works naming nobody": {
        "sql": "SELECT count(*) FROM work w LEFT JOIN work_credit e ON e.work = w.id "
               "WHERE e.work IS NULL",
        "reads": ("work", "work_credit")},
    "names two sources disagree about": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM claim "
               "GROUP BY surface, predicate HAVING count(DISTINCT value) > 1)",
        "reads": ("claim",)},
    "names nothing in the corpus is identified by": {
        "sql": "SELECT count(*) FROM surface s WHERE s.kind IN ('title', 'author', 'publisher') "
               "AND NOT EXISTS (SELECT 1 FROM names n WHERE n.surface = s.id)",
        "reads": ("surface", "names")},
    "names that name more than one thing": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM names GROUP BY surface "
               "HAVING count(*) > 1)",
        "reads": ("names",)},
    "names two sources disagree about, live claims only": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM claim WHERE displaced = 0 "
               "GROUP BY surface, predicate HAVING count(DISTINCT value) > 1)",
        "reads": ("claim",)},
    "dates cited to something that is not a page": {
        "sql": "SELECT count(*) FROM edition WHERE dated IS NOT NULL AND cite IS NOT NULL "
               "AND cite NOT LIKE 'http%' AND cite NOT LIKE 'madb:%' AND cite NOT LIKE 'openbd:%'",
        "reads": ("edition",)},
    "works on a house with no line named": {
        "sql": "SELECT count(*) FROM work_publisher WHERE imprint IS NULL",
        "reads": ("work_publisher",)},
    "rows the store could not admit": {
        "sql": "SELECT count(*) FROM quarantine",
        "reads": ("quarantine",)},
    "identities somebody ruled apart": {
        "sql": "SELECT count(*) FROM identity_ruling WHERE kind IN ('keep', 'homophone')",
        "reads": ("identity_ruling",)},
    "credits named by more than one work": {
        "sql": "SELECT count(*) FROM (SELECT credit FROM work_credit GROUP BY credit "
               "HAVING count(*) > 1)",
        "reads": ("work_credit",)},
    "claims whose evidence their basis does not admit": {
        "sql": "SELECT count(*) FROM claim c WHERE c.source_kind IS NOT NULL "
               "AND c.source NOT IN (SELECT source FROM self_sourced) "
               "AND EXISTS (SELECT 1 FROM basis_admits_kind a WHERE a.basis = c.basis "
               "AND a.predicate = c.predicate) AND NOT EXISTS "
               "(SELECT 1 FROM basis_admits_kind a WHERE a.basis = c.basis "
               "AND a.predicate = c.predicate AND a.source_kind = c.source_kind)",
        "reads": ("claim", "basis_admits_kind", "self_sourced")},
}


#: What must never be true. Each returns the offending rows, and the first column is what the
#: gate prints, so it names the thing rather than counting it.
INVARIANTS = {
    # THE FEED HOLDS WHAT A PLATFORM ATTESTED AND NOTHING ELSE. A listing site's claim is an INPUT
    # to the pipeline, and a row that reached the feed on one is the pipeline publishing its own
    # working. The claim survives on status.html, where it is labelled as a claim.
    "feed holds only attested rows": {
        "sql": "SELECT work_raw, id FROM release WHERE coalesce(provenance, '') <> 'attested'",
        "reads": ("release",),
        "asserts": "empty",
        "fallback": "drop the row from the feed; it stays in the claim trace on status.html",
        "canary": "INSERT INTO release (id, platform, provenance) "
                  "VALUES ('canary', (SELECT name FROM platform LIMIT 1), 'claimed')"},
    # EVERY UPDATE SAYS WHAT KIND OF UPDATE IT IS. `unknown` meant a claim row, and those are gone.
    "every update has a kind": {
        "sql": "SELECT work_raw, id FROM release WHERE event = 'unknown'",
        "reads": ("release",),
        "asserts": "empty",
        "fallback": "drop the row rather than publish an uncategorised update",
        "canary": "INSERT INTO release (id, platform, provenance, event) "
                  "VALUES ('canary', (SELECT name FROM platform LIMIT 1), 'attested', 'unknown')"},
    # A WORK'S DATES RUN FORWARD. A run cannot end before it began, and a row saying otherwise is
    # two sources being read as one work.
    "dates within a row are ordered": {
        "sql": "SELECT work, first, latest FROM serialisation "
               "WHERE first IS NOT NULL AND latest IS NOT NULL AND substr(first, 1, 7) > "
               "substr(latest, 1, 7)",
        "reads": ("serialisation",),
        "asserts": "empty",
        "fallback": "the two dates come from different sources; find which and keep the source's",
        "canary": "UPDATE serialisation SET first = '2099-01', latest = '2000-01' "
                  "WHERE work = (SELECT work FROM serialisation WHERE first IS NOT NULL "
                  "AND latest IS NOT NULL LIMIT 1)"},
    # A PRINT RUN STARTS BEFORE ITS LAST VOLUME. Same argument on the other layer.
    "a print run's dates are ordered": {
        "sql": "SELECT record, first, last FROM print_row "
               "WHERE first IS NOT NULL AND last IS NOT NULL AND first > last",
        "reads": ("print_row",),
        "asserts": "empty",
        "fallback": "one of the two dates belongs to another record of the same run",
        # PLANTED AS A ROW AND NOT AS AN EDIT, because no print row in the corpus states both dates
        # today: `last` is empty on all 2,512 of them. An UPDATE canary matched nothing and the
        # check reported clean, which is §4 exactly.
        "canary": "INSERT INTO print_row (work, record, first, last) "
                  "SELECT id, 'canary-record', '2099-01', '2000-01' FROM work LIMIT 1"},
    # A REFUTATION IS ABOUT A SERIALISATION, so a work that only ever appeared in print cannot be
    # rebutted for one. `work_presentation.visibility` is the register and `print` is the state.
    "no refutation of print serials": {
        "sql": "SELECT p.work FROM work_presentation p JOIN work_state s ON s.work = p.work "
               "WHERE p.visibility = 'rebutted' AND s.state = 'print'",
        "reads": ("work_presentation", "work_state"),
        "asserts": "empty",
        "fallback": "withdraw the rebuttal; the work was never published as a serialisation",
        # INSERT OR REPLACE, because 1,407 of the 1,648 print works have no presentation row at
        # all, so an UPDATE canary landed on nothing.
        "canary": "INSERT OR REPLACE INTO work_presentation (work, visibility) "
                  "SELECT work, 'rebutted' FROM work_state WHERE state = 'print' LIMIT 1"},
    # AN IMPRINT BELONGS TO THE HOUSE THAT RUNS IT. A line resolved against one publisher and
    # attached to a print row of another is a join that crossed two houses.
    "an imprint spelling belongs to its own publisher": {
        "sql": "SELECT y.imprint_raw, y.publisher, i.publisher FROM print_party y "
               "JOIN imprint i ON i.id = y.imprint "
               "WHERE y.publisher IS NOT NULL AND i.publisher <> y.publisher",
        "reads": ("print_party", "imprint"),
        "asserts": "empty",
        "fallback": "the registry names the line under the wrong house, or the spelling is shared",
        "canary": "UPDATE print_party SET publisher = (SELECT id FROM publisher WHERE id <> "
                  "(SELECT publisher FROM imprint WHERE id = print_party.imprint) LIMIT 1) "
                  "WHERE imprint IS NOT NULL AND id = "
                  "(SELECT min(id) FROM print_party WHERE imprint IS NOT NULL)"},
    # EVERY VOLUME THE STORE HOLDS BELONGS TO A RECORD THAT EXISTS. The foreign key says the work
    # exists; this says the RECORD does, which is what a volume is filed under.
    "every volume names a record the store holds": {
        "sql": "SELECT v.record, count(*) FROM volume v WHERE NOT EXISTS "
               "(SELECT 1 FROM record r WHERE r.id = v.record) GROUP BY v.record",
        "reads": ("volume", "record"),
        "asserts": "empty",
        "fallback": "the record was dropped from the compile and its volumes came with it",
        "canary": "UPDATE volume SET record = 'canary-no-such-record' WHERE id = "
                  "(SELECT min(id) FROM volume)"},
    # A CLAIM STANDS BEHIND EXACTLY ONE VALUE PER RECORD. Two live claims from one record about one
    # predicate is a record contradicting itself on the same line of the page.
    "a record makes one live claim per predicate": {
        "sql": "SELECT r.spelling, c.predicate, count(*) FROM claim c "
               "JOIN claim_record cr ON cr.claim = c.id JOIN name_record r ON r.id = cr.record "
               "WHERE c.displaced = 0 GROUP BY cr.record, c.predicate HAVING count(*) > 1",
        "reads": ("claim", "claim_record", "name_record"),
        "asserts": "empty",
        "fallback": "one of the two is displaced and the record has not said which",
        # THE SCHEMA REFUSED THE FIRST VERSION OF THIS CANARY, which is the constraint doing its
        # job: a `stated` claim owes a document, so a canary copying one had to carry its citation
        # or pick a basis that owes none.
        "canary": "INSERT INTO claim (surface, kind, predicate, value, basis, displaced) "
                  "SELECT c.surface, c.kind, c.predicate, 'カナリア', c.basis, 0 FROM claim c "
                  "JOIN claim_record cr ON cr.claim = c.id WHERE c.displaced = 0 "
                  "AND c.basis <> 'stated' LIMIT 1; "
                  "INSERT INTO claim_record (claim, record) SELECT (SELECT id FROM claim "
                  "WHERE value = 'カナリア'), cr.record FROM claim_record cr "
                  "JOIN claim c ON c.id = cr.claim WHERE c.displaced = 0 "
                  "AND c.basis <> 'stated' LIMIT 1"},
}


#: What is counted and ratchets down. The number lives in `docs/budgets.json` beside every other
#: budget, so a rise is accepted in one place with a reason.
BUDGETS = {
    # A RECORD'S RUBY SPELLS THE RECORD'S OWN NAME, and 11 sets do not. Two classes, both real. 9
    # are a bracketed reading the aligner drops: `恋する小惑星 (アステロイド)` gets spans covering
    # `恋する小惑星` and nothing over the gloss, so a renderer splicing them lands them short. 2 are
    # a name stored with a COMBINING dakuten where the aligner emits the composed character, so
    # `お嬢さま` and `お嬢さま` differ by a code point nobody can see. docs/GAPS.md carries both.
    #
    # ASKED OF THE RECORD AND NOT OF THE FOLD, which is the distinction §6 was bitten by: the
    # fold-keyed spans are the WINNING record's, and 362 of them legitimately spell `イマイ　悠`
    # where the fold is `イマイ悠`.
    "ruby spans that do not spell their own name": {
        "sql": "SELECT count(*) FROM (SELECT r.record FROM ruby r "
               "JOIN name_record n ON n.id = r.record GROUP BY r.record "
               "HAVING group_concat(r.text, '') <> n.spelling)",
        "reads": ("ruby", "name_record"),
        "why": "name records whose stored furigana do not reconstruct the name they sit over, so a "
               "renderer splicing them lands them on the wrong characters"},
    # THE CLASSIC SIGN OF A MOVED CSS SELECTOR: the adapter still returns rows, just emptier ones.
    "incomplete attested rows": {
        "sql": "SELECT count(*) FROM release WHERE provenance = 'attested' "
               "AND (trim(coalesce(instalment, '')) = '' OR author IS NULL "
               "OR NOT EXISTS (SELECT 1 FROM release_access_mode m WHERE m.release = release.id))",
        "reads": ("release", "release_access_mode"),
        "why": "attested releases missing a chapter name, author or access state. The classic sign "
               "of a moved CSS selector: the adapter still returns rows, just emptier ones. It "
               "rose 37 to 52 when the store began taking the compiler's rows rather than the "
               "feed's: 1,270 releases against the 961 the feed publishes, and the window was "
               "never the population this asks about."},
    # A NAME WITH NOTHING TO SHOW AN ENGLISH READER. The floor answers for most strings, so what
    # this counts is a title the store holds no reading, no rendering and no romanisation for.
    "works without English": {
        "sql": "SELECT count(*) FROM work w WHERE NOT EXISTS ("
               "SELECT 1 FROM names n JOIN claim c ON c.surface = n.surface "
               "WHERE n.work = w.id AND c.predicate = 'english' AND c.displaced = 0) "
               "AND NOT EXISTS (SELECT 1 FROM names n JOIN romanisation r ON r.surface = n.surface "
               "WHERE n.work = w.id)",
        "reads": ("work", "names", "claim", "romanisation"),
        "why": "works whose title reaches neither an English name nor a romanisation, so an "
               "English-only reader is shown the Japanese"},
    # A VOLUME NOBODY CAN DATE. `volumes with an isbn and no date` is the sharper form and is 0;
    # this is the whole population, including the volumes that state no ISBN either.
    "volume rows with no publication date": {
        # A PRINTING DATE AND NOT ANY DATE. A shop's delivery date is a different fact about the
        # same book, carries its own label, and does not date the printing.
        "sql": "SELECT count(*) FROM volume v WHERE v.record IN "
               "(SELECT record FROM print_row_record) AND NOT EXISTS (SELECT 1 FROM edition e "
               "WHERE e.volume = v.id AND e.kind = 'printing' AND e.dated IS NOT NULL)",
        "reads": ("volume", "edition", "print_row_record"),
        "why": "volumes on a work's print run that state no printing date, which is what the "
               "dating passes work through",
        # BOTH HALVES OF THE RULE, which is what the scratch self-test asserted before §10. The
        # first row is undated and on a run, so it counts; the second is undated and on a record no
        # print row reaches, and counting that would report a debt nobody owes.
        "canary": "INSERT INTO volume (work, record, seq) SELECT work, record, 9001 FROM volume "
                  "WHERE record IN (SELECT record FROM print_row_record) LIMIT 1; "
                  "INSERT INTO volume (work, record, seq) SELECT work, 'canary-unreached', 9002 "
                  "FROM volume LIMIT 1",
        "canary_rises_by": 1},
    # A RUN THE CATALOGUE COUNTS AND CANNOT LIST. The record states how many volumes there are and
    # the store holds fewer rows than that, which is a gap in what was captured.
    "volume rows a page counts but cannot list": {
        # A ROW WITH NOTHING ON IT. Not blocking, because a source could legitimately state that a
        # volume exists and nothing else; none does today, and a rise says a field stopped being
        # carried.
        "sql": "SELECT count(*) FROM volume v WHERE v.record IN "
               "(SELECT record FROM print_row_record) AND v.number_raw IS NULL "
               "AND v.designation IS NULL AND NOT EXISTS "
               "(SELECT 1 FROM volume_isbn i WHERE i.volume = v.id) AND NOT EXISTS "
               "(SELECT 1 FROM edition e WHERE e.volume = v.id AND e.dated IS NOT NULL)",
        "reads": ("volume", "volume_isbn", "edition", "print_row_record"),
        "why": "volume rows a catalogue counts and states nothing about, so a page can show the "
               "count and list nothing",
        "canary": "INSERT INTO volume (work, record, seq) SELECT work, record, 9003 FROM volume "
                  "WHERE record IN (SELECT record FROM print_row_record) LIMIT 1",
        "canary_rises_by": 1},
    # A NAME CARRYING ITS OWN CATALOGUING. `[カラー版]` and `【単話版】` are what an edition is, and
    # a work whose title states one is a row that will not join its siblings.
    "works named by a truncation": {
        # THE ASCII ELLIPSIS ALONE, which is what a listing page writes when it cuts a long name.
        # `…` and `‥` are typography a title may legitimately end in.
        "sql": "SELECT count(*) FROM (SELECT title AS t FROM work WHERE title LIKE '%...' "
               "UNION SELECT work_raw FROM release WHERE work_raw LIKE '%...')",
        "reads": ("work", "release"),
        "why": "titles ending in an ASCII ellipsis, which is a listing page truncating a long name "
               "and the pipeline storing the truncation as the work. A published month keeps its "
               "row set, so a row shipped that way stays until the archive ages out."},
}


#: POPULATIONS A CAPTURE PASS WORKS FROM, as against questions with an expectation. A pass asking
#: what the PUBLISHED database is missing is asking about the compiled form, which is this store: it
#: used to be asked of `data/build/series.json`, which the store emits, so the answer went out
#: through a file and came back in. That also made the pass depend on a compile having written that
#: file, and on a fresh runner it had not, so the pass died on a missing path every time.
POPULATIONS = {
    # A WORK SERIALISED ON THE WEB THAT NO PRINT RUN COVERS. `shopquery` and `editions/capture` ask
    # this same question, and their docstrings have each claimed to be its one producer while both
    # held a copy of the loop. One query, asked by both.
    "works with a serialisation and no print edition": {
        "sql": "SELECT w.id AS id, w.title AS work, b.field AS author, o.platform AS platform,"
               " o.url AS url FROM work w"
               " JOIN offer o ON o.work = w.id"
               " LEFT JOIN work_byline b ON b.work = w.id"
               " WHERE NOT EXISTS (SELECT 1 FROM print_row p WHERE p.work = w.id)"
               " ORDER BY w.id, o.id",
        "reads": ("work", "offer", "print_row", "work_byline")},
}


def population(db, name):
    """The rows of a named population, as dicts keyed by the columns the query selects."""
    spec = POPULATIONS[name]
    cur = db.execute(spec["sql"])
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def all_asks():
    """Every ask, whatever shape its expectation has."""
    return {**QUESTIONS, **INVARIANTS, **BUDGETS}


def store_checks():
    """The asks `check.py` turns into invariants and budgets: those with an expectation."""
    return {**INVARIANTS, **BUDGETS}
