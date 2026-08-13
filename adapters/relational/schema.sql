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

-- A DATE SAYS IT IS A DATE, §5k. Thirteen columns across ten tables were unconstrained TEXT and
-- `'yesterday afternoon'` inserted into any of them. Every value is well formed today, including
-- the partial `YYYY-MM` that `edition.dated` and `work.first_publication` carry beside whole dates,
-- so the shape is free to adopt, which is the only time a constraint is. Written per column rather
-- than as a domain, because SQLite has none and a shared function would be a second home.

-- ── the things that have identity ───────────────────────────────────────────────────────────────
-- OPAQUE IDS, because a name is not an identity. Two artists share a pen name, one artist changes
-- theirs, and a work is reissued under a title its author never used. `w#####`, `c#####`, `h#####`
-- are the project's existing identifiers and they carry no meaning on purpose.

CREATE TABLE work (
  id                TEXT PRIMARY KEY CHECK (id GLOB 'w[0-9][0-9][0-9][0-9][0-9]'),
  title             TEXT NOT NULL CHECK (title <> ''),
  first_publication TEXT CHECK (first_publication IS NULL OR first_publication GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR first_publication GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),  -- ISO 8601, whole or partial
  -- A LIST HOLDING NULL MAKES A CHECK PASS ON EVERYTHING, since `x IN (a, b, NULL)` answers NULL
  -- for an x that matches neither and a CHECK passes on NULL. `'banana'` inserted here for as long
  -- as this column has existed. Every comparable column omits it; §5a is where this one did.
  first_event       TEXT CHECK (first_event IS NULL OR first_event IN ('publication', 'shop-delivery')),
  -- NULLABLE, BECAUSE LOOKED AND FALSE IS NOT THE SAME AS NEVER LOOKED. It was NOT NULL DEFAULT 0
  -- and 0 on every row, of which 2,459 are a record stating false and 579 have no record at all.
  -- STANDING-INSTRUCTIONS §5: absence is a state and gets its own value.
  explicit_content  INTEGER CHECK (explicit_content IN (0, 1))

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
-- WHOSE SHELF ADMITS A WORK, AND WHICH SHELF IT IS. `facts/inclusion.SHELVES` states the pair and
-- `admission` held both, so the shelf was functionally dependent on the comparator rather than on
-- the row: the same two strings repeated across 1,867 rows. §5j made it a table, which is where the
-- ruling already lived, and the column a foreign key.
CREATE TABLE comparator (
  name  TEXT PRIMARY KEY,
  shelf TEXT NOT NULL
);

CREATE TABLE admission (
  id         INTEGER PRIMARY KEY,
  -- KEYED ON THE RECORD, like `work_origin` and for the same reason: `works.json` carries these per
  -- catalogue record, and holding them per work put one record's grounds on another's row. §5c
  -- deduped 20 rows that were the same grounds seen through two records; they are two records'
  -- grounds and the dedupe was hiding the layer rather than a duplicate.
  record     TEXT NOT NULL,
  work       TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  comparator TEXT REFERENCES comparator(name),
  shop_url   TEXT,
  url        TEXT,
  -- WHICH PAGE OF THE SHELF THE WORK WAS FOUND ON, which 1,632 grounds state and is how a reader
  -- returns to the listing that admitted it.
  page       INTEGER,
  retrieved  TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  note       TEXT
);

-- ADDRESSABLE, for the reason `volume` is. §5c added this table and §5g gave it a key.
CREATE UNIQUE INDEX admission_one ON admission
  (record, coalesce(comparator, ''), coalesce(url, ''));

CREATE INDEX admission_work ON admission (work);

-- A SOURCE SAYING A RUN IS COMPLETE AT n VOLUMES, which is a different statement from a catalogue
-- counting the volumes it holds. `record.volume_count` is the second; this is the first, and §5c
-- filled it from both so 2,574 rows said what 330 of them meant.
-- A COLUMN THAT MEANT TWO THINGS, §5i. `source` held a source on 329 rows and a RECORD identifier
-- on 2,244, because the loader fell back to the record when no claim named a source, and the unique
-- index keyed on it. So two records from one catalogue stating one count were two rows rather than
-- the one disagreement this table exists to hold, and "which sources disagree about this run" could
-- not be asked at all.
--
-- THE CLAIM BELONGS TO THE RECORD THAT MAKES IT, so that is the key, and `source` says who the
-- record got it from where it says.
CREATE TABLE volume_claim (
  id         INTEGER PRIMARY KEY,
  work       TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  record     TEXT NOT NULL,
  volumes    INTEGER NOT NULL CHECK (volumes >= 0),
  source     TEXT,
  provenance TEXT,
  retrieved  TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

CREATE UNIQUE INDEX volume_claim_one ON volume_claim (record);

CREATE TABLE credit (
  id      TEXT PRIMARY KEY CHECK (id GLOB 'c[0-9][0-9][0-9][0-9][0-9]'),
  surface TEXT NOT NULL UNIQUE,                 -- the name as a source writes it
  -- A PERSON, AN ORGANISATION, A VENUE. `entities` decides and `credits.json` records the decision,
  -- so a query can ask how many works name no person without re-deciding it. The vocabulary is the
  -- one the corpus actually uses: I guessed a wider one first and 64 rows were refused for holding
  -- the right answer.
  kind    TEXT NOT NULL CHECK (kind IN ('person', 'organisation', 'venue', 'unknown')),
  -- WHAT THE REGISTRY CALLED IT, WHICH IS FINER THAN THE SHAPE A PAGE NEEDS. `desk`, `project`,
  -- `company`, `studio`, `committee`, `magazine`, `school`: 24 credits state one, and `kind` above
  -- is the four-way answer a renderer asks for. §6 needs both, because `credits.json` ships both
  -- and an emitter cannot invent the finer one back out of the coarser.
  registered TEXT
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
  -- A LINE INSIDE A LINE. 裏少年サンデーコミックス sits under 少年サンデーコミックス. The registry
  -- states the parent by NAME and this column repeated it, 23 of them with one that resolved to
  -- nothing. §5j: a parent is an imprint, so it is a foreign key into the table it already sits in.
  parent    INTEGER REFERENCES imprint(id) ON DELETE SET NULL,
  -- AND THE NAME THE REGISTRY STATED, because a parent need not be a line the registry carries.
  -- §5j made this a foreign key and 41 of the 42 resolved; the forty-second is
  -- `集英社ホームコミックス`, which matches no imprint, and a publisher page shows it. Dropping the
  -- name to keep only the key would have taken a fact off the page to satisfy a constraint, which
  -- §6 caught by emitting the file and finding one house short of what the compiler wrote.
  parent_name TEXT,
  CHECK (parent IS NULL OR parent <> id),
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

-- WHICH HOUSE, AND IN WHICH SEAT. §2 read this off `publishers.json`'s `works` list, which counts a
-- house named in ANY seat, so a distributor sat here as though it had published the book. §6 builds
-- it from `print_party`, where the seat is on the row, and the seat comes with it: dropping the
-- distributor edges would have lost 193 facts to make a column tidier.
CREATE TABLE work_publisher (
  work      TEXT NOT NULL REFERENCES work(id)      ON DELETE CASCADE,
  publisher TEXT NOT NULL REFERENCES publisher(id) ON DELETE RESTRICT,
  seat      TEXT NOT NULL CHECK (seat IN ('publisher', 'distributor')),
  imprint   INTEGER REFERENCES imprint(id)         ON DELETE SET NULL,
  PRIMARY KEY (work, publisher, seat)
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
  at         TEXT NOT NULL CHECK (at IS NULL OR at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
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
  id        TEXT PRIMARY KEY,
  work      TEXT REFERENCES work(id)      ON DELETE CASCADE,
  credit    TEXT REFERENCES credit(id)    ON DELETE CASCADE,
  publisher TEXT REFERENCES publisher(id) ON DELETE CASCADE,
  -- EXACTLY ONE SURVIVOR, and it is a real foreign key rather than a string nobody checks.
  CHECK (((work IS NOT NULL) + (credit IS NOT NULL) + (publisher IS NOT NULL)) = 1)
);

-- WHERE A WORK WAS FOUND, which is how this project identifies one. `works.yaml` holds 5,400 of
-- these across 3,240 works, `madb:` and `web:`, and 1,308 works carry more than one.
--
-- ONE ADDRESS REACHES ONE WORK, and that is the identity constraint the store has never had. It
-- holds only once retired identifiers are resolved through `superseded`, which is why that table
-- loads first.
CREATE TABLE work_anchor (
  scheme  TEXT NOT NULL REFERENCES anchor_scheme(name),
  address TEXT NOT NULL,
  work    TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  PRIMARY KEY (scheme, address)
);

CREATE INDEX work_anchor_work ON work_anchor (work);

-- EVERY SPELLING THE REGISTRY RESOLVES TO ONE PERSON. `credits.yaml` holds 2,473 across 2,255
-- credits and 220 carry more than one, so `credit.surface UNIQUE` was keeping one and discarding
-- the rest: a byline written `スズキフミエ` never reached `c00016`, whose kept spelling is `鈴木二三江`.
--
-- A CREDIT'S OWN TITLE IS NOT NECESSARILY IN HERE, and 130 are not. `二三　夏一` is titled with a
-- full-width space the registry folds out, so the spelling that reaches it is `二三夏一`. §5h read
-- the absence as a gap and put the titles in, which made this table disagree with the one producer
-- of the answer. `credit.surface` is what a page is headed with; this is what finds it.
CREATE TABLE credit_spelling (
  -- AN ID, SO THE ORDER THE REGISTRY WROTE THEM IN SURVIVES. `feed/credit-keys.json` is this table
  -- and nothing else, and a byte comparison against what the compiler wrote cares about the order
  -- even though a search does not.
  id       INTEGER PRIMARY KEY,
  spelling TEXT NOT NULL UNIQUE,
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
  shape    TEXT REFERENCES ruling_shape(name),
  -- WHICH SPELLING THE RULING IS FILED UNDER, which is what identifies it. Two `withdraw` rulings
  -- carry no reading and no survivor and are told apart by what they were about, so the parent has
  -- to say. It is the same relation `credit.surface` has to `credit_spelling`: a filing spelling
  -- beside the full set, rather than a second copy of the set.
  about    TEXT NOT NULL CHECK (about <> ''),
  basis    TEXT NOT NULL CHECK (basis <> ''),
  -- WHAT THE RULING PRESERVES, AS AN IDENTIFIER WHERE ONE RESOLVES. The registry writes a spelling
  -- and 0 of 220 resolved to anything, seven lines below `superseded`'s comment about a real
  -- foreign key rather than a string nobody checks. Both are kept: the spelling is what was
  -- written, the credit is what it means.
  keeps    TEXT,
  keeps_credit TEXT REFERENCES credit(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX identity_ruling_one ON identity_ruling (kind, subject, about);

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
  state TEXT NOT NULL REFERENCES work_state_kind(name),
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
  says   TEXT REFERENCES state_saying(name),
  term   TEXT,
  url    TEXT,
  read   TEXT CHECK (read IS NULL OR read GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR read GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

CREATE UNIQUE INDEX state_claim_one ON state_claim (work, source, coalesce(says, ''));

-- HOW A WORK IS PRESENTED, AND WHETHER IT IS PRESENTED AT ALL. `marketing_label` is publisher-side
-- labelling under DEFINITIONS §4, which is a different question from the shelf a work was admitted
-- on, and `visibility` is the §13 register: `rebutted` and `marginal`.
CREATE TABLE work_presentation (
  work       TEXT PRIMARY KEY REFERENCES work(id) ON DELETE CASCADE,
  -- NULL WHERE THE PUBLISHER APPLIED NONE, rather than the string `none`, which 2,127 rows held.
  -- A word standing for absence is the fault §5 names, and it also makes `label IS NOT NULL` lie.
  label      TEXT CHECK (label IS NULL OR label <> 'none'),
  visibility TEXT CHECK (visibility IS NULL OR visibility IN ('rebutted', 'marginal')),
  -- HOW THE LABEL WAS ARRIVED AT, which the corpus states as a source, a page, a date and a note.
  source     TEXT,
  url        TEXT,
  retrieved  TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
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

  -- THE JUDGEMENTS THAT USED TO SIT HERE ARE IN `name_record`, §5h. `verified`, `uncertain`,
  -- `ordinary` and `transliterates` describe the RECORD somebody ruled on and this row is a FOLD,
  -- so two spellings folding together collided on them and the loader resolved it by overwriting.
  -- 14 `verified: true` rulings were erased that way: `今東　ともよ`, whose reading the National
  -- Diet Library states and a person verified, folds onto `今東ともよ`, whose reading is an
  -- analyser's, and the surviving row said nobody had verified it. Under STANDING-INSTRUCTIONS §6
  -- that ships as marking a national library reading unverified.
  --
  -- `undivided` IS DELIBERATELY NOT A COLUMN ANYWHERE. A person's romanisation runs the family and
  -- given names together where nothing states the parting point, and the store holds the reading
  -- itself and whether the credit is a person, which is everything the flag is computed from.

  -- ONE TITLE STANDING FOR ANOTHER, which is how an edition marker keeps its work's English.
  --
  -- A CIRCLE IS MADE UNSTATEABLE RATHER THAN COUNTED, ruled by the project owner 2026-08-13. No
  -- CHECK can walk a graph, so `aliases pointing in a circle` was a standing question, and it
  -- caught two-node cycles alone. The rule that does the whole job is that a RETIRED row may not
  -- point at another retired row: `retired` says whether this row is itself an alias, `wants`
  -- carries the constant 0 whenever it points at anything, and the foreign key then demands a
  -- target whose `retired` is 0. A cycle of ANY length needs every row in it retired and every
  -- target current, which no arrangement satisfies.
  --
  -- IT FORBIDS CHAINS TOO, and that is a rule about how a rename is recorded. Re-point the aliases
  -- rather than chaining them, which is the discipline §5d had to apply by hand when `w01234` named
  -- a survivor that had itself been retired. `superseded` gets the property for nothing, because a
  -- retired work id is not a row in `work`; `alias_of` is self-referential and this is how it says
  -- the same thing.
  alias_of INTEGER REFERENCES surface(id) ON DELETE SET NULL,
  retired  INTEGER GENERATED ALWAYS AS (alias_of IS NOT NULL) STORED,
  wants    INTEGER GENERATED ALWAYS AS (CASE WHEN alias_of IS NULL THEN NULL ELSE 0 END) STORED,
  CHECK (alias_of IS NULL OR alias_of <> id),

  UNIQUE (kind, folded),
  -- SO AN EDGE CAN NAME BOTH AT ONCE. A composite foreign key needs these to point at, and §5f
  -- applies the same trick to every edge into this table rather than to one of the five.
  UNIQUE (id, kind),
  UNIQUE (id, retired, kind),
  FOREIGN KEY (alias_of, wants, kind) REFERENCES surface (id, retired, kind)
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
  surface INTEGER NOT NULL,
  kind    TEXT NOT NULL CHECK (kind = 'credit-line'),
  PRIMARY KEY (work, surface),
  FOREIGN KEY (surface, kind) REFERENCES surface (id, kind) ON DELETE CASCADE
);

-- ONE RECORD IN THE NAME STORE, AND WHAT A PERSON RULED ABOUT IT. `data/names/*.yaml` is keyed by
-- the spelling a source wrote, and 112 author spellings fold onto another's key, so a judgement
-- about one of them is not a judgement about the fold they share.
--
--   verified       somebody has ruled on this record. NULL where nobody has looked, which is a
--                  different thing from looked and unsure, and the interface's mark turns on it.
--   uncertain      the reading was assembled a character at a time, weaker than a guess at the
--                  whole word.
--   ordinary       the analyser read ordinary vocabulary rather than a coinage, so its answer is
--                  not the guess the mark exists to flag. `analyser_vocabulary.py` is its one
--                  producer and this is where its answer lands.
--   transliterates the kana are themselves a transliteration, so romanising them takes a reader
--                  further from the name: ステファン・セジク is Stjepan Šejić.
CREATE TABLE name_record (
  id             INTEGER PRIMARY KEY,
  kind           TEXT NOT NULL,
  spelling       TEXT NOT NULL,
  surface        INTEGER NOT NULL,
  verified       INTEGER CHECK (verified IN (0, 1)),
  uncertain      INTEGER NOT NULL DEFAULT 0 CHECK (uncertain IN (0, 1)),
  ordinary       INTEGER NOT NULL DEFAULT 0 CHECK (ordinary  IN (0, 1)),
  transliterates TEXT,
  -- WHAT KIND OF THING THE CREDIT IS, where the name store says. `notation` is the one that answers
  -- NOTHING: `はいむらきよたか(キャラクターデザイン)` is a person with a role welded on, the store
  -- holds the person separately, and the RENDERING is withheld so a lookup reaches the person. The
  -- record stays and is marked, which is what lets the withholding be counted rather than silent.
  entity         TEXT,
  -- HOW THE RECORD WOULD HAVE ITS ENGLISH MADE, which is not the same as having one. 2,571 of the
  -- 2,575 author records state a `basis` and 689 hold an English name, so on most of them the field
  -- says only that the Latin a reader gets is our romanisation. As part of the english CLAIM it
  -- existed on the 689 and vanished on the rest, and the shipped entry carries it either way.
  basis          TEXT,
  -- WHOSE ANSWER THE SHIPPED ENTRY IS IS NOT A COLUMN, and the attempt is worth recording. Where
  -- several spellings fold together the file shows one, chosen by `names/fold` for saying the most.
  -- Stored here the answer was WRONG: the rule ranks the RENDERED entries and this table holds the
  -- records, so a record whose rendering is withheld, or whose ruby the reading contradicts, scored
  -- for fields the reader never sees and won folds it does not win. The rule is one function and
  -- both callers ask it, which is what §3 wants; what it is asked ABOUT has to be the same thing.
  UNIQUE (kind, spelling),
  FOREIGN KEY (surface, kind) REFERENCES surface (id, kind) ON DELETE CASCADE
);

CREATE INDEX name_record_surface ON name_record (surface);


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
  surface INTEGER PRIMARY KEY,
  kind    TEXT NOT NULL CHECK (kind = 'credit-line'),
  -- WHAT THE FIELD PUTS BETWEEN TWO PEOPLE, so a recomposed byline reads as the field it replaces.
  joiner  TEXT NOT NULL,
  -- THE DIVISION DOES NOT ACCOUNT FOR EVERYTHING THE FIELD SAYS, which is what stops the interface
  -- rebuilding a byline out of an incomplete answer.
  partial INTEGER NOT NULL DEFAULT 0 CHECK (partial IN (0, 1)),
  FOREIGN KEY (surface, kind) REFERENCES surface (id, kind) ON DELETE CASCADE
);

CREATE TABLE credit_part (
  surface INTEGER NOT NULL REFERENCES credit_division(surface) ON DELETE CASCADE,
  seq     INTEGER NOT NULL,
  -- NULL ONLY WHERE THE PART IS `AND OTHERS`. `[他著]雪子` divides into a person and the field's own
  -- statement that there are more people it does not name, which is a part of the byline and not a
  -- person: 10 lines say it, the loader dropped the ones with no name, and a page rebuilt from the
  -- parts would have said the book is by one person where the catalogue says otherwise.
  name    TEXT,
  etc     INTEGER NOT NULL DEFAULT 0 CHECK (etc IN (0, 1)),
  -- AND ITS FOLD, which is what `credit_spelling` is keyed on.
  name_folded TEXT,
  -- THE PHRASE THE FIELD WROTE, which may state several jobs at once. `credit_part_role` is the
  -- same fact as rows, and this is kept for the same reason `state_claim.term` is: what a source
  -- actually said outlives our reading of it.
  role    TEXT,
  PRIMARY KEY (surface, seq),
  CHECK (name IS NOT NULL OR etc = 1)
);

CREATE TABLE credit_part_role (
  surface INTEGER NOT NULL,
  seq     INTEGER NOT NULL,
  role    TEXT NOT NULL REFERENCES role(name),
  PRIMARY KEY (surface, seq, role),
  FOREIGN KEY (surface, seq) REFERENCES credit_part (surface, seq) ON DELETE CASCADE
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
  surface      INTEGER NOT NULL,
  -- THE KIND TRAVELS WITH THE EDGE, as it does on `names`. §5f applied it here because a reading
  -- claim on a chapter label was accepted, and only a name is claimed about.
  kind         TEXT NOT NULL CHECK (kind IN ('title', 'author', 'publisher')),
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
  retrieved    TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),  -- ISO 8601 the answer was obtained
  -- WHEN A PERSON LOOKED AT IT, which is a different date from the one above and is the one a
  -- citation shows. `provenance.PARTS` names both and the loader kept only the first.
  reviewed     TEXT CHECK (reviewed IS NULL OR reviewed GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR reviewed GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
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
  -- WHICH RECORD MADE IT, §6. A claim hung off the FOLD alone, and 112 author spellings fold onto
  -- another's key, so two records' answers arrived in one heap with nothing saying whose was whose.
  -- `feed/names.json` ships ONE entry per fold, rendered from the record `fold_map` judged the
  -- fullest, and that entry could not be emitted from a heap: the reading, the English, the marks
  -- and the citation all have to come from the SAME record or the entry contradicts itself.
  record       INTEGER REFERENCES name_record(id) ON DELETE CASCADE,
  -- WHETHER THE RECORD STATES THIS BASIS OR INHERITED IT. A division whose record says nothing
  -- about where its answer came from takes the READING's basis, which `facts/division` says is
  -- right: a cited basis gave the division with the reading. But the two are then indistinguishable
  -- in this column, and the interface marks a division only where the record answered for it, so
  -- 771 names would carry a mark 20 of them earned.
  basis_stated INTEGER NOT NULL DEFAULT 0 CHECK (basis_stated IN (0, 1)),

  -- AND A NOTE THAT IS EMPTY IS NOT A NOTE. Every presence constraint in this file was satisfied
  -- by `''` until §5f: a researched claim with an empty note, a work with an empty title and a
  -- ruling with an empty basis were all accepted.
  CHECK (basis <> 'researched' OR coalesce(note, '') <> ''),

  -- A STATED CLAIM NAMES WHERE IT CAME FROM. This is the stage-three invariant as a constraint:
  -- a reading a source printed is an INPUT, the repository is its only copy, and one without an
  -- address cannot be checked, refreshed or argued with.
  -- `coalesce` BECAUSE THE CHECK WAS THREE-VALUED AND PASSED ON EVERYTHING IT COULD NOT SEE. With a
  -- NULL source kind the last disjunct is NULL, the whole expression is NULL, and a CHECK passes on
  -- NULL: a `stated` claim saying nothing at all about its evidence was ADMITTED, and the same
  -- claim naming `national-library` was REFUSED. 221 rows were in that hole, 219 of them divisions
  -- §5c added with no source kind at all. It is the fault §5a fixed on `work.first_event` four
  -- lines above, with a different operator.
  -- AND IT ASKS ONLY OF A CLAIM THE RECORD STANDS BEHIND. A displaced claim is one somebody has
  -- already argued with and set aside, kept because §1 records a disagreement rather than
  -- discarding it, and `reading_conflicts` holds a basis, a source and a value with nowhere to put
  -- an address. Demanding a document for something nobody asserts any more would mean dropping the
  -- disagreement to satisfy a rule about assertions. docs/GAPS.md carries the shape.
  CHECK (displaced = 1 OR basis <> 'stated' OR url IS NOT NULL OR isbn IS NOT NULL
         OR coalesce(source_kind, '') = 'derived'),

  -- A BASIS BELONGS TO A CLAIM, and the pair is what `basis_for_predicate` admits. This is what
  -- makes an English name resting on `analyser` unstateable: the vocabularies are different and
  -- the schema now knows which is which instead of accepting either for either.
  FOREIGN KEY (basis, predicate) REFERENCES basis_for_predicate (basis, predicate),
  FOREIGN KEY (surface, kind) REFERENCES surface (id, kind) ON DELETE CASCADE
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
-- WHICH RECORDS MAKE A CLAIM, WHICH IS MANY AND WAS A COLUMN. §6. Two spellings folding onto one
-- surface state the same reading, and a claim is identified by its surface and its content, so the
-- second is not a second claim: it is the same claim, made twice. The column then held whichever
-- record was read first, and 邪武丸, which wins its fold, had its reading filed against the record
-- that loses it. The entry the site shows came out with no reading at all.
CREATE TABLE claim_record (
  claim  INTEGER NOT NULL REFERENCES claim(id)       ON DELETE CASCADE,
  record INTEGER NOT NULL REFERENCES name_record(id) ON DELETE CASCADE,
  PRIMARY KEY (claim, record)
);

CREATE INDEX claim_record_record ON claim_record (record);

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

-- ── the vocabularies §5j gave a home to ────────────────────────────────────────────────────────
--
-- EACH OF THESE WAS FREE TEXT AND EACH IS NOW A FOREIGN KEY, filled from the `facts/` module that
-- states it. A CHECK written here would have been a SECOND home for the vocabulary, which is the
-- fault `check.STATES_A_READING` demonstrated by drifting from `curate.READING_ATTRIBUTION` before
-- this store existed, so in every case the ruling moved first and the key followed it.
CREATE TABLE work_state_kind (name TEXT PRIMARY KEY);      -- facts/serialisation.STATES
CREATE TABLE state_saying   (name TEXT PRIMARY KEY);       -- facts/serialisation.SAYS
CREATE TABLE release_kind   (name TEXT PRIMARY KEY);       -- facts/serialisation.RELEASE_KINDS
CREATE TABLE anchor_scheme  (name TEXT PRIMARY KEY);       -- facts/identity.ANCHOR_SCHEMES
CREATE TABLE ruling_shape   (name TEXT PRIMARY KEY);       -- facts/identity.RULING_SHAPES
CREATE TABLE volume_basis   (name TEXT PRIMARY KEY);       -- facts/dating.VOLUME_BASES

-- WHAT JOB A BYLINE STATES. `facts/credit/splitter.ROLES` is the closed set and the interface holds
-- a gloss for every one of them, which an invariant proves. A field may state SEVERAL at once,
-- `企画・監修`, so `credit_part.role` keeps the phrase the field wrote and `credit_part_role` holds
-- the atoms: a multi-valued column is the one shape a relational store may not keep.
CREATE TABLE role (name TEXT PRIMARY KEY);

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

  -- A KEY §7 CAN ADDRESS THIS ROW BY, which it had none of. `delta.write` identifies a row by a
  -- column-to-value mapping and `id` was a rowid handed out by the order `works.json` happened to
  -- iterate, with `edition` keyed on top of it, so the largest and most volatile table in the store
  -- could be inserted into and never updated. That is where §5b found `claim`.
  --
  -- THE RECORD THAT STATES IT, AND ITS POSITION IN THAT RECORD. 2,818 volumes carry no ISBN and 66
  -- of those share a work, a position and a designation with another, so no key is available from
  -- the volume's own facts; a UNIQUE over the three would refuse the reissue this table's comment
  -- below cites. Where the row came FROM is always known and always distinct.
  record  TEXT NOT NULL,
  seq     INTEGER NOT NULL,

  -- WHAT A VOLUME IS CALLED AND WHERE IT SITS ARE TWO FACTS. `volume` is a position in a run and
  -- an integer answers it. A DESIGNATION is the word the publisher uses: `上`, `創刊号`,
  -- `2017年1月号`. 983 volumes carry one and no integer can hold it, which is STORE-PLAN §3.
  --
  -- NEITHER IS REQUIRED AND NEITHER EXCLUDES THE OTHER. `build.volume_number` reads 創刊号 as the
  -- first issue, so a designation can acquire a position.
  volume       INTEGER CHECK (volume IS NULL OR volume >= 0),
  -- AS THE RECORD STATES IT. `number_raw` below is what the catalogue called the volume whether or
  -- not that reads as a position, so `coalesce(designation, number_raw)` is what a volume is
  -- called and this column stays what the record says.
  designation  TEXT,
  -- WHAT THE CATALOGUE CALLED IT, `vol.6`, beside the integer position read out of it.
  number_raw   TEXT,
  -- WHETHER openBD HOLDS A REGISTRATION FOR IT, which is how a volume's ISBN reached a date, and
  -- the date it gave where that is what the row shows.
  openbd       TEXT,
  openbd_date  TEXT,
  -- THE BIBLIOGRAPHY'S OWN IDENTIFIER FOR THE BOOK, and where the ISBN was read from.
  madb_id      TEXT,
  isbn_source  TEXT,
  cover_url    TEXT,
  -- THE LAST VOLUME, AND WHO SAYS SO. A shop stating a completed run is a claim like any other, so
  -- it carries its source, how it was arrived at, and the count it stated.
  final_volume INTEGER NOT NULL DEFAULT 0 CHECK (final_volume IN (0, 1)),
  final_source TEXT,
  final_provenance TEXT,
  final_volumes INTEGER,
  final_retrieved TEXT

  -- THERE IS NO KEY HERE BEYOND THE ISBN AND THAT IS THE DATA'S DOING, not an omission. 92 rows
  -- share a work, a position and a designation with another, 40 of them holding no ISBN at all:
  -- 13 works carry a reissue, so w00174 legitimately holds volume 2 twice at different ISBNs, and
  -- for the 40 nothing in the corpus distinguishes the two records. A UNIQUE over the three would
  -- refuse a reissue, which is a real thing this project holds.
);

CREATE UNIQUE INDEX volume_source ON volume (record, seq);
CREATE INDEX volume_work ON volume (work);

-- ONE ISBN IS ONE BOOK AND ONE BOOK MAY CARRY SEVERAL, which `volume.isbn UNIQUE` could say only
-- half of. 81 volumes list two: a regular printing and a special edition of the same book, which
-- the corpus holds as `editions` and the store kept one of. The key is the ISBN, so the half that
-- matters is unweakened, and the foreign key is what lets a book have more than one.
--
-- THE KEY IS THE ISBN AND NOT A SPELLING OF IT, which is the difference between a constraint and a
-- constraint that fires. 940 of 3,371 arrived hyphenated beside 2,423 bare, so `9784091572882` and
-- `978-4-09-157288-2` were two rows, and "one ISBN is one book" was defeated by punctuation. It hid
-- two duplicate WORKS for as long as it stood: 8 ISBNs reached two work identifiers each.
--
-- NORMALISED IN THE SCHEMA RATHER THAN WATCHED FROM OUTSIDE, ruled by the project owner 2026-08-13.
-- A budget counting mis-spelled ISBNs would report a fault after the row landed; a format the table
-- refuses means the duplicate cannot enter and no second thing has to be consulted to know it. 13
-- digits, or 10 for the older form whose check digit may be X.
CREATE TABLE volume_isbn (
  -- THE RECORD'S OWN ORDER, WITH ITS PRIMARY FIRST. A book with a standard and a special edition
  -- lists both, and which one the record leads with is the one a page shows as THE isbn; sorting
  -- them put the special edition first on 81 volumes.
  seq    INTEGER NOT NULL,
  isbn   TEXT PRIMARY KEY CHECK (
           isbn GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
           OR isbn GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9X]'),
  volume INTEGER NOT NULL REFERENCES volume(id) ON DELETE CASCADE
);

CREATE INDEX volume_isbn_volume ON volume_isbn (volume);

-- A DATED EVENT ABOUT ONE BOOK. One of each kind per volume, so a printing and a delivery sit
-- beside each other and neither displaces the other.
CREATE TABLE edition (
  id      INTEGER PRIMARY KEY,
  volume  INTEGER NOT NULL REFERENCES volume(id) ON DELETE CASCADE,
  kind    TEXT NOT NULL CHECK (kind IN ('printing', 'shop-delivery', 'serialisation')),
  dated   TEXT CHECK (dated IS NULL OR dated GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR dated GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),

  -- WHAT KIND OF EVIDENCE THE DATE RESTS ON, following `claim`'s pattern rather than reusing its
  -- table: `claim` is scoped to what a NAME is, by its own CHECK on predicate. A closed set,
  -- because a basis nobody can name is a basis nobody can weigh.
  dated_basis  TEXT REFERENCES volume_basis(name),
  -- WHETHER THE RECORD SAID SO OR THE LOADER WORKED IT OUT. 127 volumes state their basis and the
  -- rest have one derived from the same evidence the citation uses, which is a fair answer to
  -- "what does this date rest on" and is NOT the record's own words. `works.json` ships only the
  -- stated ones, so the difference has to be in the store or the file cannot be emitted from it.
  basis_stated INTEGER NOT NULL DEFAULT 0 CHECK (basis_stated IN (0, 1)),

  -- WHO SAYS SO, AND WHERE, WHICH ARE TWO FACTS AND WERE ONE COLUMN. `cite` packed a scheme and an
  -- identifier into one string three ways: 3,635 urls, 2,375 `madb:C418820`, and 906 that were the
  -- bare word `ndl`, which names a source and locates nothing. `work_anchor` splits exactly this
  -- into a scheme and an address and gets a key out of it, so the file disagreed with itself.
  --
  -- A DATE NAMES ITS SOURCE, ALWAYS. That is `per-book dates cite their page` as a constraint, and
  -- it is the half every row can satisfy. Whether the source also gives a page a reader can open is
  -- `dates cited to something that is not a page`, which counts the 906 rather than refusing them.
  source  TEXT,
  cite    TEXT,
  CHECK (dated IS NULL OR coalesce(source, '') <> ''),

  UNIQUE (volume, kind)
);

-- AN ISBN IS A KEY INTO EVERY DATED REGISTRY THERE IS, so a volume holding one and no date means
-- nobody asked. That was `CHECK (isbn IS NULL OR dated IS NOT NULL)` while both facts sat on one
-- row, and no CHECK can reach across three tables, so it is a standing question now:
-- `volumes with an isbn and no date`, which `check.py` has held at 0 since §3 and `delta` asks of
-- the store. The constraint is weaker and the loss is recorded rather than absorbed.

CREATE INDEX edition_volume ON edition (volume, kind);

-- WHERE AND WHEN A WORK FIRST APPEARED, AND ON WHOSE WORD. A date, the venue that carried it and
-- what kind of venue that is, and the country, which is its own question with its own basis: 2,574
-- works state `japanese-edition-catalogued`, which places the EDITION in Japan and says so rather
-- than claiming the work was first published there.
-- ONE CATALOGUE RECORD, WHICH IS THE LAYER `works.json` IS WRITTEN AT. 2,574 of these against
-- 3,038 works: a work compiled from two records has two rows here, each with its own title as that
-- catalogue wrote it, its own creator field and its own count of volumes.
--
-- `grouping` SAYS HOW THE RECORD WAS JOINED TO ITS WORK: by a series link the catalogue states, by
-- the title alone, by a match on the title, or by more than one route. It is how a reader can tell
-- a firmly identified row from one held together by its name.
CREATE TABLE record (
  id           TEXT PRIMARY KEY,
  work         TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  title        TEXT NOT NULL,
  yomi         TEXT,
  -- THE ENGLISH THE RECORD ITSELF CARRIES, on 59 of them, which is a catalogue transcribing a
  -- parallel title rather than the rendering `claim` holds for the name.
  title_en     TEXT,
  title_en_basis TEXT,
  creator      TEXT,
  -- THE FIELD'S OWN FOLD, so the division `credit_part` holds for it can be joined without a
  -- caller doing the folding. `index.json` names a row's people in the order the FIELD wrote them.
  creator_folded TEXT,
  creator_basis TEXT,
  volume_count INTEGER CHECK (volume_count IS NULL OR volume_count >= 0),
  grouping     TEXT,
  content_tier TEXT,
  -- PER RECORD, BECAUSE IT VARIES BETWEEN THE RECORDS OF ONE WORK. 220 rows differ from the label
  -- `work_presentation` carries: one catalogue applies the publisher's yuri label and another
  -- states none for the same book, and `index.json` ships the record's own answer.
  marketing_label TEXT CHECK (marketing_label IS NULL OR marketing_label <> 'none'),
  -- AND HOW THAT LABEL WAS ARRIVED AT, per record for the same reason the label is.
  label_source    TEXT,
  label_url       TEXT,
  label_retrieved TEXT CHECK (label_retrieved IS NULL OR label_retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  label_note      TEXT,
  -- THE HOUSE AND LINE AS THIS RECORD WROTE THEM. `print_row` carries the same strings for the
  -- 2,512 records a series row's run names; these 2,574 include the ones no run does.
  publisher_raw   TEXT,
  imprint_raw     TEXT,
  distributor     TEXT,
  shop_url     TEXT,
  periodical   INTEGER NOT NULL DEFAULT 0 CHECK (periodical IN (0, 1))
);

CREATE INDEX record_work ON record (work);

-- WHICH ADAPTERS A RECORD WAS ASSEMBLED FROM, which `sources` ships as a list and is a list of
-- rows here for the reason every other list in this schema is.
-- THE PEOPLE A RECORD'S CREATOR FIELD NAMES, IN THE ORDER IT NAMES THEM. `facts/credit.split_detail`
-- is the splitter and this is where its answer lands, so a consumer needs no splitter of its own.
--
-- IT IS NOT `credit_part`, AND THE DIFFERENCE IS REAL. That table holds `creditline._divide`'s
-- answer, which is what a page RENDERS a byline from; this holds the splitter's, which is what an
-- identifier is minted against. They disagree about 17 records, and both are shipped: `index.json`
-- resolves through this one. Two divisions of one field is a §3 fault worth its own entry in
-- docs/GAPS.md rather than a silent choice made here.
CREATE TABLE record_credit (
  record TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
  seq    INTEGER NOT NULL,
  credit TEXT NOT NULL REFERENCES credit(id) ON DELETE CASCADE,
  PRIMARY KEY (record, seq)
);

CREATE TABLE record_source (
  record TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  PRIMARY KEY (record, source)
);

-- KEYED ON THE RECORD AND NOT ON THE WORK, because `works.json` is the RECORD layer and two
-- catalogue records of one work each state their own first publication. Keying on the work kept
-- whichever record was read first and discarded the other's answer.
CREATE TABLE work_origin (
  record       TEXT PRIMARY KEY,
  work         TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  dated        TEXT CHECK (dated IS NULL OR dated GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR dated GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  date_source  TEXT,
  date_basis   TEXT,
  venue        TEXT,
  venue_type   TEXT,
  country      TEXT,
  country_basis TEXT,
  country_note TEXT,
  note         TEXT,
  -- WHAT THE DATE IS A DATE OF, and what the row does about the silence after it. 1,124 records
  -- carry these: the event the date names, whether anything followed it, and how long nothing has.
  date_event   TEXT,
  date_followup TEXT,
  date_silence TEXT
);

-- THE CATALOGUE RECORDS A WORK WAS COMPILED FROM, with the page each was read at and when. This is
-- what `records[]` ships and what lets a reader follow a fact back to the catalogue that stated it.
CREATE TABLE work_record (
  record    TEXT NOT NULL,
  work      TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  source    TEXT NOT NULL,
  url       TEXT,
  retrieved TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  PRIMARY KEY (record, source)
);

-- ── the print rows a work'''s run is made of ─────────────────────────────────────────────────────
--
-- A PRINT ROW IS A CATALOGUE RECORD AS A SHELF WOULD COUNT IT, which is what `publishers.json` and
-- the print half of `series.json` are both counting. A work carrying two editions under one line is
-- TWO rows and one work, which is why a house's `rows` and its `works` are different numbers and
-- say so by being named differently.
--
-- THE IMPRINT IS THE SPELLING AS CATALOGUED, not the line it resolves to. `facts/imprint.census`
-- decides which line a spelling names and measures the years each covers, and it can only do that
-- from the spellings the rows actually carry: `Yuri-hime comics`, `Yurihime comics` and
-- `IDコミックス　／　Yurihime comics` are one line written three ways and three rows' worth of
-- evidence about which years it was used in.
CREATE TABLE print_row (
  id          INTEGER PRIMARY KEY,
  work        TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  -- THE CATALOGUE RECORD THIS ROW STANDS FOR, and the key §7 addresses it by. `work_ids` names
  -- every record folded into it, which is `print_row_record` below.
  record      TEXT NOT NULL UNIQUE,
  publisher   TEXT REFERENCES publisher(id) ON DELETE SET NULL,
  -- AS THE CATALOGUE WROTE THEM. `publisher` above is what the spelling resolved to, and these are
  -- what it said, because the census is about the spellings and not about the resolution.
  publisher_raw TEXT,
  imprint_raw   TEXT,
  distributor   TEXT,
  label       TEXT,
  first       TEXT CHECK (first IS NULL OR first GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR first GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  last        TEXT CHECK (last IS NULL OR last GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR last GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  volumes     INTEGER CHECK (volumes IS NULL OR volumes >= 0),
  shop_url    TEXT,
  delivered_from TEXT,
  periodical  INTEGER NOT NULL DEFAULT 0 CHECK (periodical IN (0, 1))
);

CREATE INDEX print_row_work ON print_row (work);

-- EVERY CATALOGUE RECORD FOLDED INTO ONE ROW. `work_ids` on the block, which is how a run built
-- from several records keeps every address resolvable.
CREATE TABLE print_row_record (
  print_row INTEGER NOT NULL REFERENCES print_row(id) ON DELETE CASCADE,
  record    TEXT NOT NULL,
  PRIMARY KEY (print_row, record)
);

-- A SEAT ON A PRINT ROW, WHICH IS WHAT A PUBLISHER PAGE COUNTS. `facts/printblock.parties` says a
-- block names a publisher and may name a distributor, and each is a party with its own spelling of
-- the house and of the line. A house's `rows` counts parties and its `works` counts works, which is
-- why the two are different numbers.
--
-- THE RESOLUTION IS THE COMPILER'S AND ONLY THE ANSWER IS HERE. `publisher_identity.anchor` decides
-- which house a spelling names and `facts/imprint.resolve` which line, so an emitter grouping these
-- rows re-decides nothing: that is STORE-PLAN §3's rule for the whole plan, and it is what lets
-- `publishers.json` be an aggregation with no judgement left in it.
CREATE TABLE print_party (
  id            INTEGER PRIMARY KEY,
  print_row     INTEGER NOT NULL REFERENCES print_row(id) ON DELETE CASCADE,
  seat          TEXT NOT NULL CHECK (seat IN ('publisher', 'distributor')),
  publisher_raw TEXT,
  publisher     TEXT REFERENCES publisher(id) ON DELETE SET NULL,
  imprint_raw   TEXT,
  -- NULL WHERE NO LINE ANSWERS FOR THE SPELLING, which `imprint strings that reach no line` counts
  -- and a page shows as itself rather than dropping or inventing one.
  imprint       INTEGER REFERENCES imprint(id) ON DELETE SET NULL,
  -- THE PARTY'S OWN DATES AND NOT THE BLOCK'S. `facts/printblock.parties` says each folded record
  -- states its own, and a line's span is measured from the record that CARRIES the line rather than
  -- from whichever record happened to name the run. Taking the block's moved one span by a year.
  first         TEXT CHECK (first IS NULL OR first GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR first GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  last          TEXT CHECK (last IS NULL OR last GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR last GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

CREATE INDEX print_party_row ON print_party (print_row);
CREATE INDEX print_party_publisher ON print_party (publisher);

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
  latest     TEXT CHECK (latest IS NULL OR latest GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR latest GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  -- THE PLATFORM LISTS MORE THAN WE HOLD, which the interface already draws as `90+`.
  partial    INTEGER NOT NULL DEFAULT 0 CHECK (partial IN (0, 1)),
  retrieved  TEXT CHECK (retrieved IS NULL OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR retrieved GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
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
  published  TEXT CHECK (published IS NULL OR published GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR published GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  url        TEXT,
  kind       TEXT REFERENCES release_kind(name),
  first_seen TEXT CHECK (first_seen IS NULL OR first_seen GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' OR first_seen GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
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
--     SELECT s.folded FROM surface s WHERE s.kind IN ('title','author','publisher')
--     AND NOT EXISTS (SELECT 1 FROM names n WHERE n.surface = s.id);
--
-- Each of those is a script today, and the last two have no script at all.
