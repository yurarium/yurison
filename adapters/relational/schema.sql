-- Yurarium, as a relational model.
--
-- DERIVED DESCRIBES ITS AUTHORITY AND SAYS NOTHING ABOUT ITS SHAPE. This database is rebuilt from
-- committed inputs and deleting it costs time alone. It is still designed on its own merits,
-- because a compiler should target the best representation for the questions asked of it instead
-- of transliterating the file layout it came from. One table per YAML file would earn nothing.
--
-- THE TEST IT IS MEANT TO PASS: a reader of this file can tell what the database believes and why,
-- without reading build.py.
--
-- WHAT MOVES FROM CODE TO SCHEMA. Five invariants in check.py are foreign keys written out as
-- Python, and they run after the damage rather than refusing it:
--
--   every credit identifier resolves            work_credit.credit -> credit.id
--   a shipped identifier resolves               work_credit.work   -> work.id
--   one row per identifier                      primary keys
--   credit pages listing a work that does not name them    the edge is the only link
--   publisher pages listing a work from another house      the edge is the only link
--
-- The last two stop being checkable at all, which is the point: there is no way to state the wrong
-- thing. A page lists what the edge says and nothing else.

PRAGMA foreign_keys = ON;

-- ── the things that have identity ───────────────────────────────────────────────────────────────
-- OPAQUE IDS, because a name is not an identity. Two artists share a pen name, one artist changes
-- theirs, and a work is reissued under a title its author never used. `w#####`, `c#####`, `h#####`
-- are the project's existing identifiers and they carry no meaning on purpose.

CREATE TABLE work (
  id                TEXT PRIMARY KEY CHECK (id GLOB 'w[0-9]*'),
  title             TEXT NOT NULL,
  first_publication TEXT,                       -- ISO 8601, whole or partial
  first_event       TEXT CHECK (first_event IN ('publication', 'shop-delivery', NULL)),
  volume_count      INTEGER CHECK (volume_count IS NULL OR volume_count >= 0),
  explicit_content  INTEGER NOT NULL DEFAULT 0 CHECK (explicit_content IN (0, 1)),
  -- WHY THIS WORK IS HERE AT ALL. DEFINITIONS section 6 admits a work on stated grounds, and a row
  -- with no grounds is a work nobody decided to include.
  admitted_by       TEXT NOT NULL
);

CREATE TABLE credit (
  id      TEXT PRIMARY KEY CHECK (id GLOB 'c[0-9]*'),
  surface TEXT NOT NULL UNIQUE,                 -- the name as a source writes it
  -- A PERSON, AN ORGANISATION, A VENUE. `entities` decides and `credits.json` records the decision,
  -- so a query can ask how many works name no person without re-deciding it. The vocabulary is the
  -- one the corpus actually uses: I guessed a wider one first and 64 rows were refused for holding
  -- the right answer.
  kind    TEXT NOT NULL CHECK (kind IN ('person', 'organisation', 'venue', 'unknown'))
);

CREATE TABLE publisher (
  id   TEXT PRIMARY KEY CHECK (id GLOB 'h[0-9]*'),
  name TEXT NOT NULL UNIQUE
);

-- AN IMPRINT BELONGS TO A HOUSE, which `an imprint spelling belongs to its own publisher` says in
-- Python today. Here it is a foreign key and a spelling cannot be filed under the wrong house.
CREATE TABLE imprint (
  id        INTEGER PRIMARY KEY,
  publisher TEXT NOT NULL REFERENCES publisher(id) ON DELETE CASCADE,
  name      TEXT NOT NULL,
  UNIQUE (publisher, name)
);

-- ── the edges, which are where roles live ───────────────────────────────────────────────────────
-- A ROLE BELONGS TO THE EDGE AND NOT TO THE PERSON. One artist is 原作 on one work and 作画 on
-- another, so a role column on `credit` would be wrong for one of them. This was worked out in the
-- credit extraction and the schema is where it becomes impossible to get wrong.

CREATE TABLE work_credit (
  work   TEXT NOT NULL REFERENCES work(id)   ON DELETE CASCADE,
  credit TEXT NOT NULL REFERENCES credit(id) ON DELETE RESTRICT,
  role   TEXT,                                  -- 著, 原作, 作画 … NULL where the field states none
  seq    INTEGER NOT NULL,                      -- the order the field wrote them in
  PRIMARY KEY (work, credit, role)
);

CREATE TABLE work_publisher (
  work      TEXT NOT NULL REFERENCES work(id)      ON DELETE CASCADE,
  publisher TEXT NOT NULL REFERENCES publisher(id) ON DELETE RESTRICT,
  imprint   INTEGER REFERENCES imprint(id)         ON DELETE SET NULL,
  PRIMARY KEY (work, publisher)
);

-- ── what is claimed about a name, and on whose word ─────────────────────────────────────────────
-- THE FLATTENING THIS REPLACES. A reading lived as `reading`, `reading_basis`, `reading_source`,
-- `reading_source_kind`, `reading_at`, `reading_url`, `reading_note`, `reading_boundary` and
-- `reading_conflicts` on one record. That shape is why 293 divisions sat in `reading_note` prose
-- while `reading_boundary` was empty: two slots for one fact, and prose is not queryable.
--
-- One row is one claim. A second claim about the same subject is a second ROW, so a conflict is
-- data and not a nested list, and "which claims rest on a community database" is one query.

CREATE TABLE claim (
  id           INTEGER PRIMARY KEY,
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('work', 'credit', 'publisher')),
  subject      TEXT NOT NULL,
  predicate    TEXT NOT NULL CHECK (predicate IN ('reading', 'division', 'english', 'romanisation')),
  value        TEXT NOT NULL,

  -- HOW WE CAME BY IT. `facts/reading` and `facts/division` rule on which basis admits which kind,
  -- and `basis_admits_kind` below is that ruling as a table instead of as a Python dict.
  basis        TEXT NOT NULL REFERENCES basis(name),
  source       TEXT,                            -- who said so, in their own words
  source_kind  TEXT REFERENCES source_kind(name),
  retrieved    TEXT,                            -- ISO 8601 date the answer was obtained
  url          TEXT,

  -- WHY THE REVIEWER CONCLUDED IT. `researched` demands this and `curate.problems` enforces it in
  -- Python; here it is a CHECK, so a researched claim with no note cannot be written at all.
  note         TEXT,

  CHECK (basis <> 'researched' OR note IS NOT NULL),

  -- A STATED CLAIM NAMES WHERE IT CAME FROM. This is the stage-three invariant as a constraint:
  -- a reading a source printed is an INPUT, the repository is its only copy, and one without an
  -- address cannot be checked, refreshed or argued with.
  CHECK (basis <> 'stated' OR url IS NOT NULL OR source_kind = 'derived')
);

CREATE INDEX claim_subject ON claim (subject_kind, subject, predicate);
CREATE INDEX claim_basis   ON claim (basis);
CREATE INDEX claim_source  ON claim (source_kind);

-- ── the rulings, as data ────────────────────────────────────────────────────────────────────────
-- THESE TWO TABLES ARE WHY THE HAND-WRITTEN COPIES CANNOT COME BACK. `check.STATES_A_READING` was a
-- copy of `curate.READING_ATTRIBUTION`'s values and it had drifted before anybody looked;
-- `check.DIVIDED_BY_ITS_SOURCE` was a copy of `curate.DIVIDING_BASES`. A foreign key has no second
-- copy to drift from.

CREATE TABLE basis (
  name    TEXT PRIMARY KEY,
  -- the columns are the questions anybody asks of a basis, which is facts/division's table
  cited   INTEGER NOT NULL CHECK (cited   IN (0, 1)),
  donates INTEGER NOT NULL CHECK (donates IN (0, 1)),
  marked  INTEGER NOT NULL CHECK (marked  IN (0, 1)),
  counted INTEGER NOT NULL CHECK (counted IN (0, 1))
);

CREATE TABLE source_kind (
  name TEXT PRIMARY KEY
);

CREATE TABLE basis_admits_kind (
  basis       TEXT NOT NULL REFERENCES basis(name)       ON DELETE CASCADE,
  source_kind TEXT NOT NULL REFERENCES source_kind(name) ON DELETE CASCADE,
  PRIMARY KEY (basis, source_kind)
);

-- ── where a work was published, and when ────────────────────────────────────────────────────────
-- A PRINTING AND A DELIVERY ARE DIFFERENT EVENTS, which `a delivery date never stands beside a
-- printing` says in Python. The kind is on the row, so the question is a WHERE clause.

CREATE TABLE edition (
  id      INTEGER PRIMARY KEY,
  work    TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  isbn    TEXT UNIQUE,

  -- WHAT A VOLUME IS CALLED AND WHERE IT SITS ARE TWO FACTS, and this table held only the second.
  -- `volume` is a position in a run and an integer answers it. A DESIGNATION is the word the
  -- publisher uses: `上`, `創刊号`, `2017年1月号`. 983 volumes carry one, no integer can hold it,
  -- and STORE-PLAN §3 is where the schema stopped pretending otherwise.
  --
  -- NEITHER IS REQUIRED AND NEITHER EXCLUDES THE OTHER. A volume may have both in principle:
  -- `build.volume_number` reads 創刊号 as the first issue, so a designation can acquire a position.
  -- No row carries both today and that is left as an observation rather than written in as a
  -- CHECK, because a constraint on an accident refuses the first correct row that meets it.
  volume       INTEGER,
  designation  TEXT,

  dated   TEXT,
  kind    TEXT NOT NULL CHECK (kind IN ('printing', 'shop-delivery', 'serialisation')),

  -- WHAT KIND OF EVIDENCE THE DATE RESTS ON, following `claim`'s pattern rather than reusing its
  -- table: `claim` is scoped to what a NAME is, by its own CHECK on predicate. A closed set,
  -- because a basis nobody can name is a basis nobody can weigh.
  dated_basis  TEXT CHECK (dated_basis IS NULL OR dated_basis IN
                 ('national-library', 'openbd-registration', 'madb-tankobon', 'shop-delivery')),

  -- A DATE WITH NO PAGE BEHIND IT is what `per-book dates cite their page` refuses.
  cite    TEXT,
  CHECK (dated IS NULL OR cite IS NOT NULL),

  -- AN ISBN IS A KEY INTO EVERY DATED REGISTRY THERE IS, so a volume holding one and no date means
  -- nobody asked. `volumes with an isbn and no date` has been a ZERO budget and is now unstateable;
  -- locked in 2026-08-13 while the count was 0, which is the only time it is free to adopt.
  CHECK (isbn IS NULL OR dated IS NOT NULL)
);

CREATE INDEX edition_work ON edition (work, kind);

-- ── the questions this shape makes askable, which the file layout did not ───────────────────────
--
--   what would we lose if NDL were withdrawn
--     SELECT count(*) FROM claim WHERE source_kind = 'national-library';
--
--   which claims rest on a community database
--     SELECT * FROM claim WHERE source_kind = 'community-db';
--
--   which works name nobody
--     SELECT w.id FROM work w LEFT JOIN work_credit e ON e.work = w.id WHERE e.work IS NULL;
--
--   where do two sources disagree about one name
--     SELECT subject, predicate, count(DISTINCT value) n FROM claim
--     GROUP BY subject, predicate, subject_kind HAVING n > 1;
--
-- Each of those is a script today, and the last one has no script at all.
