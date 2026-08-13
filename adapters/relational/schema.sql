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
  id                TEXT PRIMARY KEY CHECK (id GLOB 'w[0-9][0-9][0-9][0-9][0-9]'),
  title             TEXT NOT NULL,
  first_publication TEXT,                       -- ISO 8601, whole or partial
  -- A LIST HOLDING NULL MAKES A CHECK PASS ON EVERYTHING, since `x IN (a, b, NULL)` answers NULL
  -- for an x that matches neither and a CHECK passes on NULL. `'banana'` inserted here for as long
  -- as this column has existed. Every comparable column omits it; §5a is where this one did.
  first_event       TEXT CHECK (first_event IS NULL OR first_event IN ('publication', 'shop-delivery')),
  explicit_content  INTEGER NOT NULL DEFAULT 0 CHECK (explicit_content IN (0, 1))

  -- `volume_count` AND `admitted_by` WERE COLUMNS HERE AND BOTH HELD A PLACEHOLDER ON EVERY ROW.
  -- The loader read them from `series.json`, which carries neither: the grounds are on
  -- `works.json`, structured, on 1,887 records, and the count is there too. So `admitted_by` was
  -- the string `'unstated'` 3,040 times under a NOT NULL whose own comment says a row with no
  -- grounds is a work nobody decided to include, and `volume_count` was NULL 3,040 times.
  --
  -- NEITHER COMES BACK AS A COLUMN, because measuring them showed both are CLAIMS. A work is
  -- admitted on grounds that name a comparator, a shelf, a page and a date, which is `admission`.
  -- And 72 works have records stating DIFFERENT volume counts, so a single column would have to
  -- pick one and discard a disagreement, which is the one thing this project does not do.
  -- `volume_claim` holds each with the source that states it, and how many volumes are HELD is
  -- `count(volume)`, which is the other side of `works holding fewer volumes than the shop states`.
);

-- WHY A WORK IS HERE AT ALL. DEFINITIONS §2 admits one on stated grounds: a licensed retailer's
-- yuri shelf is a comparator, presumptive and rebuttable. 1,887 grounds across 1,816 works.
CREATE TABLE admission (
  id         INTEGER PRIMARY KEY,
  work       TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  comparator TEXT,
  shelf      TEXT,
  shop_url   TEXT,
  url        TEXT,
  retrieved  TEXT,
  note       TEXT
);

CREATE INDEX admission_work ON admission (work);

-- HOW MANY VOLUMES A SOURCE SAYS THERE ARE, which is not how many we hold and is why both exist.
CREATE TABLE volume_claim (
  id         INTEGER PRIMARY KEY,
  work       TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  volumes    INTEGER NOT NULL CHECK (volumes >= 0),
  source     TEXT,
  provenance TEXT,
  retrieved  TEXT
);

CREATE UNIQUE INDEX volume_claim_one ON volume_claim (work, volumes, coalesce(source, ''));

CREATE TABLE credit (
  id      TEXT PRIMARY KEY CHECK (id GLOB 'c[0-9][0-9][0-9][0-9][0-9]'),
  surface TEXT NOT NULL UNIQUE,                 -- the name as a source writes it
  -- A PERSON, AN ORGANISATION, A VENUE. `entities` decides and `credits.json` records the decision,
  -- so a query can ask how many works name no person without re-deciding it. The vocabulary is the
  -- one the corpus actually uses: I guessed a wider one first and 64 rows were refused for holding
  -- the right answer.
  kind    TEXT NOT NULL CHECK (kind IN ('person', 'organisation', 'venue', 'unknown'))
);

CREATE TABLE publisher (
  id   TEXT PRIMARY KEY CHECK (id GLOB 'h[0-9][0-9][0-9][0-9][0-9]'),
  name TEXT NOT NULL UNIQUE
);

-- AN IMPRINT BELONGS TO A HOUSE, which `an imprint spelling belongs to its own publisher` says in
-- Python today. Here it is a foreign key and a spelling cannot be filed under the wrong house.
CREATE TABLE imprint (
  id        INTEGER PRIMARY KEY,
  publisher TEXT NOT NULL REFERENCES publisher(id) ON DELETE CASCADE,
  name      TEXT NOT NULL,
  -- THE LINE'S OWN NAME FOR ITSELF, which `facts/imprint`'s registry keys on and the site links by:
  -- `manga-time-kr-comics`. Several spellings reach one line, so this is not unique here.
  slug      TEXT,
  -- A LINE INSIDE A LINE. 裏少年サンデーコミックス sits under 少年サンデーコミックス, and the
  -- registry states the parent by name rather than by id.
  parent    TEXT,
  UNIQUE (publisher, name)
);

-- ── the edges, which are where roles live ───────────────────────────────────────────────────────
-- A ROLE BELONGS TO THE EDGE AND NOT TO THE PERSON. One artist is 原作 on one work and 作画 on
-- another, so a role column on `credit` would be wrong for one of them. This was worked out in the
-- credit extraction and the schema is where it becomes impossible to get wrong.

-- THE KEY WAS `(work, credit, role)` AND IT CONSTRAINED NOTHING. SQLite permits NULLs in a rowid
-- table's primary key, every one of the 4,165 rows has `role IS NULL`, and so the same edge inserted
-- three times running. A unique index over `coalesce(role, '')` is the same intent that fires.
--
-- THE ROLES ARE IN THE CORPUS AND NOT ON THIS ROUTE. `credits.json` writes its works list as
-- `{"id": "w00205"}` with no role in it, so the column has been empty since it was written. 631
-- name-and-role pairs sit on `series[].credits[]`, reachable only by joining a NAME to a credit
-- identifier, which is what §5d builds. Until then the column is honestly empty.
--
-- `seq` IS GONE, AND ITS ABSENCE IS TRUER THAN ITS VALUE WAS. It was documented as "the order the
-- field wrote them in" and the loader numbered each CREDIT's works rather than each WORK's credits,
-- so 2,222 edges carried 0 and 185 of the 375 works with more than one credit had the same number on
-- every edge. Byline order lives in `series[].credits[]` with the roles and arrives with them.
CREATE TABLE work_credit (
  id     INTEGER PRIMARY KEY,
  work   TEXT NOT NULL REFERENCES work(id)   ON DELETE CASCADE,
  credit TEXT NOT NULL REFERENCES credit(id) ON DELETE RESTRICT,
  role   TEXT                                   -- 著, 原作, 作画 … NULL where the field states none
);

CREATE UNIQUE INDEX work_credit_edge ON work_credit (work, credit, coalesce(role, ''));

CREATE TABLE work_publisher (
  work      TEXT NOT NULL REFERENCES work(id)      ON DELETE CASCADE,
  publisher TEXT NOT NULL REFERENCES publisher(id) ON DELETE RESTRICT,
  imprint   INTEGER REFERENCES imprint(id)         ON DELETE SET NULL,
  PRIMARY KEY (work, publisher)
);

-- ── what the compiler could not admit ──────────────────────────────────────────────────────────
--
-- STORE-PLAN §1a. An update runs unattended at 00:37 and must go on running, populating what it
-- can. A row the schema refuses either fails the job or is dropped in silence, and the second is
-- worse because nothing says it happened. So the row is written here with the constraint that
-- refused it, and the run continues.
--
-- THE TWO PATHS ANSWER DIFFERENTLY AND THAT IS THE WHOLE DESIGN. A REBUILD runs where somebody is
-- present, on every pull request and in the weekly equivalence job, and it FAILS on a refusal: the
-- loader is wrong until shown otherwise, which it has been every time so far. §2 refused 382 rows
-- and every one was my citation rule; §5a refused 3,690 and three of the four causes were mine.
-- The INCREMENTAL path quarantines so the run survives.
--
-- IT IS IN THE STORE AND NOT IN A FILE BESIDE IT, so "no data travels around the store" stays true
-- in the strong sense: even what could not be modelled is in it, in a table of its own.
--
-- A QUARANTINE THAT GROWS EVERY DAY MEANS THE SCHEMA IS ASSERTING SOMETHING THE DATA DOES NOT
-- SUPPORT, and the honest response then is to change the model rather than to keep filtering.
-- `rows the store could not admit` is what tells a bad week of captures from a wrong model.
CREATE TABLE quarantine (
  id         INTEGER PRIMARY KEY,
  -- WHERE IT WAS GOING, WHAT REFUSED IT, AND WHAT IT WAS. The row is kept as the loader had it, so
  -- a person can see the data rather than a description of it.
  target     TEXT NOT NULL,
  refusal    TEXT NOT NULL,
  row        TEXT NOT NULL,
  -- WHICH CAPTURE OR RECORD IT CAME FROM, in the loader's own words, so the deferral §9 writes can
  -- name the adapter without rediscovering it.
  came_from  TEXT,
  at         TEXT NOT NULL
);

CREATE INDEX quarantine_target ON quarantine (target);

-- ── the identity registry, which the store has never read ──────────────────────────────────────
--
-- THE ENTITY WAS ALWAYS THERE. §5d was first written asking for a ruling on whether a person is a
-- thing this project holds. The ruling is DEFINITIONS §4, identity is a human judgement, declared
-- and not inferred, and `data/identity/` is where it has lived all along. What was missing is that
-- this store never read it: `credit.surface` took one spelling off `credits.json` and made it the
-- key, and a name was resolved to a work by matching `work.title`, which is a join this project
-- makes nowhere else.

-- AN IDENTIFIER THAT WAS RETIRED INTO ANOTHER, and it has to load first. 158 addresses reach two
-- works and 5 spellings reach two credits, and every one is a retired id sitting beside its
-- survivor. `series.json:merged` carries 151 of them and `credits.json:merged` 6.
CREATE TABLE superseded (
  id     TEXT PRIMARY KEY,
  work   TEXT REFERENCES work(id)   ON DELETE CASCADE,
  credit TEXT REFERENCES credit(id) ON DELETE CASCADE,
  -- EXACTLY ONE SURVIVOR, and it is a real foreign key rather than a string nobody checks.
  CHECK ((work IS NULL) <> (credit IS NULL))
);

-- WHERE A WORK WAS FOUND, which is how this project identifies one. `works.yaml` holds 5,400 of
-- these across 3,240 works, `madb:` and `web:`, and 1,308 works carry more than one.
--
-- ONE ADDRESS REACHES ONE WORK, and that is the identity constraint the store has never had. It
-- holds only once retired identifiers are resolved through `superseded`, which is why that table
-- loads first.
CREATE TABLE work_anchor (
  scheme  TEXT NOT NULL,
  address TEXT NOT NULL,
  work    TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  PRIMARY KEY (scheme, address)
);

CREATE INDEX work_anchor_work ON work_anchor (work);

-- EVERY SPELLING THAT REACHES ONE PERSON. `credits.yaml` holds 2,473 across 2,255 credits and 220
-- carry more than one, so `credit.surface UNIQUE` was keeping one and discarding the rest: a byline
-- written `スズキフミエ` never reached `c00016`, whose kept spelling is `鈴木二三江`.
CREATE TABLE credit_spelling (
  spelling TEXT PRIMARY KEY,
  credit   TEXT NOT NULL REFERENCES credit(id) ON DELETE CASCADE
);

CREATE INDEX credit_spelling_credit ON credit_spelling (credit);

-- A DECISION THAT TWO IDENTIFIERS ARE ONE, OR THAT THEY ARE NOT, WITH THE REASONING. `delta.KINDS`
-- names `merge` and `divide`, and a store that can merge two identifiers and holds no record that
-- somebody ruled them apart will merge them again on the next run. `credit-rulings.yaml` holds 230
-- decisions and `credits.yaml` 7 homophones, which are the cases where the evidence says do not.
--
-- THE BASIS IS REQUIRED. A ruling with no reasoning is a preference, and the next pass has no way
-- to tell one from the other, which is the same argument `claim` makes for a researched note.
CREATE TABLE identity_ruling (
  id       INTEGER PRIMARY KEY,
  kind     TEXT NOT NULL CHECK (kind IN ('merge', 'keep', 'withdraw', 'not-a-credit', 'homophone')),
  subject  TEXT NOT NULL CHECK (subject IN ('credit', 'work')),
  -- WHAT WAS RULED ON, as the registry writes it: a reading two spellings share, or the shape of
  -- the difference between them.
  reading  TEXT,
  shape    TEXT,
  basis    TEXT NOT NULL,
  keeps    TEXT
);

CREATE TABLE identity_ruling_surface (
  ruling   INTEGER NOT NULL REFERENCES identity_ruling(id) ON DELETE CASCADE,
  spelling TEXT NOT NULL,
  PRIMARY KEY (ruling, spelling)
);

-- ── whether a work is still running, and on whose word ─────────────────────────────────────────
--
-- THE DISAGREEMENT RULE APPLIED TO SOMETHING OTHER THAN A NAME, which is what §5e found the model
-- could not say. Every one of the 3,040 works carries a state, 948 name what it rests on, and 271
-- hold competing source claims about whether the work is running, each with a source, a term, a
-- date and a page. `claim` is scoped to names by its own CHECK, so the store had one shape for one
-- kind of disagreement and none for this.
CREATE TABLE work_state (
  work  TEXT PRIMARY KEY REFERENCES work(id) ON DELETE CASCADE,
  -- WHAT THE INTERFACE DRAWS. `print` and `oneshot` describe a work with no serialisation to be
  -- running; `active`, `slow` and `dormant` are thresholds over the release feed; `completed` is a
  -- source saying so and `unknown` is the admitted silence.
  state TEXT NOT NULL CHECK (state IN
          ('print', 'oneshot', 'unknown', 'completed', 'active', 'dormant', 'slow')),
  -- WHY, IN THE PROJECT'S OWN WORDS: `the newest chapter is titled 最終話`. Prose, and it is prose
  -- in the corpus, so `state_claim` beside it is where the queryable form lives.
  basis TEXT
);

CREATE TABLE state_claim (
  id     INTEGER PRIMARY KEY,
  work   TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  -- WHAT THE SOURCE SAYS AND THE WORD IT USED. `says` is the reading we take, `term` is what the
  -- page printed, and keeping both is what lets a later reader disagree with the reading.
  says   TEXT,
  term   TEXT,
  url    TEXT,
  read   TEXT
);

CREATE UNIQUE INDEX state_claim_one ON state_claim (work, source, coalesce(says, ''));

-- HOW A WORK IS PRESENTED, AND WHETHER IT IS PRESENTED AT ALL. `marketing_label` is publisher-side
-- labelling under DEFINITIONS §4, which is a different question from the shelf a work was admitted
-- on, and `visibility` is the §13 register: `rebutted` and `marginal`.
CREATE TABLE work_presentation (
  work       TEXT PRIMARY KEY REFERENCES work(id) ON DELETE CASCADE,
  label      TEXT,
  visibility TEXT CHECK (visibility IS NULL OR visibility IN ('rebutted', 'marginal')),
  -- HOW THE LABEL WAS ARRIVED AT, which the corpus states as a source, a page, a date and a note.
  source     TEXT,
  url        TEXT,
  retrieved  TEXT,
  note       TEXT
);

-- ── the strings a reader is shown ───────────────────────────────────────────────────────────────
--
-- A CLAIM IS ABOUT A NAME AND NOT ABOUT A THING, which STORE-PLAN §5 is where the schema stopped
-- pretending otherwise. `claim` used to hold `subject_kind` and an identifier, so a name that
-- resolved to nothing had nowhere to hang: 890 readings and every one of the 4,174 English
-- renderings the corpus holds were skipped by the loader, silently, with no refusal and no count.
-- `data/names/*.yaml` is keyed by the NAME, `feed/names.json` is keyed by the name, and this table
-- is the one keyed thing both of them are talking about.
--
-- THE KEY IS THE FOLD, `facts/namekey.fold`, because that is what the site joins on. An archived
-- month is never rewritten, so a release from March finds today's English for its work by folding
-- the title it recorded. Keying on the raw spelling would break that join for every name whose
-- source wrote it with a full-width space.
--
-- IT HOLDS MORE THAN NAMES, and the kinds say which. A chapter label, a magazine issue and a credit
-- line are strings the site must render in Latin and nothing identifies them; they carry
-- romanisations and no claims. Filing them here rather than in a map of their own is what makes
-- `floor` and `phrases` answerable at all.
CREATE TABLE surface (
  id     INTEGER PRIMARY KEY,
  kind   TEXT NOT NULL CHECK (kind IN
           ('title', 'author', 'publisher', 'imprint', 'credit-line', 'phrase', 'floor')),
  folded TEXT NOT NULL,

  -- WHAT IT NAMES IS AN EDGE AND NOT A COLUMN, which is §5d. Three nullable columns here said a
  -- name names at most one thing, and `百合漫画短編集` names w01990 and w02284 while `Girls Love`
  -- names w01001 and w01108. A column could hold only the first, so one work of each pair took the
  -- English and the reading and the other got neither. `names` below is the edge.

  -- WHAT IS TRUE OF THE NAME ITSELF rather than of any one claim about it.
  --
  --   verified       somebody has ruled on this record. NULL where nobody has looked, which is not
  --                  the same as looked and unsure, and the interface's mark turns on the
  --                  difference.
  --   uncertain      the reading was assembled a character at a time, which is weaker than a guess
  --                  at the whole word.
  --   ordinary       the analyser read ordinary vocabulary rather than a coinage, so its answer is
  --                  not the guess the mark exists to flag. `analyser_vocabulary.py` is its one
  --                  producer and this is where its answer lands.
  --   transliterates the kana are themselves a transliteration, so romanising them takes a reader
  --                  further from the name: ステファン・セジク is Stjepan Šejić.
  -- `undivided` IS DELIBERATELY NOT A COLUMN. A person's romanisation runs the family and given
  -- names together where nothing states the parting point, and the site ships that as a flag; the
  -- store holds the reading itself and whether the credit is a person, which is everything the
  -- flag is computed from. A column would be a second copy of an answer already in the rows.
  verified       INTEGER CHECK (verified IN (0, 1)),
  uncertain      INTEGER NOT NULL DEFAULT 0 CHECK (uncertain IN (0, 1)),
  ordinary       INTEGER NOT NULL DEFAULT 0 CHECK (ordinary  IN (0, 1)),
  transliterates TEXT,

  -- ONE TITLE STANDING FOR ANOTHER, which is how an edition marker keeps its work's English.
  alias_of INTEGER REFERENCES surface(id) ON DELETE SET NULL,
  CHECK (alias_of IS NULL OR alias_of <> id),

  UNIQUE (kind, folded),
  -- SO THE EDGE CAN NAME BOTH AT ONCE. A composite foreign key needs this to point at.
  UNIQUE (id, kind)
);

-- WHAT A NAME NAMES. Many to many in both directions: one folded title names two works, and one
-- work is reached by several spellings.
--
-- THE KIND TRAVELS WITH THE EDGE so the pair can be a foreign key, which is what keeps a title from
-- naming a person. A string that is not a name, a chapter label or a credit line, reaches nothing
-- and has no row here at all.
CREATE TABLE names (
  surface   INTEGER NOT NULL,
  kind      TEXT NOT NULL,
  work      TEXT REFERENCES work(id)      ON DELETE CASCADE,
  credit    TEXT REFERENCES credit(id)    ON DELETE CASCADE,
  publisher TEXT REFERENCES publisher(id) ON DELETE CASCADE,
  CHECK (CASE kind
           WHEN 'title'     THEN work      IS NOT NULL AND credit IS NULL AND publisher IS NULL
           WHEN 'author'    THEN credit    IS NOT NULL AND work   IS NULL AND publisher IS NULL
           WHEN 'publisher' THEN publisher IS NOT NULL AND work   IS NULL AND credit    IS NULL
           ELSE 0 END),
  FOREIGN KEY (surface, kind) REFERENCES surface (id, kind) ON DELETE CASCADE
);

-- THE BYLINE AS A WORK PRINTS IT. 3,399 credit-line surfaces exist and nothing connected one to the
-- work it appeared on, and the fix is an edge rather than a column on `surface`, because one line
-- appears on many works. `credit_division` holds how it divides; this holds where it was seen.
CREATE TABLE work_byline (
  work    TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  surface INTEGER NOT NULL REFERENCES surface(id) ON DELETE CASCADE,
  PRIMARY KEY (work, surface)
);

CREATE UNIQUE INDEX names_edge ON names
  (surface, coalesce(work, ''), coalesce(credit, ''), coalesce(publisher, ''));
CREATE INDEX names_work      ON names (work);
CREATE INDEX names_credit    ON names (credit);
CREATE INDEX names_publisher ON names (publisher);

-- THE READING SPELT IN LATIN, IN THE READER'S THREE STYLES. It is not a claim about a name and must
-- not be filed as one: `build.py` says so where it assembles `en_forms`, and a romanisation has no
-- source to cite because it is a function of the reading. One row per style, so "which names differ
-- between the macron and the double spelling" is a query rather than a comparison of three maps.
CREATE TABLE romanisation (
  surface INTEGER NOT NULL REFERENCES surface(id) ON DELETE CASCADE,
  style   TEXT NOT NULL CHECK (style IN ('plain', 'macron', 'double')),
  value   TEXT NOT NULL,
  PRIMARY KEY (surface, style)
);

-- FURIGANA, AS SPANS OVER THE SURFACE AND NOT AS A BLOB. `[["最強", "さいきょう"], [" ～", null]]`
-- is a list of pairs in the JSON, and a list of pairs in a TEXT column is the carrier this store
-- exists to stop being. A span with no reading is a run of the surface that takes none.
CREATE TABLE ruby (
  surface INTEGER NOT NULL REFERENCES surface(id) ON DELETE CASCADE,
  seq     INTEGER NOT NULL,
  text    TEXT NOT NULL,
  reading TEXT,
  PRIMARY KEY (surface, seq)
);

-- HOW A CREDIT LINE DIVIDES INTO PEOPLE. `creditline._divide` owns the rule and this is where its
-- answer lands, so the division a page draws is the division the name store is keyed on.
CREATE TABLE credit_division (
  surface INTEGER PRIMARY KEY REFERENCES surface(id) ON DELETE CASCADE,
  -- WHAT THE FIELD PUTS BETWEEN TWO PEOPLE, so a recomposed byline reads as the field it replaces.
  joiner  TEXT NOT NULL,
  -- THE DIVISION DOES NOT ACCOUNT FOR EVERYTHING THE FIELD SAYS, which is what stops the interface
  -- rebuilding a byline out of an incomplete answer.
  partial INTEGER NOT NULL DEFAULT 0 CHECK (partial IN (0, 1))
);

CREATE TABLE credit_part (
  surface INTEGER NOT NULL REFERENCES credit_division(surface) ON DELETE CASCADE,
  seq     INTEGER NOT NULL,
  name    TEXT NOT NULL,
  role    TEXT,
  PRIMARY KEY (surface, seq)
);

-- A SUBSTRING SAYING THE SAME THING TWICE: a reading printed beside the name it reads. Taken off an
-- English page, where kana beside a romanisation is a second copy of a name in the wrong script.
CREATE TABLE credit_dropped (
  surface INTEGER NOT NULL REFERENCES credit_division(surface) ON DELETE CASCADE,
  text    TEXT NOT NULL,
  PRIMARY KEY (surface, text)
);

-- ── what is claimed about a name, and on whose word ─────────────────────────────────────────────
-- THE FLATTENING THIS REPLACES. A reading lived as `reading`, `reading_basis`, `reading_source`,
-- `reading_source_kind`, `reading_at`, `reading_url`, `reading_note`, `reading_boundary` and
-- `reading_conflicts` on one record. That shape is why 293 divisions sat in `reading_note` prose
-- while `reading_boundary` was empty: two slots for one fact, and prose is not queryable.
--
-- One row is one claim. A second claim about the same name is a second ROW, so a conflict is data
-- and not a nested list, and "which claims rest on a community database" is one query.
--
-- `en_forms` IS THIS TABLE READ BACK. The site ships every English form it holds keyed by what
-- makes it that form, and the one it shows is the highest-ranked of them. Both are the same rows
-- under `basis_for_predicate`'s ranking, which is why neither needs a column of its own.

CREATE TABLE claim (
  id           INTEGER PRIMARY KEY,
  surface      INTEGER NOT NULL REFERENCES surface(id) ON DELETE CASCADE,
  -- `romanisation` WAS HERE AND WAS UNSTATEABLE. §5 gave it a table of its own, because it is a
  -- function of the reading and rests on no source, and `basis_for_predicate` has no row for it, so
  -- the composite key below refused every claim the enum declared legal. A schema contradicting
  -- itself is a fault whatever the row count, which is why this went in §5a and `serialisation`,
  -- an edition kind nothing has produced yet, did not.
  predicate    TEXT NOT NULL CHECK (predicate IN ('reading', 'division', 'english')),
  value        TEXT NOT NULL,

  -- HOW WE CAME BY IT. `facts/reading` and `facts/division` rule on which basis admits which kind,
  -- and `basis_admits_kind` below is that ruling as a table instead of as a Python dict.
  basis        TEXT NOT NULL REFERENCES basis(name),
  source       TEXT,                            -- who said so, in their own words
  source_kind  TEXT REFERENCES source_kind(name),
  retrieved    TEXT,                            -- ISO 8601 date the answer was obtained
  -- WHEN A PERSON LOOKED AT IT, which is a different date from the one above and is the one a
  -- citation shows. `provenance.PARTS` names both and the loader kept only the first.
  reviewed     TEXT,
  url          TEXT,
  -- AN ISBN IS A CITATION WHERE A URL IS NOT. openBD answers by ISBN and its only address is an API
  -- query, which is not a page to send a reader to; the book it names is something they can act on.
  isbn         TEXT,

  -- WHY THE REVIEWER CONCLUDED IT. `researched` demands this and `curate.problems` enforces it in
  -- Python; here it is a CHECK, so a researched claim with no note cannot be written at all.
  note         TEXT,

  -- WHETHER THIS IS THE ANSWER THE RECORD STANDS BEHIND. §1 keeps a displaced claim rather than
  -- discarding it, and until §5c nothing said which of two rows is the live one, so 638 surfaces
  -- carried a `verified` flag beside two or more readings with no way to tell which one a person
  -- ruled on. A conflicts entry is a claim somebody moved aside, and saying so costs one column.
  displaced    INTEGER NOT NULL DEFAULT 0 CHECK (displaced IN (0, 1)),

  CHECK (basis <> 'researched' OR note IS NOT NULL),

  -- A STATED CLAIM NAMES WHERE IT CAME FROM. This is the stage-three invariant as a constraint:
  -- a reading a source printed is an INPUT, the repository is its only copy, and one without an
  -- address cannot be checked, refreshed or argued with.
  CHECK (basis <> 'stated' OR url IS NOT NULL OR isbn IS NOT NULL OR source_kind = 'derived'),

  -- A BASIS BELONGS TO A CLAIM, and the pair is what `basis_for_predicate` admits. This is what
  -- makes an English name resting on `analyser` unstateable: the vocabularies are different and
  -- the schema now knows which is which instead of accepting either for either.
  FOREIGN KEY (basis, predicate) REFERENCES basis_for_predicate (basis, predicate)
);

-- WHAT IDENTIFIES A CLAIM, WHICH IT HAD NOTHING OF. Ten groups of rows were byte-identical on all
-- eleven non-id columns, so `delta.write` had no key to address one by and neither an upsert nor a
-- retraction could be expressed. That is what stood between this store and STORE-PLAN §7, since the
-- table holding most of the corpus could be inserted into and never changed.
--
-- WHAT IT IS: the name, what is being said about it, the answer, on what basis, and by whom. Two
-- rows agreeing on all five are one claim said twice, and 51 of those existed, every one a
-- conflicts list carrying a value the live claim already held. Two sources giving the same answer
-- on the same basis stay two rows, because "which claims rest on a community database" counts them
-- separately and should.
--
-- `coalesce(source, '')` BECAUSE 20 CLAIMS NAME NONE, and a NULL in a unique index constrains
-- nothing, which is the same trap `work_credit` was in.
CREATE UNIQUE INDEX claim_identity ON claim
  (surface, predicate, value, basis, coalesce(source, ''));
CREATE INDEX claim_surface ON claim (surface, predicate);
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
  --
  -- THEY ARE QUESTIONS ABOUT A READING, and an English basis has no answer to any of them: nothing
  -- about `licensed` says whether it may lend a division. NULL is that answer, and it is all four
  -- or none, so a row cannot be half filled in and read as though the blanks meant no.
  cited   INTEGER CHECK (cited   IN (0, 1)),
  donates INTEGER CHECK (donates IN (0, 1)),
  marked  INTEGER CHECK (marked  IN (0, 1)),
  counted INTEGER CHECK (counted IN (0, 1)),
  CHECK ((cited IS NULL) = (donates IS NULL)
     AND (cited IS NULL) = (marked  IS NULL)
     AND (cited IS NULL) = (counted IS NULL))
);

-- WHICH BASIS MAY STAND BEHIND WHICH CLAIM, AND WHICH ANSWER WINS. `facts/division.rank` orders the
-- readings and `facts/reading.en_rank` orders the English names, and they are different vocabularies
-- that overlap on one word: `stated` means a source printed the kana, and it also means a source
-- printed the English. Nothing before this could tell a claim resting on the wrong one.
--
-- THE RANK IS WHY `en` NEEDS NO COLUMN. The site shows the highest-ranked English form it holds and
-- ships the rest beside it; with the order here as data, both are one query over `claim`.
CREATE TABLE basis_for_predicate (
  basis     TEXT NOT NULL REFERENCES basis(name) ON DELETE CASCADE,
  predicate TEXT NOT NULL CHECK (predicate IN ('reading', 'division', 'english', 'romanisation')),
  rank      INTEGER NOT NULL,
  PRIMARY KEY (basis, predicate)
);

CREATE TABLE source_kind (
  name TEXT PRIMARY KEY
);

-- A SOURCE THAT IS THE NAME ITSELF. `surface` means the name is already kana and nothing was looked
-- up; `title-furigana` means the title prints how a word in it is read. `provenance.SELF_SOURCED`
-- rules on both and `_kind_of` normalises them to the kind `derived`, which is true and which threw
-- away the reason. 138 claims then read as resting on evidence their basis does not admit, because
-- nothing left in the row said the evidence is the name. Held as a table so the question can be
-- asked in SQL without a second copy of the vocabulary.
CREATE TABLE self_sourced (
  source TEXT PRIMARY KEY
);

-- WHICH EVIDENCE A BASIS ADMITS, SCOPED BY THE CLAIM IT STANDS BEHIND. `facts/reading` holds two
-- attribution tables, one for readings and one for English names, and this was filled from the
-- reading one alone. So 4,749 of the 10,597 claims carrying a source kind held a pair it forbade,
-- 2,767 of them `('translated','derived')`, which the ENGLISH table admits and this table had never
-- been told about. Loading both takes it to 1,227.
--
-- IT IS NOT A FOREIGN KEY YET, AND 105 ROWS ARE WHY. 102 are English romanisations citing a
-- community database, where `ATTRIBUTION` admits `derived` for `romaji` and nothing else; the
-- project owner ruled on 2026-08-09 that Wikidata may raise the floor on a romanisation, and the
-- table was written before that. 2 are publisher names on `official-jp` citing the national
-- library, and 1 is a kana surface citing a platform. `claims whose evidence their basis does not
-- admit` counts them, and the composite key goes on `claim` when it reaches 0, which is the only
-- time a constraint is free to adopt.
--
-- WHAT THIS FIXES TODAY IS §13. A table nothing consumes reads as a control that is working, and
-- until now nothing read this one at all.
CREATE TABLE basis_admits_kind (
  basis       TEXT NOT NULL REFERENCES basis(name)       ON DELETE CASCADE,
  predicate   TEXT NOT NULL,
  source_kind TEXT NOT NULL REFERENCES source_kind(name) ON DELETE CASCADE,
  PRIMARY KEY (basis, predicate, source_kind),
  FOREIGN KEY (basis, predicate) REFERENCES basis_for_predicate (basis, predicate)
);

-- ── the books, and the events that dated them ───────────────────────────────────────────────────
--
-- A PRINTING AND A DELIVERY ARE DIFFERENT EVENTS ABOUT THE SAME BOOK, and until §5b this table
-- could hold only one of them. 812 volumes state a printing date and a shop delivery date that
-- differ; holding both took two rows, `isbn UNIQUE` refused the second, and dropping the ISBN from
-- it left nothing tying the two together. So the loader's `if/elif` keeping the printing and
-- discarding the delivery was forced by the shape rather than chosen, and the comment here cited
-- `a delivery date never stands beside a printing` as its authority, which is an invariant about
-- one WORK's date field and says nothing about two rows.
--
-- SO THE BOOK AND THE EVENT ARE TWO TABLES. `volume` is the thing on a shelf and `edition` is
-- something that happened to it on a date, which is what `kind` was always describing.

CREATE TABLE volume (
  id      INTEGER PRIMARY KEY,
  work    TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  isbn    TEXT UNIQUE,

  -- WHAT A VOLUME IS CALLED AND WHERE IT SITS ARE TWO FACTS. `volume` is a position in a run and
  -- an integer answers it. A DESIGNATION is the word the publisher uses: `上`, `創刊号`,
  -- `2017年1月号`. 983 volumes carry one and no integer can hold it, which is STORE-PLAN §3.
  --
  -- NEITHER IS REQUIRED AND NEITHER EXCLUDES THE OTHER. `build.volume_number` reads 創刊号 as the
  -- first issue, so a designation can acquire a position.
  volume       INTEGER CHECK (volume IS NULL OR volume >= 0),
  designation  TEXT

  -- THERE IS NO KEY HERE BEYOND THE ISBN AND THAT IS THE DATA'S DOING, not an omission. 92 rows
  -- share a work, a position and a designation with another, 40 of them holding no ISBN at all:
  -- 13 works carry a reissue, so w00174 legitimately holds volume 2 twice at different ISBNs, and
  -- for the 40 nothing in the corpus distinguishes the two records. A UNIQUE over the three would
  -- refuse a reissue, which is a real thing this project holds.
);

CREATE INDEX volume_work ON volume (work);

-- A DATED EVENT ABOUT ONE BOOK. One of each kind per volume, so a printing and a delivery sit
-- beside each other and neither displaces the other.
CREATE TABLE edition (
  id      INTEGER PRIMARY KEY,
  volume  INTEGER NOT NULL REFERENCES volume(id) ON DELETE CASCADE,
  kind    TEXT NOT NULL CHECK (kind IN ('printing', 'shop-delivery', 'serialisation')),
  dated   TEXT,

  -- WHAT KIND OF EVIDENCE THE DATE RESTS ON, following `claim`'s pattern rather than reusing its
  -- table: `claim` is scoped to what a NAME is, by its own CHECK on predicate. A closed set,
  -- because a basis nobody can name is a basis nobody can weigh.
  dated_basis  TEXT CHECK (dated_basis IS NULL OR dated_basis IN
                 ('national-library', 'openbd-registration', 'madb-tankobon', 'shop-delivery')),

  -- A DATE WITH NO PAGE BEHIND IT is what `per-book dates cite their page` refuses.
  cite    TEXT,
  CHECK (dated IS NULL OR cite IS NOT NULL),

  UNIQUE (volume, kind)
);

-- AN ISBN IS A KEY INTO EVERY DATED REGISTRY THERE IS, so a volume holding one and no date means
-- nobody asked. That was `CHECK (isbn IS NULL OR dated IS NOT NULL)` while both facts sat on one
-- row, and no CHECK can reach across two tables, so it is a standing question now:
-- `volumes with an isbn and no date`, which `check.py` has held at 0 since §3 and `delta` asks of
-- the store. The constraint is weaker and the loss is recorded rather than absorbed.

CREATE INDEX edition_volume ON edition (volume, kind);

-- ── what a platform offers, and what it published ──────────────────────────────────────────────
--
-- A PLATFORM IS IDENTIFIED BY ITS NAME AND NOT BY THE ADAPTER THAT READ IT. `plat` on a release is
-- the capture route: コミックDAYS arrives as both `comic-days` and `backfill`, サンデーうぇぶり as
-- `sundaywebry` and `backfill`, 一迅プラス as `ichicomi` and `claim-resolved`. Six names carry two
-- slugs each, so keying on the slug would split one platform into two.
CREATE TABLE platform (
  name TEXT PRIMARY KEY
);

-- WHAT ONE PLATFORM HOLDS OF ONE WORK. `schema.sql` said this before the table existed: what a
-- platform holds, what it charges for and when it last updated are properties of that platform's
-- OFFER and not of the work, which is why they cannot live on `work`.
-- AN INSTALMENT IS NOT A CHAPTER, and naming it `chapters` is how the two got confused. What a
-- platform lists is what it will sell you separately: often a PART of a chapter, sometimes a
-- notice, a special or a read-through that is no chapter at all. 彼女が先輩にNTRれたので ran 24
-- instalments, 22 of them free, against 11 chapters of which 10 were free, and the site published
-- `11/11 free` by treating one number as the other.
--
-- AND THERE ARE THREE COUNTS, NOT TWO. Instalments are what a platform sells; NUMBERED CHAPTERS
-- are the work's own 第1話 onward, fewer where a chapter is split to be sold in parts; LOGICAL
-- UNITS are everything the work contains, MORE than the numbering reaches, because a volume
-- carries omake, extras and afterwords that are never numbered. This store holds the first only,
-- and nothing in the corpus states the other two. docs/GAPS.md.
--
-- SO THE COLUMN SAYS WHAT IT COUNTS. `instalments` is what this platform offers as separate items,
-- and `free`, `free_timed` and `priced` count those items and not chapters.
--
-- AN OFFER IS A LISTING, NOT A PLATFORM. Keyed `(work, platform)` this refused 11 rows, and every
-- one was right to exist: 不器用ビンボーダンス has three ニコニコ漫画 listings at three addresses,
-- 100, 100 and 67 instalments, and 田所さん has two. One platform can carry one work at several
-- addresses and each is its own offer. Every one of the 1,820 states a url, so the address is an
-- identity the data actually holds.
CREATE TABLE offer (
  id         INTEGER PRIMARY KEY,
  work       TEXT NOT NULL REFERENCES work(id)        ON DELETE CASCADE,
  platform   TEXT NOT NULL REFERENCES platform(name)  ON DELETE RESTRICT,
  url        TEXT NOT NULL,
  instalments INTEGER NOT NULL DEFAULT 0 CHECK (instalments >= 0),
  free       INTEGER NOT NULL DEFAULT 0 CHECK (free       >= 0),
  free_timed INTEGER NOT NULL DEFAULT 0 CHECK (free_timed >= 0),
  priced     INTEGER NOT NULL DEFAULT 0 CHECK (priced     >= 0),
  latest     TEXT,
  -- THE PLATFORM LISTS MORE THAN WE HOLD, which the interface already draws as `90+`.
  partial    INTEGER NOT NULL DEFAULT 0 CHECK (partial IN (0, 1)),
  retrieved  TEXT,
  UNIQUE (work, platform, url)
);

-- THE ACCESS COUNTS ARE NOT CONSTRAINED TO SUM TO `instalments`, and that is measured rather than
-- assumed: 87 of 1,820 offers state modes adding to more than the instalments counted, and others
-- state fewer. Both are real and the interface says so in its own words, `12 free · 3 to buy · 5 not
-- recorded`. A CHECK here would refuse 87 rows the corpus is right to hold.

-- ONE RELEASE IS ONE EVENT ON ONE PLATFORM. The id is the platform's own, and the feed serves 13
-- of them twice because the rolling window overlaps the archived month; that is a property of how
-- the feed is SPLIT, so the loader collapses them knowingly rather than letting the key swallow it.
CREATE TABLE release (
  id         TEXT PRIMARY KEY,
  -- NULLABLE, AND THE PLAN SAID OTHERWISE. STORE-PLAN §4 expected a release naming a work we do
  -- not hold to be refused. Measured, 971 of 974 resolve by the identifier the release carries or
  -- by the folded title, and the 3 that do not carry no identifier at all: they are the GigaViewer
  -- works WORKS-PLAN §3 left without a page. A release is an event somebody observed, and which
  -- work it belongs to is a join that may not have been made. Refusing it would push a fact the
  -- site is served out of the store, which is the one thing this model may not do. So the foreign
  -- key still refuses a DANGLING work, and a release placed with NO work is admitted and counted.
  work       TEXT     REFERENCES work(id)       ON DELETE CASCADE,
  platform   TEXT NOT NULL REFERENCES platform(name) ON DELETE RESTRICT,
  -- THE PLATFORM'S OWN LABEL FOR THE INSTALMENT: `第72話`, `読切`, `最終話`, `#1(1)`. It is not a
  -- chapter number and must not be read as one.
  instalment TEXT,
  published  TEXT,
  url        TEXT,
  kind       TEXT,
  first_seen TEXT
);

CREATE INDEX release_work ON release (work, published);
CREATE INDEX offer_platform ON offer (platform);

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
--     SELECT surface, predicate, count(DISTINCT value) n FROM claim
--     GROUP BY surface, predicate HAVING n > 1;
--
--   which English name does a title show, and what else do we hold for it
--     SELECT c.value, c.basis FROM claim c
--     JOIN basis_for_predicate b ON b.basis = c.basis AND b.predicate = c.predicate
--     WHERE c.surface = ? AND c.predicate = 'english' ORDER BY b.rank DESC;
--
--   which names does the corpus identify nothing for
--     SELECT folded FROM surface WHERE kind IN ('title','author','publisher')
--     AND work IS NULL AND credit IS NULL AND publisher IS NULL;
--
-- Each of those is a script today, and the last two have no script at all.
