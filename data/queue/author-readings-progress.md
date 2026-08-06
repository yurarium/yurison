# Author readings pass, 2026-08-06 — checkpoint

Task: settle author readings from stated sources. Two routes.

1. openBD collationkey (publisher stating how its own author is read) over every ISBN the corpus
   holds. `reading_basis: stated`, `reading_source_kind: publisher-jp`.
2. GAPS §9: a Latin name the person writes themselves. `basis: stated`, `source_kind: author`.

Cache: ../names-cache/openbd.json, seeded from ../openbd-cache (410 ISBNs, 275 held).

## State at start (data/names/authors.yaml, 1757 names)

| reading_basis | n |
|---|---:|
| analyser | 873 |
| stated | 538 |
| surface | 276 |
| none | 65 |
| back-converted | 5 |

`en basis`: romaji 1690, stated 65, official-jp 1, none 1.

## Log

- Read the authority documents.
- Offline run of openbd_reading.py: 873 guessed, 122 on a book we hold an ISBN for, 302 ISBNs.
  Health refused, because offline cannot tell an uncached ISBN from one openBD does not hold.
- Widened `openbd_reading.py`: `corpus_isbns()` asks over every ISBN any source record states
  (1363) instead of only the ISBNs MADB files under a credit we hold (302); `unsettled_readings()`
  selects on nothing having stated a reading rather than on an analyser having guessed one;
  `normalised()` declines a collationkey that has lost a kana name's own kana.
- Fetched: openBD holds 1115 of 1363. 104 readings settled, all `stated` / `publisher-jp`.
- Appended those 104 plus とりい しづく (surface) to data/names/curated.yaml. `--check` clean at
  1182 titles, 584 authors.
- NEXT: apply, rebuild, gate. Then GAPS §9, the Latin names people write themselves.
- Applied. Store: stated 538 -> 642.
- `curate.py` could not record what GAPS §9 asks for. `ATTRIBUTION["stated"]` listed platform and
  publisher-jp and not `author`, so an entry attributing a Latin byline to the artist's own page
  was rejected outright. The row's own comment says "the person's own rendering, where they wrote
  it". `author` reached SOURCE_KINDS and READING_ATTRIBUTION in a round about readings and this
  list was edited apart from them. Added, with the case in test_curate.py.
- Found while ranking authors: 181 kana-only author names carried an `analyser` reading. Pass 1
  answers those exactly and for nothing, but the autopilot in build.py only ever runs pass 4, and
  pass 4 queued on "has no reading". Three were wrong on the live site: はうあゆ as Wa u Ayu,
  はとぼし as Wa Toboshi (an analyser takes は as the particle) and あーねすと as アー ネ ストッ.
  Fixed in pass4_analyser.wants_reading, calling pass1_kana.surface_fields rather than repeating
  it. Scoped to authors: 6 kana TITLES have the analyser right, because in a sentence は IS wa.
- Corpus regenerated under this run (BOOK☆WALKER imprint suffixes retracted, 93 duplicate works).
  Re-read titles.json: 3144 titles, curated keys still all match, 0 stray.
- Autopilot bug found and fixed: a `reading_refuted` record has no reading, and `fill_missing`
  read that as an empty slot. Ten refuted names were refilled with the guess a reviewer had just
  disproved, 古川楊也 back as フルカワ ヨウナリ within hours. `wants_reading` now declines them.
- GAPS §9: 犬井あゆ -> Ayu Inui and 野宮りおん -> Rion Nomiya, both `stated` off クロスフォリオ出版's
  own English editions, corroborated by NDL's reading. Merged into their existing entries rather
  than appended, which would have dropped their NDL readings under a duplicate key.
- Shelf trap recorded in curated.yaml: 179 of 976 BOOK☆WALKER credits carry a separator and the
  part after it is the circle, not the person.

## Finished 2026-08-06

- `./test.py`: 84 passed, 0 failed, 0 vacuous, 0 unproven.
- `./check.py --gate`: 0 invariants violated. One budget over, `stock phrasing in comments`
  897 against 896. Not from this work: swapping every file this session touched for its HEAD
  version leaves the count at 897, and build.py alone is one LOWER than HEAD. Another session is
  working in that area.
- `uncertain readings` back to 64, on budget, after the refutation loop was closed.
